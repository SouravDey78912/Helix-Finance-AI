"""
rag/ingest/cleaner.py
======================
Step 2 of RAG Ingest: Text Cleaning.

Normalises raw extracted text:
  - Remove excessive whitespace and control characters
  - Fix encoding artifacts
  - Remove page headers/footers
  - Normalise unicode

TODO: Implement cleaning pipeline using regex + unicodedata.
"""

import re
import unicodedata
import structlog

logger = structlog.get_logger(__name__)


async def clean_text(raw_text: str) -> str:
    """
    Clean and normalise raw extracted text.
    """
    logger.info("clean_text called", text_length=len(raw_text))
    
    # 1. Normalize unicode (NFKC)
    cleaned = unicodedata.normalize("NFKC", raw_text)
    
    # 2. Replace multiple consecutive newlines or whitespaces with single ones
    # Keep newlines but collapse spacing
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    
    # 3. Strip leading/trailing whitespaces
    cleaned = cleaned.strip()
    
    return cleaned

