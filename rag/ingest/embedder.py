"""
rag/ingest/embedder.py
=======================
Step 5 of RAG Ingest: Embedding Generation.

Generates dense vector embeddings for text chunks.

Local:       BAAI/bge-small-en-v1.5 via sentence-transformers (free, runs offline)
Production:  Managed embedding service (Azure OpenAI embeddings, Cohere, etc.)
TODO: Batch embed chunks for efficiency.
TODO: Cache embeddings in Redis to avoid re-embedding unchanged chunks.
"""
import httpx
import structlog

from rag.ingest.chunker import TextChunk
from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


HF_EMBEDDING_URL = (
    "https://router.huggingface.co/"
    "hf-inference/models/"
    "sentence-transformers/all-MiniLM-L6-v2/"
    "pipeline/feature-extraction"
)


async def embed_chunks(chunks: list[TextChunk]) -> list[dict]:
    """
    Generate embeddings using Hugging Face hosted inference.

    Model:
        sentence-transformers/all-MiniLM-L6-v2

    Output:
        384-dimensional embeddings.
    """

    logger.info(
        "embed_chunks called",
        chunk_count=len(chunks),
    )

    if not chunks:
        return []

    if not settings.hf_token:
        raise RuntimeError("HF_TOKEN is not configured")

    texts = [chunk.text for chunk in chunks]

    headers = {
        "Authorization": f"Bearer {settings.hf_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": texts,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                HF_EMBEDDING_URL,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        embeddings = response.json()

        results = []

        for chunk, embedding in zip(chunks, embeddings):
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "embedding": embedding,
                    "text": chunk.text,
                    "metadata": {
                        **chunk.metadata,
                        "text": chunk.text,
                    },
                }
            )

        logger.info(
            "Embeddings successfully generated",
            count=len(results),
            dimensions=len(results[0]["embedding"]),
        )

        return results

    except Exception:
        logger.exception(
            "Failed to generate Hugging Face embeddings",
            chunk_count=len(chunks),
        )
        raise