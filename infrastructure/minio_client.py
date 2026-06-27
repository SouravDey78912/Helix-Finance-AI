"""
infrastructure/minio_client.py
================================
MinIO / S3-compatible object storage client.

Local:       MinIO in Docker Compose (free, S3-compatible)
Production:  AWS S3 / Azure Blob Storage / GCS

Migration path: Replace MINIO_ENDPOINT with S3 endpoint — no code changes
                (boto3 or minio SDK both support S3-compatible APIs).

Use cases:
  - Store raw uploaded documents before ingestion
  - Store processed document artifacts

TODO: Implement upload, download, delete, list operations.
TODO: Set up bucket policies for access control.
"""

from minio import Minio
from minio.error import S3Error
import structlog

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_minio_client: Minio | None = None


def get_minio_client() -> Minio:
    """Return the shared MinIO client (lazy-initialised)."""
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        logger.info("MinIO client initialised", endpoint=settings.minio_endpoint)
    return _minio_client


async def ensure_bucket_exists() -> None:
    """
    Create the MinIO bucket if it does not exist.

    TODO: Call from app lifespan startup.
    """
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
        logger.info("MinIO bucket created", bucket=settings.minio_bucket)


async def upload_file(file_path: str, object_name: str, content_type: str) -> str:
    """
    Upload a file to MinIO and return the object URL.

    TODO: Implement using client.fput_object().
    """
    raise NotImplementedError("MinIO upload not yet implemented")


async def download_file(object_name: str, destination_path: str) -> None:
    """
    Download a file from MinIO to a local path.

    TODO: Implement using client.fget_object().
    """
    raise NotImplementedError("MinIO download not yet implemented")


async def delete_file(object_name: str) -> None:
    """
    Delete a file from MinIO.

    TODO: Implement using client.remove_object().
    """
    raise NotImplementedError("MinIO delete not yet implemented")
