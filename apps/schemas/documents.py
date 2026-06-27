"""
apps/schemas/documents.py
==========================
Pydantic models for Document Management endpoints.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus = DocumentStatus.PENDING
    task_id: str = Field(..., description="Celery task ID for async ingestion")
    message: str = "Document queued for processing"


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    uploaded_at: datetime
    indexed_at: datetime | None = None
    chunk_count: int | None = None
    metadata: dict = {}


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord]
    total: int
    page: int
    page_size: int
