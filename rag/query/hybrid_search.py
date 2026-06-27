"""
rag/query/hybrid_search.py
===========================
Step 2 of RAG Query: Hybrid Search.

Combines dense (vector) and sparse (BM25/keyword) search for best recall.

Dense:  Qdrant vector search with BAAI/bge embeddings
Sparse: Qdrant sparse vectors (BM25 via FastEmbed) or keyword filter

TODO: Implement Qdrant hybrid search with RRF (Reciprocal Rank Fusion) fusion.
TODO: Support metadata filtering (jurisdiction, doc_type, date range).

Production: Same Qdrant API works at scale — just upgrade cluster size.
"""

import structlog

logger = structlog.get_logger(__name__)


async def hybrid_search(
    queries: list[str],
    collection: str,
    top_k: int = 20,
    metadata_filter: dict | None = None,
) -> list[dict]:
    """
    Run hybrid search (dense + sparse) across Qdrant collection.

    Returns:
        List of dicts with keys: chunk_id, text, score, metadata

    TODO: Embed queries using embedder.py.
    TODO: Run Qdrant query_points with both dense and sparse vectors.
    TODO: Apply RRF to merge results from multiple query variants.
    """
    logger.info("hybrid_search called", query_count=len(queries), top_k=top_k)
    raise NotImplementedError("Hybrid search not yet implemented")
