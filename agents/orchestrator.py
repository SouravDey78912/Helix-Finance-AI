"""
agents/orchestrator.py
=======================
LangGraph graph builder and runner.

This is the central orchestration layer. The graph defines the exact
workflow from the architecture document:

  User Query
    │
    ▼
  Planner Agent         — decomposes the query into sub-tasks
    │
    ▼
  Task Router           — selects which specialist agent(s) to invoke
    │
    ├── Retriever       — hybrid RAG search (Qdrant)
    │
    ├── AML Agent       — anti-money laundering analysis
    ├── KYC Agent       — know-your-customer verification
    └── Compliance Agent— regulatory compliance check
         │
         ▼
       Verifier         — validates agent outputs for consistency
         │
         ▼
       Guardrails       — safety and compliance filters
         │
         ▼
       Response         — structured final response

TODO: Implement LangGraph StateGraph with real agent nodes.
TODO: Add Langfuse callbacks for tracing each node.
TODO: Add Phoenix for RAG debugging visibility.
"""

from typing import Any, TypedDict

import structlog

logger = structlog.get_logger(__name__)


class AgentState(TypedDict):
    """Shared state passed between all LangGraph nodes."""
    query: str
    session_id: str
    user_id: str
    plan: list[str]
    selected_agents: list[str]
    retrieved_context: list[dict]
    agent_outputs: dict[str, Any]
    verified_output: dict | None
    guardrails_triggered: bool
    final_response: str | None
    agent_trace: list[str]
    error: str | None


def build_graph():
    """
    Build the LangGraph StateGraph.

    TODO: Import and wire all agent node functions.
    TODO: Define conditional edges for task routing.
    TODO: Add error handling edges.

    Returns:
        CompiledGraph: A compiled LangGraph ready for invocation.
    """
    raise NotImplementedError(
        "LangGraph orchestrator not yet implemented. "
        "Implement node functions in agents/ and wire them here."
    )


async def run_query(query: str, session_id: str, user_id: str) -> AgentState:
    """
    Entry point for the orchestrator. Runs the full agent pipeline.

    TODO: Call build_graph().arun(initial_state) once graph is implemented.
    """
    raise NotImplementedError
