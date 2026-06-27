"""
apps/schemas/aml.py
====================
Pydantic models for Anti-Money Laundering (AML) endpoints.
"""

from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransactionData(BaseModel):
    transaction_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3, examples=["USD"])
    sender_account: str
    receiver_account: str
    transaction_type: str = Field(..., examples=["wire_transfer", "cash_deposit"])
    metadata: dict = {}


class AMLAnalysisRequest(BaseModel):
    transaction: TransactionData
    include_explanation: bool = True


class AMLFlag(BaseModel):
    flag_type: str
    description: str
    severity: RiskLevel


class AMLAnalysisResponse(BaseModel):
    transaction_id: str
    risk_level: RiskLevel
    risk_score: float = Field(..., ge=0.0, le=1.0)
    flags: list[AMLFlag] = []
    explanation: str | None = None
    recommended_action: str | None = None
    sar_required: bool = False
