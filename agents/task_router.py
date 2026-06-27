"""
agents/task_router.py
======================
Task Router — LangGraph node.

Responsibility: Based on the plan from the Planner Agent, decide which
specialist agents to invoke and in what order.

Possible routes:
  - Retriever only (simple knowledge lookup)
  - Retriever + AML Agent
  - Retriever + KYC Agent
  - Retriever + Compliance Agent
  - All specialist agents (complex multi-domain query)

TODO: Implement routing logic using LLM or rule-based classifier.
TODO: Return conditional edge values for LangGraph routing.
"""

import structlog

from agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)

# Available specialist agents
AVAILABLE_AGENTS = ["retriever", "aml_agent", "kyc_agent", "compliance_agent"]


async def task_router_node(state: AgentState) -> AgentState:
    """
    Task Router LangGraph node.

    Analyses the plan and selects which agents to activate.
    Sets state['selected_agents'] with ordered list of agent names.

    TODO: Implement with LLM classifier or keyword-based routing.
    TODO: Support parallel agent execution via LangGraph Send API.
    """
    logger.info("task_router_node called", plan=state.get("plan"))
    raise NotImplementedError("Task Router not yet implemented")
