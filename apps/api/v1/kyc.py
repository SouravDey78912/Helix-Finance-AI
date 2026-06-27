"""
apps/api/v1/kyc.py
===================
Know Your Customer (KYC) endpoints.

POST /kyc/verify — run KYC verification for a customer.

Architecture: FastAPI → LangGraph Task Router → KYC Agent → Verifier → Guardrails
"""

from fastapi import APIRouter, status

from apps.dependencies import CurrentUserDep
from apps.schemas.kyc import KYCVerificationRequest, KYCVerificationResponse

router = APIRouter()


@router.post(
    "/verify",
    response_model=KYCVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify customer identity (KYC)",
    description=(
        "Submit customer data for KYC verification via the **KYC Specialist Agent**.\n\n"
        "Performs:\n"
        "- Document authenticity checks\n"
        "- Sanctions and PEP (Politically Exposed Person) screening\n"
        "- Adverse media screening\n"
        "- Risk scoring based on nationality and transaction profile\n\n"
        "**TODO**: Wire to agents/specialist/kyc_agent.py via orchestrator."
    ),
)
async def verify_customer(
    payload: KYCVerificationRequest,
    current_user: CurrentUserDep,
) -> KYCVerificationResponse:
    raise NotImplementedError
