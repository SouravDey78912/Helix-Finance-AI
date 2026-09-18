"""
apps/schemas/chat.py
=====================
Pydantic models for the Chat / Query endpoint.
"""

from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        examples=["What are the AML red flags for this transaction?"],
    )
    session_id: str | None = Field(None, description="Conversation session ID")
    context: dict[str, Any] | None = Field(None, description="Extra context metadata")


class SourceDocument(BaseModel):
    doc_id: str
    title: str
    chunk_text: str
    score: float = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] = {}


class AgentStep(BaseModel):
    step_number: int
    title: str
    action: str
    status: str = Field("completed", description="pending | running | completed | failed")
    detail: str | None = None


class PendingApproval(BaseModel):
    approval_id: str
    summary: str
    risk_level: str = Field("MEDIUM", description="HIGH | MEDIUM | LOW")
    gaps_count: int
    gaps: list[dict[str, Any]] = []
    recommendation: str


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    status: str = Field("COMPLETED", description="COMPLETED | PENDING_APPROVAL")
    sources: list[SourceDocument] = []
    agent_trace: list[str] = Field(
        default_factory=list,
        description="Ordered list of agent nodes that processed this query",
    )
    agent_steps: list[AgentStep] = []
    pending_approval: PendingApproval | None = None
    ag_ui_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="AG-UI Protocol standard event payload sequence (ag-ui.com specification)",
    )
    guardrails_triggered: bool = False
    latency_ms: float | None = None



class ApprovalRequest(BaseModel):
    session_id: str
    approval_id: str
    decision: str = Field("APPROVED", description="APPROVED | REJECTED | REVISE")
    feedback: str | None = None


class ApprovalResponse(BaseModel):
    session_id: str
    status: str = "COMPLETED"
    answer: str
    sources: list[SourceDocument] = []
    agent_steps: list[AgentStep] = []
    latency_ms: float | None = None


class SteerRequest(BaseModel):
    session_id: str
    steering_instruction: str | None = Field(None, description="Direct textual steering instruction for agent")
    document_ids: list[str] | None = Field(None, description="List of newly ingested evidence document IDs")

