"""
apps/api/v1/auth.py
====================
Authentication endpoints.

POST /auth/login    — issue access + refresh tokens
POST /auth/refresh  — exchange refresh token for new access token
POST /auth/logout   — revoke refresh token
GET  /auth/me       — return current user info

Architecture note: JWT created by security/jwt_handler.py.
Production: replace JWT with OAuth2 / SSO (Azure AD, Okta).
"""

from fastapi import APIRouter, HTTPException, status

from apps.dependencies import CurrentUserDep
from apps.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserInfo,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description=(
        "Authenticate with email + password and receive JWT access & refresh tokens.\n\n"
        "**TODO**: Verify credentials against PostgreSQL users table.\n"
        "**TODO**: Hash comparison via security/password.py."
    ),
)
async def login(payload: LoginRequest) -> TokenResponse:
    raise NotImplementedError


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token.\n\n"
        "**TODO**: Validate refresh token against Redis token store (revocation list)."
    ),
)
async def refresh_token(payload: RefreshRequest) -> TokenResponse:
    raise NotImplementedError


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout / revoke refresh token",
    description=(
        "Revoke the given refresh token.\n\n"
        "**TODO**: Add token to Redis revocation list."
    ),
)
async def logout(payload: LogoutRequest) -> None:
    raise NotImplementedError


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user",
    description="Return the authenticated user's profile decoded from the JWT.",
)
async def get_me(current_user: CurrentUserDep) -> UserInfo:
    raise NotImplementedError
