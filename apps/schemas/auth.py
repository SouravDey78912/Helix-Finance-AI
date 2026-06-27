"""
apps/schemas/auth.py
====================
Pydantic models for Authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["analyst@helixfinance.ai"])
    password: str = Field(..., min_length=8, examples=["supersecret123"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token TTL in seconds")


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    user_id: str
    email: str
    roles: list[str]
