"""
apps/api/v1/chat.py
====================
Chat / Query & AG-UI (Agent User Interaction Protocol) Endpoints.
Reference: https://docs.ag-ui.com/introduction

POST /api/v1/chat/query — Single-agent workflow query with AG-UI protocol payload.
POST /api/v1/chat/approve — Resumes workflow with human approval decision.
GET /api/v1/chat/ag-ui/stream — Server-Sent Events (SSE) streaming AG-UI protocol events.
"""

import asyncio
import json
import time
import uuid
import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from apps.config import get_settings
from apps.dependencies import CurrentUserDep
from apps.schemas.chat import (
    AgentStep,
    ApprovalRequest,
    ApprovalResponse,
    ChatRequest,
    ChatResponse,
    PendingApproval,
    SourceDocument,
    SteerRequest,
)
from agents.single_agent import start_workflow, resume_workflow, steer_workflow, get_workflow_state
from agents.ag_ui_protocol import (
    build_ag_ui_protocol_event_sequence,
    encode_event,
    create_run_started,
    create_step_started,
    create_step_finished,
    create_interrupt,
    create_run_finished,
)


router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()


def _build_sources(raw_sources: list, chunks: list) -> list[SourceDocument]:
    sources: list[SourceDocument] = []
    for i, src in enumerate(raw_sources):
        chunk_text = ""
        if i < len(chunks):
            chunk_text = chunks[i].get("text", "")[:400]
        raw_score = 0.0
        if i < len(chunks):
            raw_score = chunks[i].get("rerank_score") or chunks[i].get("score") or 0.0
        sources.append(
            SourceDocument(
                doc_id=src.get("document_id", ""),
                title=src.get("filename", "Unknown Document"),
                chunk_text=chunk_text,
                score=round(float(raw_score), 4),
                metadata=src,
            )
        )
    return sources


def _build_agent_steps(steps_data: list) -> list[AgentStep]:
    result = []
    for item in steps_data:
        result.append(
            AgentStep(
                step_number=item.get("step_number", 1),
                title=item.get("title", ""),
                action=item.get("action", ""),
                status=item.get("status", "completed"),
                detail=item.get("detail"),
            )
        )
    return result


def _build_ag_ui_event_sequence(state: dict, run_id: str, latency_ms: float) -> list[dict]:
    """Build standardized AG-UI Protocol event envelope sequence using ag-ui-protocol package."""
    session_id = state.get("session_id", "session-default")
    return build_ag_ui_protocol_event_sequence(
        thread_id=session_id,
        run_id=run_id,
        query=state.get("query", ""),
        steps_data=state.get("steps", []),
        needs_approval=state.get("needs_approval", False),
        approval_status=state.get("approval_status", "PENDING"),
        gap_analysis=state.get("gap_analysis"),
        risk_assessment=state.get("risk_assessment"),
        approval_id=state.get("approval_id"),
        final_answer=state.get("final_answer"),
        investigation_status=state.get("investigation_status", "INVESTIGATING"),
        evidence_requests=state.get("evidence_requests", []),
    )


@router.post(
    "/steer",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Steer Agent Workflow with Evidence or User Guidance",
    description="Provide additional document evidence IDs or text guidance to steer an interrupted agent workflow.",
)
async def steer(payload: SteerRequest, current_user: CurrentUserDep) -> ChatResponse:
    start_ts = time.monotonic()
    run_id = f"run-{uuid.uuid4().hex[:8]}"

    logger.info(
        "human_steering submitted",
        session_id=payload.session_id,
        instruction=payload.steering_instruction,
        doc_count=len(payload.document_ids or []),
    )

    try:
        updated_state = await steer_workflow(
            session_id=payload.session_id,
            steering_instruction=payload.steering_instruction,
            document_ids=payload.document_ids,
        )
    except Exception as e:
        logger.error("Failed to steer single agent workflow", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow steering error: {str(e)}",
        )

    sources = _build_sources(updated_state.get("sources", []), updated_state.get("chunks", []))
    agent_steps = _build_agent_steps(updated_state.get("steps", []))
    latency_ms = round((time.monotonic() - start_ts) * 1000, 2)
    ag_ui_events = _build_ag_ui_event_sequence(updated_state, run_id, latency_ms)

    return ChatResponse(
        answer=updated_state.get("final_answer") or "Agent investigation resumed with new evidence/guidance.",
        session_id=payload.session_id,
        status=updated_state.get("investigation_status", "COMPLETED"),
        sources=sources,
        agent_trace=updated_state.get("agent_trace", []),
        agent_steps=agent_steps,
        ag_ui_events=ag_ui_events,
        guardrails_triggered=False,
        latency_ms=latency_ms,
    )



