"""
rag/ingest/embedder.py
=======================
Step 5 of RAG Ingest: Embedding Generation.

Generates dense vector embeddings for text chunks.

Local:       BAAI/bge-small-en-v1.5 via sentence-transformers (free, runs offline)
Production:  Managed embedding service (Azure OpenAI embeddings, Cohere, etc.)

TODO: Load model using sentence-transformers or via LiteLLM embedding API.
TODO: Batch embed chunks for efficiency.
TODO: Cache embeddings in Redis to avoid re-embedding unchanged chunks.
"""

import litellm
import structlog

from rag.ingest.chunker import TextChunk
from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


async def embed_chunks(chunks: list[TextChunk]) -> list[dict]:
    """
    Generate embeddings for a list of text chunks.

    Returns:
        List of dicts with keys: chunk_id, embedding (list[float]), metadata
    """
    logger.info("embed_chunks called", chunk_count=len(chunks))
    if not chunks:
        return []

    texts = [chunk.text for chunk in chunks]

    try:
        # Call LiteLLM async embedding API
        kwargs = {
            "model": settings.embedding_model,
            "input": texts,
        }
        if settings.litellm_base_url:
            kwargs["api_base"] = settings.litellm_base_url
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key

        response = await litellm.aembedding(**kwargs)
        
        results = []
        for i, chunk in enumerate(chunks):
            embedding = response.data[i]["embedding"]
            results.append({
                "chunk_id": chunk.chunk_id,
                "embedding": embedding,
                "text": chunk.text,
                "metadata": {
                    **chunk.metadata,
                    "text": chunk.text,
                }
            })
            
        logger.info("Embeddings successfully generated", count=len(results))
        return results

    except Exception as e:
        logger.error("Failed to generate embeddings via LiteLLM", error=str(e))
        # For testing fallback or development, if embeddings call fails we can mock it
        # but in production we raise it. Let's raise the exception to let Celery retry.
        raise

