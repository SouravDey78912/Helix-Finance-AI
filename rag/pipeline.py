"""
rag/pipeline.py
================
RAG Pipeline orchestrator — coordinates ingest and query sub-pipelines.

Ingest Pipeline (from 01_System_Architecture.md):
  Upload → Parse → Clean → Metadata → Chunk → Embed → Qdrant

Query Pipeline (from 01_System_Architecture.md):
  Query → Rewrite → Hybrid Search → Rerank → Context Builder → LLM
"""

import structlog

from rag.ingest.parser import parse_document
from rag.ingest.cleaner import clean_text
from rag.ingest.metadata_extractor import extract_metadata
from rag.ingest.chunker import chunk_text
from rag.ingest.entity_extractor import extract_entities_from_chunk
from rag.ingest.embedder import embed_chunks
from infrastructure.qdrant_client import upsert_embeddings
from rag.query.rewriter import rewrite_query
from rag.query.hybrid_search import hybrid_search
from rag.query.reranker import rerank
from rag.query.context_builder import build_context

logger = structlog.get_logger(__name__)


class RAGPipeline:
    """
    Orchestrates the full RAG pipeline.
    """

    def __init__(self):
        pass

    async def ingest(self, file_path: str, document_id: str, metadata: dict, status_callback=None) -> dict:
        """
        Run the full document ingestion pipeline with optional granular stage status callbacks.
        """
        logger.info("RAG ingest pipeline started", document_id=document_id, file_path=file_path)
        
        # 1. Parse
        if status_callback:
            await status_callback("PARSING")
        content_type = metadata.get("content_type", "text/plain")
        raw_text = await parse_document(file_path, content_type)
        
        # 2. Clean
        cleaned_text = await clean_text(raw_text)
        
        # 3. Metadata Extraction
        extracted_meta = await extract_metadata(cleaned_text, metadata.get("filename", ""))
        
        # 4. Chunk
        if status_callback:
            await status_callback("CHUNKING")
        chunks = await chunk_text(cleaned_text, document_id)
        
        # 5. Extract Structured Entities & Merge metadata into chunks
        if status_callback:
            await status_callback("EXTRACTING_ENTITIES", len(chunks))

        total_entities_extracted = 0
        for chunk in chunks:
            chunk.metadata.update(extracted_meta)
            chunk.metadata["filename"] = metadata.get("filename", "")
            chunk.metadata["document_id"] = document_id
            
            # Extract structured requirements / controls / risks from chunk
            entities = await extract_entities_from_chunk(chunk.text, chunk.metadata)
            chunk.metadata["entities"] = entities
            total_entities_extracted += len(entities)

        # 6. Embed
        if status_callback:
            await status_callback("EMBEDDING", len(chunks))
        embedded_chunks = await embed_chunks(chunks)
        
        # 7. Store / Index
        if status_callback:
            await status_callback("INDEXING", len(chunks))
        await upsert_embeddings(embedded_chunks)
        
        logger.info("RAG ingest pipeline successfully completed", document_id=document_id, chunk_count=len(chunks), entities_count=total_entities_extracted)
        
        return {
            "document_id": document_id,
            "status": "COMPLETED",
            "chunk_count": len(chunks),
            "entities_count": total_entities_extracted,
            "metadata": extracted_meta,
        }


    async def query(self, query_text: str, top_k: int = 5, metadata_filter: dict | None = None) -> dict:
        """
        Run the full RAG query pipeline.

        Returns:
            dict containing:
              - context_text: str
              - sources: list[dict]
              - chunks: list[dict] (reranked candidate chunks)
        """


        logger.info("RAG query pipeline started", query=query_text, top_k=top_k)
        
        # 1. Rewrite Query
        queries = await rewrite_query(query_text)
        
        # 2. Hybrid Search
        from apps.config import get_settings
        settings = get_settings()
        collection = settings.qdrant_collection
        
        candidates = await hybrid_search(
            queries=queries,
            collection=collection,
            top_k=top_k * 3,  # search wider first, then rerank
            metadata_filter=metadata_filter,
        )
        
        # 3. Rerank
        reranked_chunks = await rerank(
            query=query_text,
            candidates=candidates,
            top_n=top_k,
        )
        
        # 4. Context Builder
        context_result = await build_context(
            query=query_text,
            chunks=reranked_chunks,
        )
        
        logger.info("RAG query pipeline completed successfully", chunk_count=len(reranked_chunks))
        
        return {
            "context_text": context_result["context_text"],
            "sources": context_result["sources"],
            "chunks": reranked_chunks,
        }