@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive Agent Query with AG-UI Protocol",
    description="Submit natural language query to run single-agent workflow formatted with AG-UI protocol events.",
)
async def query(payload: ChatRequest, current_user: CurrentUserDep) -> ChatResponse:
    start_ts = time.monotonic()
    session_id = payload.session_id or str(uuid.uuid4())
    run_id = f"run-{uuid.uuid4().hex[:8]}"

    logger.info(
        "chat_query received for AG-UI single agent workflow",
        user_id=str(current_user.id),
        session_id=session_id,
        run_id=run_id,
        query=payload.query,
    )

    try:
        state = await start_workflow(
            query=payload.query,
            session_id=session_id,
            user_id=str(current_user.id),
        )
    except Exception as e:
        logger.error("Single agent workflow failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Single agent workflow error: {str(e)}",
        )

    sources = _build_sources(state.get("sources", []), state.get("chunks", []))
    agent_steps = _build_agent_steps(state.get("steps", []))
    latency_ms = round((time.monotonic() - start_ts) * 1000, 2)
    ag_ui_events = _build_ag_ui_event_sequence(state, run_id, latency_ms)

    needs_approval = state.get("needs_approval", False)
    approval_status = state.get("approval_status", "PENDING")

    if needs_approval and approval_status == "PENDING":
        gap_analysis = state.get("gap_analysis") or {}
        risk_assessment = state.get("risk_assessment") or {}
        gaps = gap_analysis.get("gaps", [])
        risk_level = risk_assessment.get("overall_risk_level", "MEDIUM")

        pending_info = PendingApproval(
            approval_id=state.get("approval_id") or f"appr-{uuid.uuid4().hex[:8]}",
            summary=f"Identified {len(gaps)} compliance gaps across retrieved policy documents.",
            risk_level=risk_level,
            gaps_count=len(gaps),
            gaps=gaps,
            recommendation="Review and approve remediation plan to proceed with final report synthesis.",
        )

        return ChatResponse(
            answer=(
                "**Interactive Compliance Audit In Progress**\n\n"
                "The agent has retrieved document evidence, extracted requirements, and completed compliance gap analysis. "
                "**Human Approval is required** to sign off on findings before final report generation."
            ),
            session_id=session_id,
            status="PENDING_APPROVAL",
            sources=sources,
            agent_trace=state.get("agent_trace", []),
            agent_steps=agent_steps,
            pending_approval=pending_info,
            ag_ui_events=ag_ui_events,
            guardrails_triggered=False,
            latency_ms=latency_ms,
        )

    return ChatResponse(
        answer=state.get("final_answer") or "Workflow completed successfully.",
        session_id=session_id,
        status="COMPLETED",
        sources=sources,
        agent_trace=state.get("agent_trace", []),
        agent_steps=agent_steps,
        pending_approval=None,
        ag_ui_events=ag_ui_events,
        guardrails_triggered=False,
        latency_ms=latency_ms,
    )


@router.post(
    "/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Human Approval for Agent Workflow",
    description="Approve, revise, or reject the agent's gap analysis and risk assessment to finalize synthesis.",
)
async def approve(payload: ApprovalRequest, current_user: CurrentUserDep) -> ApprovalResponse:
    start_ts = time.monotonic()
    logger.info(
        "human_approval submitted",
        session_id=payload.session_id,
        approval_id=payload.approval_id,
        decision=payload.decision,
    )

    try:
        updated_state = await resume_workflow(
            session_id=payload.session_id,
            approval_id=payload.approval_id,
            decision=payload.decision,
            feedback=payload.feedback,
        )
    except Exception as e:
        logger.error("Failed to resume single agent workflow", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow resumption error: {str(e)}",
        )

    sources = _build_sources(updated_state.get("sources", []), updated_state.get("chunks", []))
    agent_steps = _build_agent_steps(updated_state.get("steps", []))
    latency_ms = round((time.monotonic() - start_ts) * 1000, 2)

    return ApprovalResponse(
        session_id=payload.session_id,
        status="COMPLETED",
        answer=updated_state.get("final_answer") or "Final analysis complete.",
        sources=sources,
        agent_steps=agent_steps,
        latency_ms=latency_ms,
    )


@router.get(
    "/ag-ui/stream",
    summary="AG-UI Protocol SSE Event Stream",
    description="Server-Sent Events (SSE) stream adhering to the AG-UI 1.0 Specification.",
)
async def ag_ui_stream(session_id: str, query_text: str, current_user: CurrentUserDep):
    """SSE streaming generator yielding AG-UI protocol event payloads."""
    run_id = f"run-{uuid.uuid4().hex[:8]}"

    async def event_generator():
        # Event 1: Run Started
        run_evt = create_run_started(session_id, run_id)
        yield encode_event(run_evt)
        await asyncio.sleep(0.1)

        # Run Workflow
        state = await start_workflow(query=query_text, session_id=session_id, user_id=str(current_user.id))

        # Stream Steps
        for step in state.get("steps", []):
            step_title = step.get("title", f"Step-{step.get('step_number', 1)}")
            s_start = create_step_started(session_id, run_id, step_title)
            yield encode_event(s_start)
            await asyncio.sleep(0.05)

            if step.get("status") == "completed":
                s_end = create_step_finished(session_id, run_id, step_title)
                yield encode_event(s_end)

        # Stream Interrupt if required
        if state.get("needs_approval") and state.get("approval_status") == "PENDING":
            gap_analysis = state.get("gap_analysis") or {}
            risk_assessment = state.get("risk_assessment") or {}
            gaps = gap_analysis.get("gaps", [])
            risk_level = risk_assessment.get("overall_risk_level", "MEDIUM")

            int_evt = create_interrupt(
                thread_id=session_id,
                run_id=run_id,
                interrupt_id=state.get("approval_id") or f"appr-{uuid.uuid4().hex[:8]}",
                reason="Compliance Gap Sign-Off Required",
                payload={
                    "risk_level": risk_level,
                    "gaps_count": len(gaps),
                    "gaps": gaps,
                },
            )
            yield encode_event(int_evt)
        elif state.get("final_answer"):
            run_fin = create_run_finished(session_id, run_id)
            yield encode_event(run_fin)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

