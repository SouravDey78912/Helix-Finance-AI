import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from rag.ingest.parser import parse_document
from rag.ingest.cleaner import clean_text
from rag.ingest.metadata_extractor import extract_metadata
from rag.ingest.chunker import chunk_text
from rag.ingest.embedder import embed_chunks, TextChunk
from rag.query.rewriter import rewrite_query
from rag.query.hybrid_search import hybrid_search
from rag.query.reranker import rerank
from rag.query.context_builder import build_context
from rag.pipeline import RAGPipeline


@pytest.mark.asyncio
async def test_clean_text():
    raw = "  Hello \t World \n\n New Line   "
    cleaned = await clean_text(raw)
    assert cleaned == "Hello World\n\nNew Line"


@pytest.mark.asyncio
async def test_parser_txt(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello compliance text", encoding="utf-8")
    
    parsed = await parse_document(str(txt_file), "text/plain")
    assert parsed == "Hello compliance text"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_extract_metadata_llm(mock_completion):
    # Mock LLM Response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"doc_type": "policy", "jurisdiction": "US", "effective_date": "2024-01-01", "regulatory_body": "FinCEN", "topics": ["AML"], "language": "English"}'
            )
        )
    ]
    mock_completion.return_value = mock_response

    metadata = await extract_metadata("some compliance document text", "test_policy.txt")
    assert metadata["doc_type"] == "policy"
    assert metadata["jurisdiction"] == "US"
    assert metadata["regulatory_body"] == "FinCEN"


@pytest.mark.asyncio
@patch("litellm.acompletion", side_effect=Exception("API Error"))
async def test_extract_metadata_fallback(mock_completion):
    # Tests that the fallback regex/heuristic functions work when the LLM fails
    metadata = await extract_metadata(
        "This is an Anti-Money Laundering AML policy regulation for the United States FinCEN effective 2024-05-10.",
        "aml_regulation.txt",
    )
    assert metadata["doc_type"] in ["policy", "regulation"]
    assert metadata["jurisdiction"] == "US"
    assert metadata["regulatory_body"] == "FinCEN"
    assert "AML" in metadata["topics"]


@pytest.mark.asyncio
async def test_chunk_text():
    text = "Line A\n\nLine B\n\nLine C"
    chunks = await chunk_text(text, document_id="doc-123", chunk_size=20, chunk_overlap=2)
    assert len(chunks) > 0
    assert chunks[0].document_id == "doc-123"
    assert chunks[0].text == "Line A"


@pytest.mark.asyncio
@patch("litellm.aembedding")
async def test_embed_chunks(mock_aembedding):
    mock_response = MagicMock()
    mock_response.data = [{"embedding": [0.1, 0.2, 0.3]}]
    mock_aembedding.return_value = mock_response

    chunks = [
        TextChunk(
            chunk_id="chunk-1",
            text="hello",
            chunk_index=0,
            document_id="doc-1",
            metadata={"source": "test"},
        )
    ]
    embedded = await embed_chunks(chunks)
    assert len(embedded) == 1
    assert embedded[0]["chunk_id"] == "chunk-1"
    assert embedded[0]["embedding"] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_rewrite_query(mock_completion):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='["aml compliance requirements", "fincen aml policy", "regulations for money laundering"]'
            )
        )
    ]
    mock_completion.return_value = mock_response

    rewritten = await rewrite_query("what are aml rules?")
    assert len(rewritten) == 4  # original + 3 variants
    assert rewritten[0] == "what are aml rules?"


@pytest.mark.asyncio
@patch("infrastructure.qdrant_client.search_vectors")
@patch("litellm.aembedding")
async def test_hybrid_search(mock_aembedding, mock_search_vectors):
    mock_emb_response = MagicMock()
    mock_emb_response.data = [{"embedding": [0.1] * 384}]
    mock_aembedding.return_value = mock_emb_response

    mock_search_vectors.return_value = [
        {"chunk_id": "chunk-1", "score": 0.9, "text": "Compliance rules", "metadata": {}},
        {"chunk_id": "chunk-2", "score": 0.8, "text": "AML rules", "metadata": {}},
    ]

    results = await hybrid_search(["query 1"], "helix_docs", top_k=5)
    assert len(results) == 2
    assert "rrf_score" in results[0]


@pytest.mark.asyncio
async def test_rerank():
    candidates = [
        {"chunk_id": "c1", "text": "Compliance is important.", "score": 0.8},
        {"chunk_id": "c2", "text": "KYC processes identify customers.", "score": 0.95},
    ]
    # sentence-transformers CE not installed/failing is tested gracefully here by utilizing fallback
    results = await rerank("who is customer KYC?", candidates, top_n=1)
    assert len(results) == 1
    # Fallback uses score/rrf_score
    assert results[0]["chunk_id"] == "c2"


@pytest.mark.asyncio
async def test_build_context():
    chunks = [
        {"text": "KYC compliance.", "metadata": {"document_id": "d1", "filename": "policy.pdf", "chunk_index": 0}},
        {"text": "AML rules.", "metadata": {"document_id": "d1", "filename": "policy.pdf", "chunk_index": 1}},
    ]
    context = await build_context("query", chunks, max_tokens=1000)
    assert "KYC compliance." in context["context_text"]
    assert "AML rules." in context["context_text"]
    assert len(context["sources"]) == 2
    assert context["sources"][0]["filename"] == "policy.pdf"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_extract_entities_from_chunk(mock_completion):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"entities": [{"entity_type": "Requirement", "title": "CDD Check", "action": "must complete", "condition": "before onboarding", "obligation_level": "MANDATORY", "risk_category": "KYC"}]}'
            )
        )
    ]
    mock_completion.return_value = mock_response

    from rag.ingest.entity_extractor import extract_entities_from_chunk
    entities = await extract_entities_from_chunk("Customer due diligence must be completed before onboarding.")
    assert len(entities) == 1
    assert entities[0]["entity_type"] == "Requirement"
    assert entities[0]["action"] == "must complete"


@pytest.mark.asyncio
@patch("rag.pipeline.upsert_embeddings", new_callable=AsyncMock)
@patch("rag.pipeline.embed_chunks")
@patch("rag.pipeline.chunk_text")
@patch("rag.pipeline.extract_metadata")
@patch("rag.pipeline.clean_text")
@patch("rag.pipeline.parse_document")
async def test_rag_pipeline_ingest(
    mock_parse, mock_clean, mock_meta, mock_chunk, mock_embed, mock_upsert
):
    mock_parse.return_value = "raw compliance doc text"
    mock_clean.return_value = "cleaned text"
    mock_meta.return_value = {"doc_type": "policy", "jurisdiction": "US"}
    
    mock_chunk.return_value = [
        TextChunk(chunk_id="c1", text="Customer due diligence must be completed.", chunk_index=0, document_id="doc1", metadata={})
    ]
    mock_embed.return_value = [{"chunk_id": "c1", "embedding": [0.1], "metadata": {}}]

    pipeline = RAGPipeline()
    res = await pipeline.ingest("mock_file.txt", "doc1", {"filename": "mock_file.txt", "content_type": "text/plain"})
    
    assert res["status"] == "COMPLETED"
    assert res["chunk_count"] == 1
    assert "entities_count" in res
    mock_upsert.assert_called_once()

