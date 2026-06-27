"""
apps/dependencies.py
====================
Shared FastAPI dependencies injected into route handlers.
Each dependency is a stub; replace the body with real client calls
as you implement each infrastructure layer.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.config import Settings, get_settings
from security.jwt_handler import decode_access_token

# ── Settings dependency ───────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings)]

# ── Bearer token scheme ───────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: SettingsDep,
) -> dict:
    """
    Validate JWT and return the decoded token payload as the 'current user'.

    TODO: Look up the user in PostgreSQL once the DB layer is implemented.
    """
    payload = decode_access_token(credentials.credentials, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


CurrentUserDep = Annotated[dict, Depends(get_current_user)]


# ── Database dependency (stub) ────────────────────────────────────────────────

async def get_db():
    """
    Yield an async SQLAlchemy session.

    TODO: Implement once infrastructure/database.py session factory is ready.
    """
    raise NotImplementedError("Database session not yet implemented")
    yield  # noqa: unreachable — placeholder for async generator shape


# ── Redis dependency (stub) ───────────────────────────────────────────────────

async def get_redis():
    """
    Yield an async Redis client.

    TODO: Implement once infrastructure/redis_client.py is ready.
    """
    raise NotImplementedError("Redis client not yet implemented")
    yield
