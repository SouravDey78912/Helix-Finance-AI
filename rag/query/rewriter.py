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

import litellm
import json
import structlog
from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


async def rewrite_query(query: str) -> list[str]:
    """
    Rewrite the query into multiple variants for better recall.

    Returns:
        List of query strings (original + rewritten variants).
    """
    logger.info("rewrite_query called", query=query)
    
    # We always include the original query
    queries = [query]

    try:
        kwargs = {
            "model": settings.litellm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an AI search assistant. Rewrite the user's search query into exactly 3 search query variants. "
                        "These variants should capture different phrasing, terms, and synonyms to improve retrieval. "
                        "Respond only with a JSON array of 3 strings."
                    )
                },
                {
                    "role": "user",
                    "content": f"Query: {query}"
                }
            ],
            "timeout": 8,
        }
        if settings.litellm_base_url:
            kwargs["api_base"] = settings.litellm_base_url
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key

        response = await litellm.acompletion(**kwargs)
        result_content = response.choices[0].message.content.strip()
        
        # Parse JSON array
        # Clean potential markdown block formatting
        if result_content.startswith("```"):
            # strip off code block markers
            lines = result_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            result_content = "\n".join(lines).strip()

        variants = json.loads(result_content)
        if isinstance(variants, list):
            for var in variants:
                if isinstance(var, str) and var.strip() and var not in queries:
                    queries.append(var.strip())
        logger.info("Query rewritten successfully", original=query, variants=queries)
    except Exception as e:
        logger.warning("LiteLLM query rewriting failed, using fallback", error=str(e))
        # Simple heuristic fallback: break down query or just use synonyms if applicable
        # Or just return the original query
        pass

    return queries

