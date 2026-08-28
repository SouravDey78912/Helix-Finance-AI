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
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
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
    """
    client = await get_qdrant_client()
    points = []
    for item in embeddings:
        points.append(
            PointStruct(
                id=item["chunk_id"],
                vector=item["embedding"],
                payload=item["metadata"],
            )
        )
    
    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )
    logger.info("Upserted points to Qdrant", count=len(points), collection=settings.qdrant_collection)


async def search_vectors(
    query_vector: list[float],
    top_k: int = 20,
    filter_conditions: dict | None = None,
) -> list[dict]:
    """
    Search for similar vectors in Qdrant.
    """
    client = await get_qdrant_client()
    
    # Construct filters if provided
    qdrant_filter = None
    if filter_conditions:
        must_conditions = []
        for key, val in filter_conditions.items():
            if val is not None:
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=val),
                    )
                )
        if must_conditions:
            qdrant_filter = Filter(must=must_conditions)

    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        query_filter=qdrant_filter,
    )

    return [
        {
            "chunk_id": str(hit.id),
            "score": hit.score,
            "text": hit.payload.get("text", "") if hit.payload else "",
            "metadata": hit.payload or {},
        }
        for hit in results
    ]

