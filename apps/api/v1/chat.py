"""
apps/api/v1/chat.py
====================
Chat / Query endpoint.

POST /chat/query — main RAG query entry point.

Pipeline:
  1. RAG Hybrid Search + Rerank + Context Building
  2. LLM answer generation with full context
  3. Structured response with source citations
"""

import time
import uuid

import litellm
import structlog
from fastapi import APIRouter, HTTPException, status

from apps.config import get_settings
from apps.dependencies import CurrentUserDep
from apps.schemas.chat import ChatRequest, ChatResponse, SourceDocument
from rag.pipeline import RAGPipeline

router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()

_pipeline = RAGPipeline()

SYSTEM_PROMPT = """You are Helix Finance AI, an expert financial analyst and compliance assistant.

You have access to the user's uploaded financial documents, regulatory filings, and compliance reports.

Your task:
- Answer the user's question using ONLY the provided document context.
- Be accurate, concise, and cite sources using [Source N] notation.
- If the context does not contain enough information, say so clearly.
- For financial analysis, use precise language and highlight key figures.
- Do NOT fabricate information.

Format your response clearly with sections when appropriate.
"""


@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="RAG Document Query",
    description=(
        "Submit a natural language query against all indexed documents.\n\n"
        "**Pipeline**: Query → Rewrite → Hybrid Search → Rerank → Context → LLM → Answer"
    ),
)
async def query(payload: ChatRequest, current_user: CurrentUserDep) -> ChatResponse:
    start_ts = time.monotonic()
    session_id = payload.session_id or str(uuid.uuid4())

    logger.info(
        "chat_query received",
        user_id=str(current_user.id),
        session_id=session_id,
        query_length=len(payload.query),
    )

    # ── 1. RAG Retrieval ──────────────────────────────────────────────────────
    try:
        rag_result = await _pipeline.query(
            query_text=payload.query,
            top_k=5,
            metadata_filter=None,
        )
    except Exception as e:
        logger.error("RAG pipeline failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Retrieval pipeline error: {str(e)}",
        )

    context_text = rag_result.get("context_text", "")
    raw_sources = rag_result.get("sources", [])

    # ── 2. LLM Answer Generation ──────────────────────────────────────────────
    if context_text.strip():
        user_content = (
            f"Document Context:\n{context_text}\n\n"
            f"---\n\n"
            f"Question: {payload.query}"
        )
    else:
        user_content = (
            f"No relevant document context was found in the vector database.\n\n"
            f"Question: {payload.query}"
        )

    answer = ""
    try:
        kwargs: dict = {
            "model": settings.litellm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "timeout": 60,
        }
        if settings.litellm_base_url:
            kwargs["api_base"] = settings.litellm_base_url
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key

        llm_response = await litellm.acompletion(**kwargs)
        answer = llm_response.choices[0].message.content.strip()

    except Exception as e:
        logger.warning("LLM generation failed, returning context only", error=str(e))
        if context_text.strip():
            answer = (
                "I retrieved relevant information from your documents, but the "
                "language model is unavailable right now.\n\n"
                "**Retrieved Context:**\n\n" + context_text
            )
        else:
            answer = (
                "No relevant documents were found for your query, and the language "
                "model is currently unavailable."
            )

    # ── 3. Build sources ──────────────────────────────────────────────────────
    sources: list[SourceDocument] = []
    chunks = rag_result.get("chunks", [])
    for i, src in enumerate(raw_sources):
        chunk_text = ""
        if i < len(chunks):
            chunk_text = chunks[i].get("text", "")[:400]
        raw_score = 0.0
        if i < len(chunks):
            raw_score = chunks[i].get("rerank_score") or chunks[i].get("score") or 0.0
        sources.append(
            SourceDocument(
                doc_id=src.get("document_id", ""),
                title=src.get("filename", "Unknown"),
                chunk_text=chunk_text,
                score=round(float(raw_score), 4),
                metadata=src,
            )
        )

    latency_ms = round((time.monotonic() - start_ts) * 1000, 2)
    logger.info(
        "chat_query completed",
        session_id=session_id,
        source_count=len(sources),
        latency_ms=latency_ms,
    )

    return ChatResponse(
        answer=answer,
        session_id=session_id,
        sources=sources,
        agent_trace=["query_rewriter", "hybrid_search", "reranker", "context_builder", "llm"],
        guardrails_triggered=False,
        latency_ms=latency_ms,
    )

