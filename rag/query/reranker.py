"""
rag/query/reranker.py
======================
Step 3 of RAG Query: Cross-Encoder Reranking.

Re-scores the top-K retrieved chunks using a cross-encoder model
(query, chunk) → relevance score. Much more accurate than bi-encoder
but slower — only applied to top-K candidates.

Local:      BAAI/bge-reranker-base (free, runs offline)
Production: Cohere Rerank API or Jina Rerank

TODO: Load BAAI/bge-reranker-base via sentence-transformers.
TODO: Rerank candidates and return top-N.
"""

import structlog
from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


async def rerank(
    query: str,
    candidates: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Rerank candidate chunks using a cross-encoder model or fallback scoring.

    Args:
        query: The original user query.
        candidates: List of candidate chunks from hybrid_search.
        top_n: Number of top results to return after reranking.

    Returns:
        Reranked list of top_n chunks.
    """
    logger.info("rerank called", candidate_count=len(candidates), top_n=top_n)
    if not candidates:
        return []

    # 1. Try sentence-transformers CrossEncoder dynamically
    try:
        from sentence_transformers import CrossEncoder
        # Use a standard lightweight reranker
        model = CrossEncoder("BAAI/bge-reranker-base")
        pairs = [[query, c["text"]] for c in candidates]
        scores = model.predict(pairs)
        
        for idx, score in enumerate(scores):
            candidates[idx]["rerank_score"] = float(score)
        
        # Sort by rerank score
        reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
        logger.info("Reranking completed using sentence-transformers CrossEncoder")
        return reranked[:top_n]
    except Exception as e:
        logger.warning(
            "sentence-transformers CrossEncoder not available or failed; using vector score / RRF fallback",
            error=str(e),
        )
        
        # Fallback 1: Sort by score/rrf_score
        for c in candidates:
            # Prefer score, then rrf_score
            c["rerank_score"] = c.get("score") or c.get("rrf_score") or 0.0
            
        reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
        return reranked[:top_n]

