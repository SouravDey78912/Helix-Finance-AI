"""
apps/api/v1/aml.py
===================
Anti-Money Laundering (AML) endpoints.

POST /aml/analyze — run AML analysis on a transaction via the AML specialist agent.

Architecture: FastAPI → LangGraph Task Router → AML Agent → Verifier → Guardrails
"""

from fastapi import APIRouter, status

from apps.dependencies import CurrentUserDep
from apps.schemas.aml import AMLAnalysisRequest, AMLAnalysisResponse

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AMLAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze transaction for AML risk",
    description=(
        "Submit a financial transaction for Anti-Money Laundering risk analysis.\n\n"
        "The request is routed to the **AML Specialist Agent** via the LangGraph "
        "Task Router, which:\n"
        "- Searches the RAG knowledge base for relevant AML regulations\n"
        "- Applies rule-based and ML risk scoring\n"
        "- Flags suspicious patterns (structuring, layering, integration)\n"
        "- Returns SAR (Suspicious Activity Report) recommendation if needed\n\n"
        "**TODO**: Wire to agents/specialist/aml_agent.py via orchestrator."
    ),
)
async def analyze_transaction(
    payload: AMLAnalysisRequest,
    current_user: CurrentUserDep,
) -> AMLAnalysisResponse:
    raise NotImplementedError
