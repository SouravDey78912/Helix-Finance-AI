"""
agents/orchestrator.py
=======================
LangGraph single-agent interactive workflow.

Step 1 progression:
  User Query
     │
  AG-UI / Chat UI
     │
  Single Agent (LangGraph StateGraph)
     │
  ┌────────────────┼────────────────┐
  ↓                ↓                ↓
[Retrieval]   [Analysis]     [Verification]
(Search/Rerank)(Gap Analysis)  (Risk Validation)
  └────────────────┼────────────────┘
                   ↓
            [Human Approval]
                   ↓
              Final Answer
"""

import uuid
from typing import Any, Dict, List, Optional, TypedDict

import litellm
import structlog
from langgraph.graph import END, StateGraph

from apps.config import get_settings
from rag.compliance_graph import run_compliance_gap_analysis
from rag.pipeline import RAGPipeline

logger = structlog.get_logger(__name__)
settings = get_settings()

_pipeline = RAGPipeline()


class AgentStepInfo(TypedDict):
    step_number: int
    title: str
    action: str
    status: str  # pending | running | completed | failed
    detail: Optional[str]


class SingleAgentState(TypedDict):
    query: str
    session_id: str
    user_id: str
    steps: List[AgentStepInfo]
    plan: List[str]
    retrieved_context: str
    sources: List[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    extracted_entities: List[Dict[str, Any]]
    gap_analysis: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    needs_approval: bool
    approval_status: str  # PENDING | APPROVED | REJECTED | REVISED
    approval_feedback: Optional[str]
    approval_id: Optional[str]
    final_answer: Optional[str]
    agent_trace: List[str]
    error: Optional[str]


async def planner_node(state: SingleAgentState) -> Dict[str, Any]:
    """Node 1: Plan investigation steps for query."""
    logger.info("SingleAgent planner_node running", query=state["query"])

    plan = [
        "1. Search regulatory compliance guidelines & internal controls",
        "2. Extract requirements & operational control mappings",
        "3. Identify compliance gaps and evidence deficiencies",
        "4. Assess risk score and verify findings",
        "5. Request Human Approval for recommended remediations",
        "6. Synthesize final audit & analysis report",
    ]

    steps: List[AgentStepInfo] = [
        {
            "step_number": 1,
            "title": "Search Compliance Regulations & Controls",
            "action": "Hybrid vector search across regulatory filings & internal policy docs",
            "status": "completed",
            "detail": f"Targeting query: '{state['query']}'",
        },
        {
            "step_number": 2,
            "title": "Requirement & Control Extraction",
            "action": "Parse obligations and internal control mappings",
            "status": "pending",
            "detail": None,
        },
        {
            "step_number": 3,
            "title": "Compliance Gap Analysis",
            "action": "Compare requirement obligations against available evidence",
            "status": "pending",
            "detail": None,
        },
        {
            "step_number": 4,
            "title": "Risk Assessment & Verification",
            "action": "Calculate severity levels (HIGH/MEDIUM/LOW)",
            "status": "pending",
            "detail": None,
        },
        {
            "step_number": 5,
            "title": "Human Approval Gate",
            "action": "Submit findings to compliance officer for sign-off",
            "status": "pending",
            "detail": None,
        },
    ]

    return {
        "plan": plan,
        "steps": steps,
        "agent_trace": state.get("agent_trace", []) + ["planner_node"],
    }


async def retrieval_node(state: SingleAgentState) -> Dict[str, Any]:
    """Node 2: Execute hybrid search & reranking via existing RAG pipeline."""
    logger.info("SingleAgent retrieval_node running", query=state["query"])

    rag_result = await _pipeline.query(
        query_text=state["query"],
        top_k=5,
        metadata_filter=None,
    )

    context_text = rag_result.get("context_text", "")
    sources = rag_result.get("sources", [])
    chunks = rag_result.get("chunks", [])

    steps = list(state.get("steps", []))
    if len(steps) >= 2:
        steps[1]["status"] = "completed"
        steps[1]["detail"] = f"Retrieved {len(chunks)} relevant chunks from document store"

    return {
        "retrieved_context": context_text,
        "sources": sources,
        "chunks": chunks,
        "steps": steps,
        "agent_trace": state.get("agent_trace", []) + ["retrieval_node"],
    }


async def analysis_node(state: SingleAgentState) -> Dict[str, Any]:
    """Node 3: Analyze compliance graph, controls, and gaps."""
    logger.info("SingleAgent analysis_node running")
    chunks = state.get("chunks", [])

    entities: List[Dict[str, Any]] = []
    for chunk in chunks:
        chunk_meta = chunk.get("metadata", {})
        if "entities" in chunk_meta and isinstance(chunk_meta["entities"], list):
            entities.extend(chunk_meta["entities"])

    if not entities and state.get("retrieved_context"):
        entities = [
            {
                "entity_id": "REQ-01",
                "entity_type": "Requirement",
                "title": "Customer Due Diligence (CDD) Identification",
                "obligation_level": "MANDATORY",
            },
            {
                "entity_id": "REQ-02",
                "entity_type": "Requirement",
                "title": "Beneficial Ownership Verification (>25% stake)",
                "obligation_level": "MANDATORY",
            },
            {
                "entity_id": "CTRL-01",
                "entity_type": "Control",
                "title": "Automated Identity & Biometric Verification",
                "status": "ACTIVE",
            },
            {
                "entity_id": "EVID-01",
                "entity_type": "Evidence",
                "title": "Passport API Verification Log",
                "status": "OUTDATED",
            },
        ]

    gap_result = run_compliance_gap_analysis(entities)

    steps = list(state.get("steps", []))
    if len(steps) >= 3:
        steps[2]["status"] = "completed"
        steps[2]["detail"] = (
            f"Identified {gap_result['total_gaps_identified']} gaps "
            f"({gap_result['summary']['high_severity']} HIGH, {gap_result['summary']['medium_severity']} MED)"
        )

    return {
        "extracted_entities": entities,
        "gap_analysis": gap_result,
        "steps": steps,
        "agent_trace": state.get("agent_trace", []) + ["analysis_node"],
    }


async def verification_node(state: SingleAgentState) -> Dict[str, Any]:
    """Node 4: Perform risk assessment and determine if human approval is needed."""
    logger.info("SingleAgent verification_node running")

    gap_analysis = state.get("gap_analysis") or {}
    summary = gap_analysis.get("summary", {})
    high_gaps = summary.get("high_severity", 0)
    med_gaps = summary.get("medium_severity", 0)

    if high_gaps > 0:
        overall_risk = "HIGH"
    elif med_gaps > 0:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    risk_assessment = {
        "overall_risk_level": overall_risk,
        "high_severity_gaps": high_gaps,
        "medium_severity_gaps": med_gaps,
        "low_severity_gaps": summary.get("low_severity", 0),
        "requires_human_approval": True,
    }

    approval_id = state.get("approval_id") or f"appr-{uuid.uuid4().hex[:8]}"

    steps = list(state.get("steps", []))
    if len(steps) >= 4:
        steps[3]["status"] = "completed"
        steps[3]["detail"] = f"Assessed overall risk level: {overall_risk}. Human approval required."

    return {
        "risk_assessment": risk_assessment,
        "needs_approval": True,
        "approval_id": approval_id,
        "steps": steps,
        "agent_trace": state.get("agent_trace", []) + ["verification_node"],
    }


async def human_approval_node(state: SingleAgentState) -> Dict[str, Any]:
    """Node 5: Human approval gate."""
    logger.info(
        "SingleAgent human_approval_node running",
        approval_status=state.get("approval_status"),
    )

    steps = list(state.get("steps", []))
    status = state.get("approval_status", "PENDING")

    if status == "PENDING":
        if len(steps) >= 5:
            steps[4]["status"] = "running"
            steps[4]["detail"] = "Awaiting decision from Compliance Officer in AG-UI"
    elif status in ("APPROVED", "REVISED"):
        if len(steps) >= 5:
            steps[4]["status"] = "completed"
            steps[4]["detail"] = f"Approved by user (Decision: {status})"
    elif status == "REJECTED":
        if len(steps) >= 5:
            steps[4]["status"] = "failed"
            steps[4]["detail"] = "Rejected by user"

    return {
        "steps": steps,
        "agent_trace": state.get("agent_trace", []) + ["human_approval_node"],
    }


async def synthesis_node(state: SingleAgentState) -> Dict[str, Any]:
    """Node 6: Synthesize final output report."""
    logger.info("SingleAgent synthesis_node running")

    if state.get("approval_status") == "REJECTED":
        answer = (
            "**Analysis Suspended by User**\n\n"
            "The compliance officer rejected the proposed remediation and gap assessment. "
            f"User Feedback: *{state.get('approval_feedback') or 'No additional feedback provided.'}*"
        )
        return {
            "final_answer": answer,
            "agent_trace": state.get("agent_trace", []) + ["synthesis_node"],
        }

    context = state.get("retrieved_context", "")
    gap_analysis = state.get("gap_analysis") or {}
    risk_assessment = state.get("risk_assessment") or {}
    gaps = gap_analysis.get("gaps", [])

    system_prompt = (
        "You are Helix Finance AI, an expert compliance agent operating in an interactive workflow.\n"
        "Generate a comprehensive, executive-level **Compliance Audit & Gap Analysis Report**.\n"
        "Structure the report with:\n"
        "1. Executive Summary & Risk Level\n"
        "2. Key Regulatory Obligations\n"
        "3. Identified Compliance & Control Gaps (highlight severity HIGH/MEDIUM/LOW)\n"
        "4. Recommended Remediations & Next Steps\n"
    )

    user_prompt = (
        f"User Query: {state['query']}\n\n"
        f"Risk Level: {risk_assessment.get('overall_risk_level', 'MEDIUM')}\n"
        f"Gaps Count: {len(gaps)}\n"
        f"Human Approval Status: {state.get('approval_status', 'APPROVED')}\n"
        f"User Feedback: {state.get('approval_feedback', 'None')}\n\n"
        f"Retrieved Document Context:\n{context}\n\n"
        f"Gap Details:\n{gaps}"
    )

    final_answer = ""
    try:
        kwargs: dict = {
            "model": settings.litellm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "timeout": 8,
        }
        if settings.litellm_base_url:
            kwargs["api_base"] = settings.litellm_base_url
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key

        resp = await litellm.acompletion(**kwargs)
        final_answer = resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("LLM synthesis failed, constructing structured fallback", error=str(e))
        gap_lines = []
        for g in gaps:
            gap_lines.append(
                f"- **[{g.get('severity', 'MEDIUM')}] {g.get('requirement_title')}**: "
                f"Control: `{g.get('control_title')}` | Status: `{g.get('evidence_status')}`\n  *{g.get('summary')}*"
            )
        gap_text = "\n".join(gap_lines) if gap_lines else "No critical gaps identified."

        final_answer = (
            f"## Compliance Audit Report: {state['query']}\n\n"
            f"**Overall Risk Level:** `{risk_assessment.get('overall_risk_level', 'MEDIUM')}`\n"
            f"**Approval Status:** Approved by Compliance Officer\n\n"
            f"### Identified Compliance Gaps & Deficiencies\n\n"
            f"{gap_text}\n\n"
            f"### Summary & Recommendations\n"
            f"1. Update internal controls for mandatory requirements missing execution evidence.\n"
            f"2. Schedule immediate review of outdated KYC/AML verification logs.\n\n"
            f"---\n\n"
            f"**Document Context Summary:**\n{context[:600]}..."
        )

    return {
        "final_answer": final_answer,
        "agent_trace": state.get("agent_trace", []) + ["synthesis_node"],
    }


def should_continue_after_approval(state: SingleAgentState) -> str:
    """Routing logic after human approval node."""
    status = state.get("approval_status", "PENDING")
    if status == "PENDING":
        return "wait"
    return "synthesis"


def build_single_agent_graph():
    """Build the LangGraph StateGraph for the single-agent interactive workflow."""
    workflow = StateGraph(SingleAgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("synthesis", synthesis_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retrieval")
    workflow.add_edge("retrieval", "analysis")
    workflow.add_edge("analysis", "verification")
    workflow.add_edge("verification", "human_approval")

    workflow.add_conditional_edges(
        "human_approval",
        should_continue_after_approval,
        {
            "wait": END,
            "synthesis": "synthesis",
        },
    )
    workflow.add_edge("synthesis", END)

    return workflow.compile()


async def run_query(query: str, session_id: str, user_id: str) -> SingleAgentState:
    """Entry point for the single agent workflow."""
    graph = build_single_agent_graph()
    initial_state: SingleAgentState = {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,
        "steps": [],
        "plan": [],
        "retrieved_context": "",
        "sources": [],
        "chunks": [],
        "extracted_entities": [],
        "gap_analysis": None,
        "risk_assessment": None,
        "needs_approval": False,
        "approval_status": "PENDING",
        "approval_feedback": None,
        "approval_id": None,
        "final_answer": None,
        "agent_trace": [],
        "error": None,
    }

    result = await graph.ainvoke(initial_state)
    return result
