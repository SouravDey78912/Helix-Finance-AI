"""
apps/api/v1/chat.py
====================
Chat / Query endpoint.

POST /chat/query — main RAG query entry point

Architecture flow (from 01_System_Architecture.md):
  Authenticate → Authorize → Validate → Planner → Retrieval
  → Specialist Agents → Verification → Guardrails → Response
  → Audit Log → Metrics
"""

from fastapi import APIRouter, status

from apps.dependencies import CurrentUserDep
from apps.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="RAG Query",
    description=(
        "Submit a natural language query. The request flows through:\n\n"
        "1. **Planner Agent** — decomposes the query\n"
        "2. **Task Router** — selects specialist agents\n"
        "3. **Retriever** — hybrid vector search in Qdrant\n"
        "4. **Specialist Agents** — AML / KYC / Compliance analysis\n"
        "5. **Verifier** — validates agent outputs\n"
        "6. **Guardrails** — safety and compliance filters\n"
        "7. **Response** — structured answer with source citations\n\n"
        "**TODO**: Wire to agents/orchestrator.py (LangGraph graph)."
    ),
)
async def query(payload: ChatRequest, current_user: CurrentUserDep) -> ChatResponse:
    raise NotImplementedError
