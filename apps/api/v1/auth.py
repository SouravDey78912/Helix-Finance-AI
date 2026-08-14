"""
apps/api/v1/auth.py
====================
Authentication endpoints.
"""

from datetime import datetime, timezone
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.dependencies import CurrentUserDep, get_db, get_redis, SettingsDep
from apps.models.user import User
from apps.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserInfo,
)
from security.google_auth import verify_google_id_token
from security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from security.password import verify_password

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate with email + password and receive JWT access & refresh tokens.",
)
async def login(
    payload: LoginRequest,
    settings: SettingsDep,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Find user by email
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Generate tokens
    user_data = {"sub": str(user.id), "email": user.email, "roles": user.roles}
    access_token = create_access_token(user_data, settings)
    refresh_token = create_refresh_token({"sub": str(user.id)}, settings)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Google sign-in",
    description="Authenticate using a Google ID token. Auto-creates active users on first login.",
)
async def google_login(
    payload: GoogleLoginRequest,
    settings: SettingsDep,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Verify Google token
    google_payload = await verify_google_id_token(payload.id_token, settings)
    if not google_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google ID token",
        )

    email = google_payload.get("email")
    google_id = google_payload.get("sub")
    first_name = google_payload.get("given_name")
    last_name = google_payload.get("family_name")

    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token is missing email or sub claim",
        )

    # 1. Try to find user by google_id
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # 2. Try to find user by email (linked account setup)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Link Google account to existing email account
            user.google_id = google_id
            if not user.first_name:
                user.first_name = first_name
            if not user.last_name:
                user.last_name = last_name
            await db.commit()
            await db.refresh(user)
            logger.info("Linked existing user account to Google ID", user_id=str(user.id))
        else:
            # 3. Create new user
            user = User(
                email=email,
                google_id=google_id,
                first_name=first_name,
                last_name=last_name,
                hashed_password=None,  # Passwordless signup
                roles=["user"],
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Created new user via Google Sign-In", user_id=str(user.id))

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Generate tokens
    user_data = {"sub": str(user.id), "email": user.email, "roles": user.roles}
    access_token = create_access_token(user_data, settings)
    refresh_token = create_refresh_token({"sub": str(user.id)}, settings)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token (with Refresh Token Rotation).",
)
async def refresh_token(
    payload: RefreshRequest,
    settings: SettingsDep,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    # Decode refresh token
    token_data = decode_refresh_token(payload.refresh_token, settings)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = token_data.get("sub")
    jti = token_data.get("jti")

    if not user_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Check Redis revocation list
    is_revoked = await redis.get(f"blacklist:{jti}")
    if is_revoked:
        # Threat mitigation: If a revoked refresh token is reused, we can flag reuse detection
        logger.warning(
            "Revoked refresh token reuse detected! Potential session hijacking attempt.",
            user_id=user_id,
            jti=jti,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    # Check user active status in database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated or deleted",
        )

    # Revoke the used refresh token (Refresh Token Rotation)
    exp = token_data.get("exp")
    if exp:
        now = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - now)
        if ttl > 0:
            await redis.setex(f"blacklist:{jti}", ttl, "1")

    # Generate new pair of tokens
    user_data = {"sub": str(user.id), "email": user.email, "roles": user.roles}
    new_access_token = create_access_token(user_data, settings)
    new_refresh_token = create_refresh_token({"sub": str(user.id)}, settings)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout / revoke refresh token",
    description="Revoke the given refresh token by placing it on the Redis blacklist.",
)
async def logout(
    payload: LogoutRequest,
    settings: SettingsDep,
    redis: Redis = Depends(get_redis),
) -> None:
    token_data = decode_refresh_token(payload.refresh_token, settings)
    if token_data:
        jti = token_data.get("jti")
        exp = token_data.get("exp")
        if jti and exp:
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                await redis.setex(f"blacklist:{jti}", ttl, "1")
                logger.info("Successfully revoked refresh token on logout", jti=jti)
    return None


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user",
    description="Return the authenticated user's profile decoded from the JWT.",
)
async def get_me(current_user: CurrentUserDep) -> UserInfo:
    return UserInfo(
        user_id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        roles=current_user.roles,
    )
