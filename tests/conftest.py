import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
import bcrypt

# Monkeypatch bcrypt to fix passlib test initialization bug in Python 3.12+
orig_hashpw = bcrypt.hashpw
def patched_hashpw(password, salt):
    if len(password) > 72:
        password = password[:72]
    return orig_hashpw(password, salt)
bcrypt.hashpw = patched_hashpw

from apps.main import app
from apps.config import get_settings
from apps.dependencies import get_db, get_redis


@pytest.fixture(scope="session")
def settings():
    """Return test settings."""
    return get_settings()


@pytest.fixture
async def client():
    """Async test client wrapping the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def mock_external_deps():
    """Automatically mock Redis and DB dependencies for all tests unless overridden."""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    
    # Configure mock_db.execute to return a result that behaves like an empty query by default
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar_one.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    yield
    app.dependency_overrides.clear()
