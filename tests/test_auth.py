"""
tests/test_auth.py
===================
Tests for authentication endpoints.
These verify that:
  1. Unimplemented endpoints return 501 (as expected scaffolding behaviour)
  2. Protected routes reject unauthenticated requests with 403
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_not_implemented(client: AsyncClient):
    """POST /auth/login should return 501 until implemented."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@helixfinance.ai", "password": "supersecret"},
    )
    assert response.status_code == 501
    assert response.json()["status"] == "not_implemented"


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    """POST /chat/query without Bearer token should return 403."""
    response = await client.post(
        "/api/v1/chat/query",
        json={"query": "What are the AML rules?"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_aml_requires_auth(client: AsyncClient):
    """POST /aml/analyze without Bearer token should return 403."""
    response = await client.post(
        "/api/v1/aml/analyze",
        json={
            "transaction": {
                "transaction_id": "TXN-001",
                "amount": 15000,
                "currency": "USD",
                "sender_account": "ACC-001",
                "receiver_account": "ACC-002",
                "transaction_type": "wire_transfer",
            },
            "include_explanation": True,
        },
    )
    assert response.status_code == 403
