"""
security/jwt_handler.py
========================
JWT creation and validation utilities.

Uses python-jose with HS256 (local) — upgrade to RS256 with
a managed key service (Azure Key Vault / AWS KMS) for production.

Production replacement: OAuth2 PKCE flow with managed IdP (Azure AD, Okta).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from apps.config import Settings


def create_access_token(data: dict[str, Any], settings: Settings) -> str:
    """
    Create a signed JWT access token.

    TODO: Add 'jti' (JWT ID) claim for token revocation support.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict[str, Any], settings: Settings) -> str:
    """
    Create a signed JWT refresh token with a longer TTL.

    TODO: Store refresh token hash in Redis for revocation support.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload.update({"exp": expire, "type": "refresh"})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any] | None:
    """
    Decode and validate a JWT access token.
    Returns the payload dict on success, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str, settings: Settings) -> dict[str, Any] | None:
    """
    Decode and validate a JWT refresh token.

    TODO: Check against Redis revocation list.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
