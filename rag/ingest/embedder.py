"""
rag/ingest/embedder.py
======================

Step 5 of the RAG ingestion pipeline: Embedding Generation.

Generates dense vector embeddings for text chunks using the
Hugging Face hosted inference API.

Embedding model:
    sentence-transformers/all-MiniLM-L6-v2

Provider:
    Hugging Face Inference API

Vector dimensions:
    384

Architecture:
    Document chunks
        ↓
    Hugging Face Inference API
        ↓
    384-dimensional embeddings
        ↓
    Qdrant vector store

Important:
    The exact same embedding model and generation logic must be used
    during both document ingestion and query-time retrieval.

    Using different embedding models for documents and queries will
    produce incompatible vector spaces and result in poor or invalid
    similarity search results.

TODO:
    - Add configurable batch sizes for large documents.
    - Add retry/backoff for transient Hugging Face API failures.
    - Add embedding caching to avoid re-embedding unchanged chunks.
    - Add embedding model/version metadata for future migrations.
"""

import httpx
import structlog

from apps.config import get_settings
from rag.ingest.chunker import TextChunk

logger = structlog.get_logger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Hugging Face embedding configuration
# ---------------------------------------------------------------------------
#
# Hugging Face exposes sentence-transformers models through its
# feature-extraction pipeline.
#
# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
#
# Keep this model identical for:
#   1. Document/chunk ingestion
#   2. User query embedding
#
# Otherwise the vectors will not belong to the same embedding space.
# ---------------------------------------------------------------------------

HF_EMBEDDING_URL = (
    "https://router.huggingface.co/"
    "hf-inference/models/"
    "sentence-transformers/all-MiniLM-L6-v2/"
    "pipeline/feature-extraction"
)

EMBEDDING_DIMENSION = 384


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using Hugging Face.

    Args:
        texts:
            List of text strings to embed.

    Returns:
        A list of embedding vectors.

        Each vector contains 384 floating-point values because
        all-MiniLM-L6-v2 produces 384-dimensional embeddings.

    Raises:
        RuntimeError:
            If HF_TOKEN is not configured.

        httpx.HTTPStatusError:
            If Hugging Face returns an HTTP error.

        Exception:
            For any other embedding generation failure.
    """

    if not texts:
        return []

    if not settings.hf_token:
        raise RuntimeError("HF_TOKEN is not configured")

    headers = {
        "Authorization": f"Bearer {settings.hf_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": texts,
    }

    try:
        logger.info(
            "Generating Hugging Face embeddings",
            text_count=len(texts),
            model="sentence-transformers/all-MiniLM-L6-v2",
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                HF_EMBEDDING_URL,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        embeddings = response.json()

        # Validate the response before returning it.
        if not isinstance(embeddings, list):
            raise RuntimeError(
                "Unexpected Hugging Face embedding response format"
            )

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Embedding count mismatch: "
                f"expected={len(texts)}, received={len(embeddings)}"
            )

        # Validate the vector dimension.
        for index, embedding in enumerate(embeddings):
            if not isinstance(embedding, list):
                raise RuntimeError(
                    f"Invalid embedding format at index {index}"
                )

            if len(embedding) != EMBEDDING_DIMENSION:
                raise RuntimeError(
                    "Unexpected embedding dimension: "
                    f"expected={EMBEDDING_DIMENSION}, "
                    f"received={len(embedding)}"
                )

        logger.info(
            "Hugging Face embeddings generated successfully",
            count=len(embeddings),
            dimensions=EMBEDDING_DIMENSION,
        )

        return embeddings

    except Exception:
        logger.exception(
            "Failed to generate Hugging Face embeddings",
            text_count=len(texts),
        )
        raise


async def embed_chunks(chunks: list[TextChunk]) -> list[dict]:
    """
    Generate embeddings for document chunks.

    This function is used during the document ingestion pipeline.

    Pipeline:
        TextChunk
            ↓
        Hugging Face embedding API
            ↓
        384-dimensional vector
            ↓
        Chunk + vector + metadata

    Args:
        chunks:
            List of TextChunk objects produced by the chunking stage.

    Returns:
        List of dictionaries containing:

            chunk_id
            embedding
            text
            metadata
    """

    logger.info(
        "embed_chunks called",
        chunk_count=len(chunks),
    )

    if not chunks:
        return []

    texts = [chunk.text for chunk in chunks]

    embeddings = await generate_embeddings(texts)

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
        "Document chunk embeddings successfully generated",
        count=len(results),
        dimensions=EMBEDDING_DIMENSION,
    )

    return results