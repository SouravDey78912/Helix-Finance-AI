"""
infrastructure/qdrant_client.py
=================================
Qdrant vector database client.

Local:       Qdrant in Docker Compose (free, runs offline)
Production:  Qdrant Cloud / self-hosted Qdrant Cluster

Migration path: Change QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY env vars.
                No application code changes required.

TODO: Create collection with correct vector dimensions on startup.
TODO: Implement upsert, search, delete operations.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
import structlog

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_qdrant_client: AsyncQdrantClient | None = None


async def get_qdrant_client() -> AsyncQdrantClient:
    """Return the shared async Qdrant client (lazy-initialised)."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
        )
        logger.info("Qdrant client initialised", host=settings.qdrant_host)
    return _qdrant_client


async def ensure_collection_exists(client: AsyncQdrantClient) -> None:
    """
    Create the Qdrant collection if it does not exist.

    TODO: Call this from the app lifespan startup hook.
    """
    collections = await client.get_collections()
    existing = [c.name for c in collections.collections]
    if settings.qdrant_collection not in existing:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Qdrant collection created", collection=settings.qdrant_collection)


async def upsert_embeddings(embeddings: list[dict]) -> None:
    """
    Upsert a batch of embeddings into Qdrant.

    TODO: Implement using client.upsert() with PointStruct.
    """
    raise NotImplementedError("Qdrant upsert not yet implemented")


async def search_vectors(
    query_vector: list[float],
    top_k: int = 20,
    filter_conditions: dict | None = None,
) -> list[dict]:
    """
    Search for similar vectors in Qdrant.

    TODO: Implement using client.search() with optional filter.
    """
    raise NotImplementedError("Qdrant search not yet implemented")
