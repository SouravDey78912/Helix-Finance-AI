"""
tests/test_health.py
=====================
Tests for the health check endpoints.
These are the only tests that should pass immediately (no dependencies needed).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    """GET /api/v1/health should return 200 OK."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "app_name" in data


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient):
    """GET /api/v1/health/ready should return 200 with degraded status."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    # Readiness returns degraded until all infra is connected
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


@pytest.mark.asyncio
async def test_docs_available(client: AsyncClient):
    """GET /docs should return 200 (Swagger UI available)."""
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_schema(client: AsyncClient):
    """GET /openapi.json should return valid schema."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "info" in schema
