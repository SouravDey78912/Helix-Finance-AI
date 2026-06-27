"""
agents/guardrails.py
=====================
Guardrails — LangGraph node.

Responsibility: Apply safety and compliance filters to the verified
agent output before it is returned to the user.

Checks performed:
  - PII detection and masking (account numbers, SSN, etc.)
  - Hallucination detection (response grounded in retrieved context?)
  - Regulatory compliance (does the response create any liability?)
  - Toxicity / harmful content filtering

TODO: Integrate with a guardrails library (e.g., NeMo Guardrails, Guardrails AI).
TODO: If triggered, return a safe fallback response.
"""

import structlog

from agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)


async def guardrails_node(state: AgentState) -> AgentState:
    """
    Guardrails LangGraph node.

    Applies safety filters. If any guardrail is triggered:
      - Sets state['guardrails_triggered'] = True
      - Replaces state['final_response'] with a safe fallback

    TODO: Implement PII detection using spaCy or Presidio.
    TODO: Implement hallucination detection using RAG faithfulness score.
    """
    logger.info("guardrails_node called")
    raise NotImplementedError("Guardrails not yet implemented")
