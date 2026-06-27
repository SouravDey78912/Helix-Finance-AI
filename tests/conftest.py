"""
tests/conftest.py
==================
Shared pytest fixtures for the Helix Finance AI test suite.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.main import app
from apps.config import get_settings


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
