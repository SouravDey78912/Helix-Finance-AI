"""
apps/api/v1/router.py
======================
Aggregates all v1 API routers into a single include.
"""

from fastapi import APIRouter

from apps.api.v1 import auth, chat, documents, aml, kyc, compliance, health

v1_router = APIRouter()

v1_router.include_router(health.router, prefix="/health", tags=["Health"])
v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(chat.router, prefix="/chat", tags=["Chat / Query"])
v1_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
v1_router.include_router(aml.router, prefix="/aml", tags=["AML"])
v1_router.include_router(kyc.router, prefix="/kyc", tags=["KYC"])
v1_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
