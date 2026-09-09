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

import json
import re
import structlog
import litellm
from pydantic import BaseModel, Field

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DocumentMetadata(BaseModel):
    doc_type: str = Field(description="Document type, e.g., regulation, policy, report, contract, guideline")
    jurisdiction: str = Field(description="Jurisdiction, e.g., US, EU, UK, Global, DE, FR")
    effective_date: str = Field(description="Effective date of the document in YYYY-MM-DD format if found, or 'Unknown'")
    regulatory_body: str = Field(description="Regulatory body, e.g., FATF, FinCEN, FCA, SEC, Unknown")
    topics: list[str] = Field(description="List of primary topics/tags, e.g., AML, KYC, Sanctions")
    language: str = Field(description="Language of the document, e.g., English")


async def extract_metadata(text: str, filename: str) -> dict:
    """
    Extract structured metadata from document content.

    Returns:
        dict with keys: doc_type, jurisdiction, effective_date,
                        regulatory_body, topics, language
    """
    logger.info("extract_metadata called", filename=filename)

    # Use first ~4000 characters for metadata extraction
    sample_text = text[:4000]

    try:
        # Configure model parameters
        kwargs = {
            "model": settings.litellm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a regulatory compliance document analyzer. Extract structured metadata from the text.",
                },
                {
                    "role": "user",
                    "content": f"Document Snippet:\n{sample_text}\n\nFilename: {filename}",
                },
            ],
            "response_format": DocumentMetadata,
            "timeout": 10,
        }
        if settings.litellm_base_url:
            kwargs["api_base"] = settings.litellm_base_url
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key

        response = await litellm.acompletion(**kwargs)
        result_content = response.choices[0].message.content
        logger.info("Metadata extraction completed via LLM")
        
        # Parse output
        data = json.loads(result_content)
        return data

    except Exception as e:
        logger.warning("LiteLLM metadata extraction failed, using heuristic fallback", error=str(e))
        return _heuristic_fallback_metadata(text, filename)


def _heuristic_fallback_metadata(text: str, filename: str) -> dict:
    """Fallback method using standard heuristics and regex."""
    text_lower = text[:5000].lower()
    filename_lower = filename.lower()

    # Determine Doc Type
    doc_type = "report"
    if any(k in filename_lower or k in text_lower for k in ["regulation", "rule", "law", "act"]):
        doc_type = "regulation"
    elif any(k in filename_lower or k in text_lower for k in ["policy", "procedure"]):
        doc_type = "policy"
    elif any(k in filename_lower or k in text_lower for k in ["contract", "agreement"]):
        doc_type = "contract"
    elif any(k in filename_lower or k in text_lower for k in ["guideline", "guidance"]):
        doc_type = "guideline"

    # Determine Jurisdiction
    jurisdiction = "Global"
    if "fincen" in text_lower or "sec" in text_lower or "us" in text_lower or "united states" in text_lower:
        jurisdiction = "US"
    elif "fca" in text_lower or "uk" in text_lower or "united kingdom" in text_lower:
        jurisdiction = "UK"
    elif "eu" in text_lower or "european union" in text_lower or "esma" in text_lower:
        jurisdiction = "EU"

    # Determine Regulatory Body
    regulatory_body = "Unknown"
    for body in ["FATF", "FinCEN", "FCA", "SEC", "CFTC", "ESMA", "EBA"]:
        if body.lower() in text_lower or body.lower() in filename_lower:
            regulatory_body = body
            break

    # Determine Effective Date
    effective_date = "Unknown"
    # Match dates like YYYY-MM-DD or Month DD, YYYY
    date_match = re.search(r"\b(19|20)\d{2}[-/]\d{2}[-/]\d{2}\b", text[:5000])
    if date_match:
        effective_date = date_match.group(0)

    # Determine Topics
    topics = []
    for topic, keywords in {
        "AML": ["aml", "anti-money laundering", "money laundering"],
        "KYC": ["kyc", "know your customer", "identity verification"],
        "Sanctions": ["sanction", "ofac", "embargo"],
        "Compliance": ["compliance", "audit", "reporting"],
    }.items():
        if any(k in text_lower for k in keywords):
            topics.append(topic)
    if not topics:
        topics = ["Compliance"]

    return {
        "doc_type": doc_type,
        "jurisdiction": jurisdiction,
        "effective_date": effective_date,
        "regulatory_body": regulatory_body,
        "topics": topics,
        "language": "English",
    }

