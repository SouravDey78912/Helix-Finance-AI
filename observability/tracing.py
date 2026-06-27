"""
observability/tracing.py
=========================
Langfuse LLM observability tracing setup.

Local:       Langfuse self-hosted in Docker Compose (free)
Production:  Langfuse Cloud / self-hosted

Langfuse captures:
  - LLM prompt + completion pairs
  - Token usage and cost
  - Latency per LLM call
  - Full agent trace (span per LangGraph node)
  - RAG retrieval spans

TODO: Wrap LiteLLM calls with Langfuse callbacks.
TODO: Add span per LangGraph node in orchestrator.py.
TODO: Set up Phoenix for RAG-specific debugging (retrieval quality).
"""

import structlog

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def init_langfuse():
    """
    Initialise the Langfuse client.

    TODO: Import langfuse and create Langfuse(secret_key=..., public_key=...) client.
    TODO: Return the client for use as a LangChain callback handler.
    TODO: Integrate with LiteLLM's callback system.
    """
    if not settings.langfuse_secret_key:
        logger.warning(
            "Langfuse secret key not set — LLM tracing disabled. "
            "Set LANGFUSE_SECRET_KEY in .env to enable."
        )
        return None

    logger.info("Langfuse tracing initialised", host=settings.langfuse_host)
    raise NotImplementedError("Langfuse tracing not yet implemented")


def get_langfuse_callback():
    """
    Return a Langfuse callback handler for LangChain/LangGraph.

    TODO: Return LangfuseCallbackHandler instance.
    """
    raise NotImplementedError("Langfuse callback not yet implemented")
