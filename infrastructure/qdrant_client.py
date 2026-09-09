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
    Called automatically before every upsert operation.
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
    Auto-creates the collection if it does not exist yet.
    """
    client = await get_qdrant_client()
    await ensure_collection_exists(client)
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
    Search Qdrant for chunks similar to the supplied query vector.

    The query vector must be generated using the same embedding model
    and embedding dimension that were used during document ingestion.

    Args:
        query_vector:
            Dense embedding vector generated from the user's query.

        top_k:
            Maximum number of similar chunks to retrieve.

        filter_conditions:
            Optional metadata filters to apply to the Qdrant search.

    Returns:
        List of matching chunks containing:
            - chunk_id
            - score
            - text
            - metadata
    """

    logger.info(
        "Qdrant vector search started",
        collection=settings.qdrant_collection,
        top_k=top_k,
        vector_dimension=len(query_vector),
    )

    if not query_vector:
        logger.warning("Empty query vector supplied to Qdrant")
        return []

    # all-MiniLM-L6-v2 produces 384-dimensional embeddings.
    expected_dimension = settings.embedding_dimension

    if len(query_vector) != expected_dimension:
        raise ValueError(
            f"Invalid query vector dimension: "
            f"expected={expected_dimension}, "
            f"received={len(query_vector)}"
        )

    client = await get_qdrant_client()

    # ------------------------------------------------------------------
    # Construct Qdrant metadata filter.
    #
    # Example:
    #     {
    #         "document_id": "abc",
    #         "user_id": "xyz"
    #     }
    #
    # becomes:
    #
    #     Filter(
    #         must=[
    #             FieldCondition(...),
    #             FieldCondition(...)
    #         ]
    #     )
    # ------------------------------------------------------------------

    qdrant_filter = None

    if filter_conditions:
        must_conditions = []

        for key, value in filter_conditions.items():
            if value is None:
                continue

            must_conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )

        if must_conditions:
            qdrant_filter = Filter(
                must=must_conditions
            )

    # ------------------------------------------------------------------
    # Query Qdrant.
    #
    # query_points() is the current Qdrant client API.
    #
    # with_payload=True is required because we need the stored chunk
    # text and metadata for the RAG context.
    #
    # with_vectors=False avoids returning the potentially large vectors
    # since we don't need them after similarity search.
    # ------------------------------------------------------------------

    try:
        response = await client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
            with_vectors=False,
        )

    except Exception:
        logger.exception(
            "Qdrant vector search failed",
            collection=settings.qdrant_collection,
            top_k=top_k,
        )
        raise

    # ------------------------------------------------------------------
    # Convert Qdrant ScoredPoint objects into application-level dicts.
    # ------------------------------------------------------------------

    results = []

    for hit in response.points:
        payload = hit.payload or {}

        results.append(
            {
                "chunk_id": str(hit.id),
                "score": float(hit.score),
                "text": payload.get("text", ""),
                "metadata": payload,
            }
        )

    logger.info(
        "Qdrant vector search completed",
        collection=settings.qdrant_collection,
        result_count=len(results),
    )

    return results

