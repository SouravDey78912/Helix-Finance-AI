"""
agents/ag_ui_protocol.py
========================
AG-UI (Agent User Interaction Protocol) Implementation using official `ag-ui-protocol` package.
Reference: https://docs.ag-ui.com/introduction

Uses ag_ui.core and ag_ui.encoder for standard event generation, SSE stream encoding,
and Human-in-the-Loop interrupts.
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from ag_ui.core import (
    Interrupt,
    RunFinishedEvent,
    RunFinishedSuccessOutcome,
    RunStartedEvent,
    StepFinishedEvent,
    StepStartedEvent,
    ToolCallArgsEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder

_encoder = EventEncoder()


def encode_event(evt) -> str:
    """Encode an AG-UI core event into SSE data format string."""
    return _encoder.encode(evt)


def create_run_started(thread_id: str, run_id: str) -> RunStartedEvent:
    return RunStartedEvent(thread_id=thread_id, run_id=run_id)


def create_step_started(thread_id: str, run_id: str, step_name: str) -> StepStartedEvent:
    return StepStartedEvent(thread_id=thread_id, run_id=run_id, step_name=step_name)


def create_step_finished(thread_id: str, run_id: str, step_name: str) -> StepFinishedEvent:
    return StepFinishedEvent(thread_id=thread_id, run_id=run_id, step_name=step_name)



def create_tool_call_start(thread_id: str, run_id: str, tool_call_id: str, name: str) -> ToolCallStartEvent:
    return ToolCallStartEvent(thread_id=thread_id, run_id=run_id, tool_call_id=tool_call_id, name=name)


def create_tool_call_result(thread_id: str, run_id: str, tool_call_id: str, result: str) -> ToolCallResultEvent:
    return ToolCallResultEvent(thread_id=thread_id, run_id=run_id, tool_call_id=tool_call_id, result=result)


def create_interrupt(
    thread_id: str,
    run_id: str,
    interrupt_id: str,
    reason: str,
    payload: Dict[str, Any],
) -> Interrupt:
    return Interrupt(
        id=interrupt_id,
        reason=reason,
    )



def create_run_finished(thread_id: str, run_id: str) -> RunFinishedEvent:
    return RunFinishedEvent(
        thread_id=thread_id,
        run_id=run_id,
        outcome=RunFinishedSuccessOutcome(),
    )


def build_ag_ui_protocol_event_sequence(
    thread_id: str,
    run_id: str,
    query: str,
    steps_data: List[Dict[str, Any]],
    needs_approval: bool,
    approval_status: str,
    gap_analysis: Optional[Dict[str, Any]],
    risk_assessment: Optional[Dict[str, Any]],
    approval_id: Optional[str],
    final_answer: Optional[str],
) -> List[Dict[str, Any]]:
    """Build serialized event dictionaries conforming to ag-ui-protocol package."""
    events = []

    # 1. Run Started
    run_started = create_run_started(thread_id, run_id)
    events.append({"type": run_started.type, "threadId": thread_id, "runId": run_id})

    # 2. Steps
    for step in steps_data:
        step_title = step.get("title", f"Step-{step.get('step_number', 1)}")
        s_start = create_step_started(thread_id, run_id, step_title)
        events.append({
            "type": s_start.type,
            "threadId": thread_id,
            "runId": run_id,
            "stepName": step_title,
            "action": step.get("action"),
            "status": step.get("status", "completed"),
            "detail": step.get("detail"),
        })

        if step.get("status") == "completed":
            s_end = create_step_finished(thread_id, run_id, step_title)
            events.append({
                "type": s_end.type,
                "threadId": thread_id,
                "runId": run_id,
                "stepName": step_title,
            })

    # 3. Interrupt if pending
    if needs_approval and approval_status == "PENDING":
        gaps = (gap_analysis or {}).get("gaps", [])
        risk_level = (risk_assessment or {}).get("overall_risk_level", "MEDIUM")
        int_id = approval_id or f"appr-{uuid.uuid4().hex[:8]}"

        payload_data = {
            "risk_level": risk_level,
            "gaps_count": len(gaps),
            "gaps": gaps,
            "actions": [
                {"action_id": "APPROVED", "label": "Approve & Synthesize Report"},
                {"action_id": "REVISED", "label": "Request Revision"},
                {"action_id": "REJECTED", "label": "Reject Findings"},
            ],
        }
        int_evt = create_interrupt(
            thread_id=thread_id,
            run_id=run_id,
            interrupt_id=int_id,
            reason="Compliance Gap Sign-Off Required",
            payload=payload_data,
        )
        events.append({
            "type": "INTERRUPT",
            "threadId": thread_id,
            "runId": run_id,
            "interruptId": int_id,
            "reason": int_evt.reason,
            "payload": payload_data,
        })

    elif final_answer:
        run_fin = create_run_finished(thread_id, run_id)
        events.append({"type": run_fin.type, "threadId": thread_id, "runId": run_id})

    return events
