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
    increment_retry: bool = False,
) -> None:
    """Async helper to update document stage status, timestamps, and retry counts in DB."""
    doc_uuid = uuid.UUID(document_id)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = status
            doc.stage_updated_at = datetime.now(timezone.utc)
            if status == "COMPLETED":
                doc.indexed_at = datetime.now(timezone.utc)
            if chunk_count is not None:
                doc.chunk_count = chunk_count
            if increment_retry:
                doc.retry_count = (doc.retry_count or 0) + 1
            if error_message is not None:
                doc.error_message = error_message
                meta = dict(doc.metadata_dict)
                meta["error"] = error_message
                doc.metadata_dict = meta
            elif status == "COMPLETED":
                doc.error_message = None
            await session.commit()
            logger.info("Document database status updated", document_id=document_id, status=status, retry_count=doc.retry_count)


@celery_app.task(
    name="workers.tasks.ingest_task.ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ingest",
)
def ingest_document(self: Task, document_id: str, object_name: str, metadata: dict) -> dict:
    """
    Celery task: Ingest a document through the granular RAG pipeline state machine.
    """
    logger.info("ingest_document task started", document_id=document_id, object_name=object_name, attempt=self.request.retries)

    # Establish or get async event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Transition to PROCESSING
    loop.run_until_complete(update_document_status(document_id, "PROCESSING"))

    async def stage_callback(stage: str, count: int | None = None):
        await update_document_status(document_id, stage, chunk_count=count)

    try:
        # 1. Download file from MinIO
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, metadata.get("filename", "downloaded_file"))
            logger.info("Downloading file from MinIO", object_name=object_name, dest=local_path)
            loop.run_until_complete(download_file(object_name, local_path))
            
            file_size = os.path.getsize(local_path)
            logger.info("File successfully downloaded", path=local_path, size_bytes=file_size)

            # 2. Run actual RAG pipeline:
            from rag.pipeline import RAGPipeline
            pipeline = RAGPipeline()
            if "content_type" not in metadata:
                metadata["content_type"] = "application/octet-stream"

            pipeline_result = loop.run_until_complete(
                pipeline.ingest(local_path, document_id, metadata, status_callback=stage_callback)
            )
            chunk_count = pipeline_result["chunk_count"]

        # 3. Update status to COMPLETED
        loop.run_until_complete(
            update_document_status(document_id, "COMPLETED", chunk_count=chunk_count)
        )
        return {
            "document_id": document_id,
            "status": "COMPLETED",
            "chunk_count": chunk_count,
        }

    except Exception as e:
        logger.error("ingest_document task error", document_id=document_id, error=str(e), retries=self.request.retries)
        
        is_last_attempt = self.request.retries >= self.max_retries
        if is_last_attempt:
            logger.error("Max retries reached. Marking document as FAILED.", document_id=document_id)
            loop.run_until_complete(
                update_document_status(document_id, "FAILED", error_message=str(e))
            )
            raise e
        else:
            logger.warning("Retrying document ingestion...", document_id=document_id, retry=self.request.retries + 1)
            loop.run_until_complete(
                update_document_status(document_id, "RETRYING", error_message=str(e), increment_retry=True)
            )
            raise self.retry(exc=e)
