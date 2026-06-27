"""
apps/api/v1/documents.py
=========================
Document management endpoints.

POST /documents/upload  — upload a file (stored in MinIO, queued for ingestion)
GET  /documents         — list indexed documents
GET  /documents/{id}    — get document metadata
DELETE /documents/{id}  — delete document + vector embeddings

RAG ingest pipeline (from 01_System_Architecture.md):
  Upload → Parse → Clean → Metadata → Chunk → Embed → Qdrant
"""

from fastapi import APIRouter, File, UploadFile, status

from apps.dependencies import CurrentUserDep
from apps.schemas.documents import DocumentListResponse, DocumentRecord, DocumentUploadResponse

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document for ingestion",
    description=(
        "Upload a document (PDF, DOCX, TXT). It will be:\n\n"
        "1. Stored in **MinIO** object storage\n"
        "2. Queued as a **Celery** async task (workers/tasks/ingest_task.py)\n"
        "3. Processed through the RAG ingest pipeline: Parse → Clean → "
        "Metadata → Chunk → Embed → Qdrant\n\n"
        "**TODO**: Implement MinIO upload in infrastructure/minio_client.py.\n"
        "**TODO**: Enqueue Celery ingest task."
    ),
)
async def upload_document(
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="Document to ingest (PDF, DOCX, TXT)"),
) -> DocumentUploadResponse:
    raise NotImplementedError


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description=(
        "Return paginated list of documents with their ingestion status.\n\n"
        "**TODO**: Query PostgreSQL documents table."
    ),
)
async def list_documents(
    current_user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> DocumentListResponse:
    raise NotImplementedError


@router.get(
    "/{document_id}",
    response_model=DocumentRecord,
    summary="Get document metadata",
    description="**TODO**: Fetch document record from PostgreSQL.",
)
async def get_document(document_id: str, current_user: CurrentUserDep) -> DocumentRecord:
    raise NotImplementedError


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description=(
        "Delete a document from MinIO storage, PostgreSQL, and Qdrant vector store.\n\n"
        "**TODO**: Implement cascading delete across all stores."
    ),
)
async def delete_document(document_id: str, current_user: CurrentUserDep) -> None:
    raise NotImplementedError
