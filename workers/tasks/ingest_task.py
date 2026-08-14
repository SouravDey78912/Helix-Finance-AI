"""
workers/tasks/ingest_task.py
=============================
Celery task: Asynchronous document ingestion.
"""

import asyncio
from datetime import datetime, timezone
import os
import tempfile
import uuid
import structlog
from celery import Task
from sqlalchemy import select

from workers.celery_app import celery_app
from infrastructure.database import AsyncSessionLocal
from apps.models.document import Document
from infrastructure.minio_client import download_file

logger = structlog.get_logger(__name__)


async def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Async helper to update document status and metadata in PostgreSQL."""
    doc_uuid = uuid.UUID(document_id)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = status
            if status == "indexed":
                doc.indexed_at = datetime.now(timezone.utc)
                if chunk_count is not None:
                    doc.chunk_count = chunk_count
            if error_message:
                meta = dict(doc.metadata_dict)
                meta["error"] = error_message
                doc.metadata_dict = meta
            await session.commit()
            logger.info("Document database status updated", document_id=document_id, status=status)


@celery_app.task(
    name="workers.tasks.ingest_task.ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ingest",
)
def ingest_document(self: Task, document_id: str, object_name: str, metadata: dict) -> dict:
    """
    Celery task: Ingest a document through the RAG pipeline.
    """
    logger.info("ingest_document task started", document_id=document_id, object_name=object_name)

    # Establish or get async event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Update status to processing
    loop.run_until_complete(update_document_status(document_id, "processing"))

    try:
        # 1. Download file from MinIO to verify storage client integration
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, metadata.get("filename", "downloaded_file"))
            logger.info("Downloading file from MinIO", object_name=object_name, dest=local_path)
            loop.run_until_complete(download_file(object_name, local_path))
            
            file_size = os.path.getsize(local_path)
            logger.info("File successfully downloaded", path=local_path, size_bytes=file_size)

            # TODO: Integrate actual RAG pipeline:
            # Parse (rag/ingest/parser.py) -> Clean -> Metadata -> Chunk -> Embed -> Store (Qdrant)
            # Currently simulating with standard 5 chunks for verification
            mock_chunk_count = 5

        # 2. Update status to indexed
        loop.run_until_complete(
            update_document_status(document_id, "indexed", chunk_count=mock_chunk_count)
        )
        return {
            "document_id": document_id,
            "status": "indexed",
            "chunk_count": mock_chunk_count,
        }

    except Exception as e:
        logger.error("ingest_document task failed", document_id=document_id, error=str(e))
        loop.run_until_complete(
            update_document_status(document_id, "failed", error_message=str(e))
        )
        raise self.retry(exc=e)
