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

logger = structlog.get_logger(__name__)


async def rerank(
    query: str,
    candidates: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Rerank candidate chunks using a cross-encoder model.

    Args:
        query: The original user query.
        candidates: List of candidate chunks from hybrid_search.
        top_n: Number of top results to return after reranking.

    Returns:
        Reranked list of top_n chunks.

    TODO: Implement cross-encoder scoring with BAAI/bge-reranker-base.
    """
    logger.info("rerank called", candidate_count=len(candidates), top_n=top_n)
    raise NotImplementedError("Reranker not yet implemented")
