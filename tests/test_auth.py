"""
tests/test_auth.py
===================
Tests for authentication endpoints and security utilities.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient

from apps.config import get_settings
from security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from security.password import hash_password, verify_password


def test_password_hashing():
    """Verify that password hashing and verification works."""
    password = "supersecurepassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_token_handling():
    """Verify access and refresh token creation, expiration, and decoding."""
    settings = get_settings()
    user_data = {"sub": "user-uuid-1234", "email": "test@helixfinance.ai", "roles": ["user"]}
    
    # Access Token
    access_token = create_access_token(user_data, settings)
    decoded_access = decode_access_token(access_token, settings)
    assert decoded_access is not None
    assert decoded_access["sub"] == "user-uuid-1234"
    assert decoded_access["email"] == "test@helixfinance.ai"
    assert decoded_access["type"] == "access"
    assert "jti" in decoded_access
    
    # Refresh Token
    refresh_token = create_refresh_token({"sub": "user-uuid-1234"}, settings)
    decoded_refresh = decode_refresh_token(refresh_token, settings)
    assert decoded_refresh is not None
    assert decoded_refresh["sub"] == "user-uuid-1234"
    assert decoded_refresh["type"] == "refresh"
    assert "jti" in decoded_refresh


@pytest.mark.asyncio
async def test_login_incorrect_credentials(client: AsyncClient):
    """POST /auth/login with incorrect credentials should return 401."""
    # We patch the database query to return None (user not found)
    with patch("apps.api.v1.auth.Depends") as mock_depends:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@helixfinance.ai", "password": "wrongpassword123"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_google_login_invalid_token(client: AsyncClient):
    """POST /auth/google with invalid ID token should return 400."""
    response = await client.post(
        "/api/v1/auth/google",
        json={"id_token": "invalid-token-value"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Google ID token"


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    """POST /chat/query without Bearer token should return 403."""
    response = await client.post(
        "/api/v1/chat/query",
        json={"query": "What are the AML rules?"},
    )
    assert response.status_code == 403
