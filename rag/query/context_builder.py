"""
rag/query/context_builder.py
=============================
Step 4 of RAG Query: Context Building.

Assembles the final prompt context from reranked chunks.

Responsibilities:
  - Format chunks into a readable context block
  - Apply token budget (ensure context fits LLM window)
  - Add source citations for each chunk
  - Structure context for the LLM prompt template

TODO: Implement context formatting with token counting (tiktoken).
TODO: Add source citation formatting.
TODO: Implement context compression for long documents (LLMLingua or similar).
"""

import structlog

logger = structlog.get_logger(__name__)


async def build_context(
    query: str,
    chunks: list[dict],
    max_tokens: int = 3000,
) -> dict:
    """
    Build the final LLM prompt context from reranked chunks.

    Returns:
        dict with keys:
          - context_text: str (formatted context for the LLM)
          - sources: list[dict] (citations for the response)
          - token_count: int

    TODO: Implement token counting and truncation.
    TODO: Format citations in a structured way.
    """
    logger.info("build_context called", chunk_count=len(chunks))
    raise NotImplementedError("Context builder not yet implemented")
