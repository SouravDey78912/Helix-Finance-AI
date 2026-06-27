"""
apps/api/v1/compliance.py
==========================
Compliance Check endpoints.

POST /compliance/check — run regulatory compliance check for an entity.

Architecture: FastAPI → LangGraph Task Router → Compliance Agent → Verifier → Guardrails
"""

from fastapi import APIRouter, status

from apps.dependencies import CurrentUserDep
from apps.schemas.compliance import ComplianceCheckRequest, ComplianceCheckResponse

router = APIRouter()


@router.post(
    "/check",
    response_model=ComplianceCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Regulatory compliance check",
    description=(
        "Check an entity (customer, transaction, or institution) against "
        "regulatory frameworks via the **Compliance Specialist Agent**.\n\n"
        "Supported regulations: FATF, BSA, GDPR, MiFID II, PSD2, and more.\n\n"
        "Process:\n"
        "1. Retrieve applicable regulations from RAG knowledge base\n"
        "2. Apply compliance rules to entity data\n"
        "3. Return violations, warnings, and recommended actions\n\n"
        "**TODO**: Wire to agents/specialist/compliance_agent.py via orchestrator."
    ),
)
async def compliance_check(
    payload: ComplianceCheckRequest,
    current_user: CurrentUserDep,
) -> ComplianceCheckResponse:
    raise NotImplementedError
