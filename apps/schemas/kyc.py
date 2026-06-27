"""
apps/schemas/kyc.py
====================
Pydantic models for Know Your Customer (KYC) endpoints.
"""

from enum import Enum
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class CustomerData(BaseModel):
    customer_id: str
    full_name: str
    date_of_birth: str = Field(..., examples=["1990-01-15"])
    nationality: str = Field(..., min_length=2, max_length=2, examples=["US"])
    document_type: str = Field(..., examples=["passport", "national_id", "drivers_license"])
    document_number: str
    document_expiry: str = Field(..., examples=["2030-12-31"])


class KYCVerificationRequest(BaseModel):
    customer: CustomerData
    document_ids: list[str] = Field(
        default_factory=list,
        description="MinIO document IDs for uploaded identity documents",
    )


class KYCCheckResult(BaseModel):
    check_name: str
    passed: bool
    details: str | None = None


class KYCVerificationResponse(BaseModel):
    customer_id: str
    verification_status: VerificationStatus
    checks: list[KYCCheckResult] = []
    risk_score: float = Field(..., ge=0.0, le=1.0)
    notes: str | None = None
    verified_at: str | None = None
