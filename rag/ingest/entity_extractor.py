"""
rag/ingest/entity_extractor.py
===============================
Structured Entity & Knowledge Extractor.

Transforms raw compliance document chunks into structured entities:
  - Requirements (e.g. Mandatory CDD, SAR filing thresholds)
  - Controls (e.g. Identity verification, Dual authorization)
  - Risks (e.g. Structuring, Money Laundering, PEP exposure)
  - Definitions & Obligations
"""

import json
import re
from typing import List, Optional
import structlog
import litellm
from pydantic import BaseModel, Field

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ComplianceEntity(BaseModel):
    entity_type: str = Field(
        description="Type of entity: Requirement, Control, Risk, Finding, Definition"
    )
    title: str = Field(
        description="Short concise title of the entity/requirement"
    )
    action: str = Field(
        description="The action required or described, e.g., 'must be completed', 'screened against watchlists'"
    )
    condition: Optional[str] = Field(
        default="None",
        description="Condition or trigger when this applies, e.g., 'before establishing business relationship', 'transfers > $10,000'"
    )
    obligation_level: str = Field(
        default="MANDATORY",
        description="Level of obligation: MANDATORY, RECOMMENDED, OPTIONAL"
    )
    risk_category: Optional[str] = Field(
        default="Compliance Risk",
        description="Category of risk involved, e.g., AML, KYC, Sanctions, Fraud"
    )


class ChunkEntityExtractionResult(BaseModel):
    entities: List[ComplianceEntity] = Field(default_factory=list)


async def extract_entities_from_chunk(text: str, doc_metadata: dict | None = None) -> list[dict]:
    """
    Extract structured compliance entities from a document chunk.

    Args:
        text: Raw chunk text content.
        doc_metadata: Optional document-level metadata (doc_type, regulatory_body, etc.)

    Returns:
        List of extracted entity dictionaries.
    """
    if not text or len(text.strip()) < 20:
        return []

    doc_meta = doc_metadata or {}
    filename = doc_meta.get("filename", "document")
    doc_type = doc_meta.get("doc_type", "policy")

    try:
        kwargs = {
            "model": settings.litellm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Senior Regulatory Compliance Analyst. Extract structured compliance entities "
                        "(Requirements, Controls, Risks, Definitions) from the text chunk. "
                        "Identify mandatory actions, triggering conditions, and risk categories."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Document: {filename} ({doc_type})\n\nChunk Text:\n{text}",
                },
            ],
            "response_format": ChunkEntityExtractionResult,
            "timeout": 10,
        }
        if settings.litellm_base_url:
            kwargs["api_base"] = settings.litellm_base_url
        if settings.openai_api_key:
            kwargs["api_key"] = settings.openai_api_key

        response = await litellm.acompletion(**kwargs)
        result_content = response.choices[0].message.content
        
        # Clean codeblock wrappers if present
        if result_content.startswith("```"):
            lines = result_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            result_content = "\n".join(lines).strip()

        data = json.loads(result_content)
        entities = data.get("entities", [])
        logger.info("Extracted entities via LLM", count=len(entities))
        return entities

    except Exception as e:
        logger.warning("LiteLLM entity extraction failed, using rule-based fallback", error=str(e))
        return _fallback_heuristic_entity_extractor(text)


def _fallback_heuristic_entity_extractor(text: str) -> list[dict]:
    """Fallback rule-based heuristic extractor for compliance entities."""
    entities = []
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        s_lower = sentence.lower()
        
        # Check for mandatory requirements
        if any(keyword in s_lower for keyword in ["must", "shall", "required to", "mandatory"]):
            action_match = re.search(r'\b(must|shall|required to)\s+([^.,;]+)', sentence, re.IGNORECASE)
            action_text = action_match.group(0) if action_match else "must comply"
            
            condition_match = re.search(r'\b(before|after|if|when|prior to)\s+([^.,;]+)', sentence, re.IGNORECASE)
            condition_text = condition_match.group(0) if condition_match else "General operational condition"

            entities.append({
                "entity_type": "Requirement",
                "title": sentence[:60].strip() + ("..." if len(sentence) > 60 else ""),
                "action": action_text.strip(),
                "condition": condition_text.strip(),
                "obligation_level": "MANDATORY",
                "risk_category": "Compliance Risk",
            })

        # Check for risks / sanctions
        elif any(keyword in s_lower for keyword in ["risk", "prohibited", "violation", "penalty", "sanction"]):
            entities.append({
                "entity_type": "Risk",
                "title": sentence[:60].strip() + ("..." if len(sentence) > 60 else ""),
                "action": "prohibited_or_flagged",
                "condition": "upon violation or risk trigger",
                "obligation_level": "MANDATORY",
                "risk_category": "AML/Sanctions Risk",
            })

    return entities
