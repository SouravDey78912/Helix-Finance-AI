"""
rag/ingest/metadata_extractor.py
==================================
Step 3 of RAG Ingest: Metadata Extraction.

Extracts structured metadata from documents:
  - Document type (regulation, policy, report, contract)
  - Jurisdiction (US, EU, UK, etc.)
  - Effective date / version
  - Regulatory body (FATF, FinCEN, FCA, etc.)
  - Topics / tags

TODO: Implement using LiteLLM structured output extraction.
TODO: Use document filename and headers as initial signals.
"""

import structlog

logger = structlog.get_logger(__name__)


async def extract_metadata(text: str, filename: str) -> dict:
    """
    Extract structured metadata from document content.

    Returns:
        dict with keys: doc_type, jurisdiction, effective_date,
                        regulatory_body, topics, language

    TODO: Implement LiteLLM metadata extraction prompt.
    """
    logger.info("extract_metadata called", filename=filename)
    raise NotImplementedError("Metadata extractor not yet implemented")
