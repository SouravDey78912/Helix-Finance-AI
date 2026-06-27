"""
agents/planner.py
==================
Planner Agent — LangGraph node.

Responsibility: Decompose the user's query into a structured plan of sub-tasks.

Input:  AgentState with query
Output: AgentState with plan (list of sub-task descriptions)

TODO: Implement using LiteLLM call to decompose query.
TODO: Use structured output (Pydantic) to parse the plan.
TODO: Add Langfuse span for observability.
"""

import structlog

from agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)


async def planner_node(state: AgentState) -> AgentState:
    """
    Planner Agent LangGraph node.

    Decomposes the incoming query into an ordered list of sub-tasks,
    which the Task Router then uses to select specialist agents.

    Example plan output:
        [
            "Retrieve AML regulations for wire transfers > $10,000",
            "Analyze transaction pattern for structuring",
            "Check customer KYC status",
        ]

    TODO: Call LiteLLM with a planning prompt template.
    TODO: Parse structured JSON response into plan list.
    """
    logger.info("planner_node called", query=state["query"])
    raise NotImplementedError("Planner Agent not yet implemented")
