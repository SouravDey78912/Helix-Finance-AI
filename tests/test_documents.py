import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient

from apps.main import app
from apps.dependencies import get_current_user, get_db
from apps.models.user import User
from apps.models.document import Document

# ── Mock Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_dependencies():
    # Setup dummy user
    dummy_user = User(
        id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        email="testuser@helixfinance.ai",
        first_name="Test",
        last_name="User",
        is_active=True,
        roles=["user"],
    )
    # Override current user auth
    app.dependency_overrides[get_current_user] = lambda: dummy_user
    yield
    # Cleanup overrides
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("apps.api.v1.documents.upload_file_stream", new_callable=AsyncMock)
@patch("apps.api.v1.documents.ingest_document")
async def test_upload_document(
    mock_celery_task: MagicMock,
    mock_upload_stream: AsyncMock,
    client: AsyncClient,
):
    """POST /api/v1/documents/upload should upload, save metadata, and enqueue Celery task."""
    
    # Mock celery task .delay() returning a dummy task
    mock_task_instance = MagicMock()
    mock_task_instance.id = "mock-celery-task-uuid"
    mock_celery_task.delay.return_value = mock_task_instance

    # Mock database session
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Make request
    files = {"file": ("test.pdf", b"pdf content header data dummy", "application/pdf")}
    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
    )

    # Assert responses
    assert response.status_code == 202
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "pending"
    assert data["task_id"] == "mock-celery-task-uuid"
    assert "document_id" in data

    # Verify mocks were called
    mock_upload_stream.assert_called_once()
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_celery_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    """GET /api/v1/documents should return a paginated list of documents."""
    
    mock_db = AsyncMock()
    
    # Mock database results
    dummy_doc = Document(
        id=uuid.UUID("87654321-4321-8765-4321-876543210987"),
        filename="report.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        status="indexed",
        chunk_count=5,
        uploaded_at=datetime.now(timezone.utc),
        metadata_dict={"object_name": "87654321-4321-8765-4321-876543210987.pdf"}
    )
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [dummy_doc]
    mock_execute_result.scalar_one.return_value = 1
    
    mock_db.execute.return_value = mock_execute_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = await client.get("/api/v1/documents?page=1&page_size=20")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["documents"]) == 1
    assert data["documents"][0]["filename"] == "report.pdf"
    assert data["documents"][0]["status"] == "indexed"


@pytest.mark.asyncio
@patch("apps.api.v1.documents.delete_file", new_callable=AsyncMock)
async def test_delete_document(mock_delete_file: AsyncMock, client: AsyncClient):
    """DELETE /api/v1/documents/{id} should delete document from MinIO and PostgreSQL."""
    
    mock_db = AsyncMock()
    
    dummy_doc = Document(
        id=uuid.UUID("87654321-4321-8765-4321-876543210987"),
        filename="report.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        status="indexed",
        uploaded_at=datetime.now(timezone.utc),
        metadata_dict={"object_name": "report_object.pdf"}
    )
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = dummy_doc
    mock_db.execute.return_value = mock_execute_result
    app.dependency_overrides[get_db] = lambda: mock_db

    response = await client.delete("/api/v1/documents/87654321-4321-8765-4321-876543210987")
    
    assert response.status_code == 204
    mock_delete_file.assert_called_once_with("report_object.pdf")
    mock_db.delete.assert_called_once_with(dummy_doc)
    mock_db.commit.assert_called_once()
