"""
apps/schemas/compliance.py
===========================
Pydantic models for Compliance Check endpoints.
"""

from enum import Enum
from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"


class ComplianceCheckRequest(BaseModel):
    entity_id: str = Field(..., description="ID of the entity (customer, transaction, etc.)")
    entity_type: str = Field(..., examples=["customer", "transaction", "institution"])
    regulations: list[str] = Field(
        default_factory=list,
        description="Specific regulation codes to check against (e.g. FATF, GDPR, BSA)",
        examples=[["FATF", "BSA"]],
    )
    context: dict = Field(default_factory=dict)


class ComplianceViolation(BaseModel):
    regulation: str
    rule_id: str
    description: str
    severity: str = Field(..., examples=["warning", "violation", "critical"])


class ComplianceCheckResponse(BaseModel):
    entity_id: str
    entity_type: str
    status: ComplianceStatus
    violations: list[ComplianceViolation] = []
    regulations_checked: list[str] = []
    summary: str | None = None
    next_review_date: str | None = None
