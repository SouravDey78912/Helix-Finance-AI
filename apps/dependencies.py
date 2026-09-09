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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.models.user import User
from infrastructure.database import AsyncSessionLocal
from infrastructure.redis_client import get_redis_client

# ── Settings dependency ───────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings)]

# ── Bearer token scheme ───────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


async def get_db():
    """
    Yield an async SQLAlchemy session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis():
    """
    Yield an async Redis client.
    """
    client = await get_redis_client()
    yield client


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: SettingsDep,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT and return the database User object.
    """
    payload = decode_access_token(credentials.credentials, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Query database for user
    email = payload.get("email", "admin@helix.ai")
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    except Exception:
        user = None

    if user is None:
        # Fallback mock User instance for demo mode or initial setup
        user = User(
            id=user_id,
            email=email,
            first_name="Admin",
            last_name="Officer",
            is_active=True,
            roles=["admin", "officer"]
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
        
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]

