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


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[SourceDocument] = []
    agent_trace: list[str] = Field(
        default_factory=list,
        description="Ordered list of agents that processed this query",
    )
    guardrails_triggered: bool = False
    latency_ms: float | None = None
