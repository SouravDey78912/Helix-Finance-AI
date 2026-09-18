"""
agents/single_agent.py
======================
Single Agent Workflow Runner & In-Memory Session State Store.

Coordinates graph invocation, human approval interrupts, and workflow resumption.
"""

from typing import Dict, Any, Optional
import structlog
from agents.orchestrator import SingleAgentState, build_single_agent_graph, run_query

logger = structlog.get_logger(__name__)

# Active in-memory session graph states
_ACTIVE_AGENT_SESSIONS: Dict[str, SingleAgentState] = {}


async def start_workflow(query: str, session_id: str, user_id: str) -> SingleAgentState:
    """
    Start the single-agent interactive workflow for a query.
    Executes through Retrieval -> Analysis -> Verification -> Human Approval Gate.
    """
    logger.info("Starting single agent workflow", session_id=session_id, user_id=user_id)
    state = await run_query(query=query, session_id=session_id, user_id=user_id)
    _ACTIVE_AGENT_SESSIONS[session_id] = state
    return state


async def resume_workflow(
    session_id: str,
    approval_id: str,
    decision: str,
    feedback: Optional[str] = None,
) -> SingleAgentState:
    """
    Resume an interrupted single-agent workflow after receiving human approval/decision.
    """
    logger.info(
        "Resuming single agent workflow with approval decision",
        session_id=session_id,
        approval_id=approval_id,
        decision=decision,
    )

    state = _ACTIVE_AGENT_SESSIONS.get(session_id)
    if not state:
        logger.warning("Session state not found in active memory, creating default state", session_id=session_id)
        state = {
            "query": "Compliance Investigation",
            "session_id": session_id,
            "user_id": "current_user",
            "steps": [],
            "plan": [],
            "retrieved_context": "",
            "sources": [],
            "chunks": [],
            "extracted_entities": [],
            "gap_analysis": None,
            "risk_assessment": None,
            "needs_approval": True,
            "approval_status": "PENDING",
            "approval_feedback": None,
            "approval_id": approval_id,
            "final_answer": None,
            "agent_trace": [],
            "error": None,
        }

    state["approval_status"] = decision.upper()
    state["approval_feedback"] = feedback

    graph = build_single_agent_graph()
    updated_state = await graph.ainvoke(state)
    _ACTIVE_AGENT_SESSIONS[session_id] = updated_state
    return updated_state


async def steer_workflow(
    session_id: str,
    steering_instruction: Optional[str] = None,
    document_ids: Optional[list[str]] = None,
) -> SingleAgentState:
    """
    Resume an evidence-interrupted single-agent workflow with user guidance or new evidence documents.
    """
    logger.info(
        "Steering single agent workflow with evidence/guidance",
        session_id=session_id,
        instruction=steering_instruction,
        doc_count=len(document_ids or []),
    )

    state = _ACTIVE_AGENT_SESSIONS.get(session_id)
    if not state:
        logger.warning("Session state not found for steering, unable to resume", session_id=session_id)
        raise ValueError(f"No active session state found for session_id: {session_id}")

    if steering_instruction:
        state["user_steering_instruction"] = steering_instruction
    if document_ids:
        state["new_document_ids"] = list(set(state.get("new_document_ids", []) + document_ids))

    state["investigation_status"] = "RESUMING"

    graph = build_single_agent_graph()
    updated_state = await graph.ainvoke(state)
    _ACTIVE_AGENT_SESSIONS[session_id] = updated_state
    return updated_state


def get_workflow_state(session_id: str) -> Optional[SingleAgentState]:
    """Retrieve current state for session."""
    return _ACTIVE_AGENT_SESSIONS.get(session_id)
