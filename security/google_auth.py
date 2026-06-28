"""
security/google_auth.py
========================
Verification of Google ID tokens using Google's public JWKS.
"""

from typing import Any
import httpx
import structlog
from jose import jwt, JWTError

from apps.config import Settings

logger = structlog.get_logger(__name__)

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Simple in-memory cache for Google JWKS to avoid calling the endpoint on every request
_jwks_cache: dict[str, Any] | None = None


async def get_google_jwks() -> dict[str, Any]:
    """Fetch Google's public JSON Web Key Set."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(GOOGLE_JWKS_URL, timeout=5.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


async def verify_google_id_token(id_token: str, settings: Settings) -> dict[str, Any] | None:
    """
    Verify and decode Google ID Token.
    Returns the decoded token payload on success, or None on failure.
    """
    # Developer convenience: Bypass verification in debug mode if Google Client ID is not configured
    if not settings.google_client_id:
        if settings.debug:
            logger.warning(
                "GOOGLE_CLIENT_ID is not configured. "
                "Bypassing Google ID token signature verification for development ease!"
            )
            try:
                # Decode without verification
                payload = jwt.get_unverified_claims(id_token)
                return payload
            except JWTError as e:
                logger.error("Failed to parse unverified claims from Google ID token", error=str(e))
                return None
        else:
            logger.error("GOOGLE_CLIENT_ID is missing in a non-debug environment")
            return None

    try:
        jwks = await get_google_jwks()
        # Decode and verify token
        payload = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer="https://accounts.google.com",
        )
        return payload
    except JWTError as e:
        logger.error("Google ID token verification failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error during Google ID token verification", error=str(e))
        return None
