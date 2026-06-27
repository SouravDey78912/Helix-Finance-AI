"""
rag/query/rewriter.py
======================
Step 1 of RAG Query: Query Rewriting.

Expands and refines the user's query for better retrieval:
  - HyDE (Hypothetical Document Embedding) — generate a hypothetical answer
  - Step-back prompting — abstract to broader question
  - Multi-query expansion — generate N query variants

TODO: Implement using LiteLLM with query rewriting prompt template.
"""

import structlog

logger = structlog.get_logger(__name__)


async def rewrite_query(query: str) -> list[str]:
    """
    Rewrite the query into multiple variants for better recall.

    Returns:
        List of query strings (original + rewritten variants).

    TODO: Implement HyDE + multi-query expansion via LiteLLM.
    """
    logger.info("rewrite_query called", query=query)
    raise NotImplementedError("Query rewriter not yet implemented")
