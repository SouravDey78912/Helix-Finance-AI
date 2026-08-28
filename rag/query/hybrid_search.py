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

import litellm
import structlog
from apps.config import get_settings
from infrastructure.qdrant_client import search_vectors

logger = structlog.get_logger(__name__)
settings = get_settings()


async def hybrid_search(
    queries: list[str],
    collection: str,
    top_k: int = 20,
    metadata_filter: dict | None = None,
) -> list[dict]:
    """
    Run hybrid search across Qdrant collection using Reciprocal Rank Fusion.

    Returns:
        List of dicts with keys: chunk_id, text, score, metadata
    """
    logger.info("hybrid_search started", query_count=len(queries), top_k=top_k)

    # 1. Embed all query variants
    query_embeddings = []
    for query in queries:
        try:
            kwargs = {
                "model": settings.embedding_model,
                "input": [query],
            }
            if settings.litellm_base_url:
                kwargs["api_base"] = settings.litellm_base_url
            if settings.openai_api_key:
                kwargs["api_key"] = settings.openai_api_key

            response = await litellm.aembedding(**kwargs)
            query_embeddings.append(response.data[0]["embedding"])
        except Exception as e:
            logger.error("Failed to embed query in search", query=query, error=str(e))
            # Continue with other queries if possible
            continue

    if not query_embeddings:
        logger.warning("No successful query embeddings generated, returning empty search results.")
        return []

    # 2. Query Qdrant for each query variant
    # Store list of results (list of lists of hits)
    all_results = []
    for q_emb in query_embeddings:
        try:
            results = await search_vectors(
                query_vector=q_emb,
                top_k=top_k * 2,  # retrieve slightly more to improve fusion recall
                filter_conditions=metadata_filter,
            )
            all_results.append(results)
        except Exception as e:
            logger.error("Qdrant vector search failed during hybrid search", error=str(e))

    # 3. Reciprocal Rank Fusion (RRF)
    # RRF score formula: RRF_Score = sum(1.0 / (k + rank))
    # constant k = 60 is standard
    k = 60
    rrf_scores = {}  # chunk_id -> rrf_score
    chunk_registry = {}  # chunk_id -> chunk data dict

    for query_result in all_results:
        for rank, chunk in enumerate(query_result, start=1):
            chunk_id = chunk["chunk_id"]
            if chunk_id not in chunk_registry:
                chunk_registry[chunk_id] = chunk
            
            # Update RRF score
            current_score = rrf_scores.get(chunk_id, 0.0)
            rrf_scores[chunk_id] = current_score + (1.0 / (k + rank))

    # Sort chunks by RRF score descending
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    # Compile top_k results
    final_results = []
    for cid in sorted_chunk_ids[:top_k]:
        chunk = chunk_registry[cid]
        # Include RRF score in dict
        chunk["rrf_score"] = rrf_scores[cid]
        final_results.append(chunk)

    logger.info("Hybrid search completed", retrieved_count=len(final_results))
    return final_results

