"""
apps/schemas/documents.py
==========================
Pydantic models for Document Management endpoints.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    task_id: str = Field(..., description="Celery task ID for async ingestion")
    message: str = "Document queued for processing"


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    uploaded_at: datetime
    indexed_at: datetime | None = None
    stage_updated_at: datetime | None = None
    retry_count: int = 0
    error_message: str | None = None
    chunk_count: int | None = None
    metadata: dict = {}


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord]
    total: int
    page: int
    page_size: int
