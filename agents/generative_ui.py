"""
agents/generative_ui.py
========================
Generative UI Specification & Component Schema Registry for Helix Finance AI.
Reference: AG-UI (Agent User Interaction) + Generative UI Component Registry

Architecture:
  LangGraph Agent -> Generative UI Schema -> AG-UI Events -> Dynamic UI Renderer (Frontend Registry)

This module provides validated JSON schemas and factory functions for Helix FinTech Compliance UI components:
  1. DocumentUpload        - Dynamic evidence file dropzone
  2. EvidenceRequest       - Agent prompt requesting evidence documents
  3. InvestigationScope    - Scope selector (AML Onboarding, Sanctions, etc.)
  4. RiskThreshold         - Risk level threshold selection
  5. RequirementCard       - Regulatory requirement summary card
  6. ControlCard           - Operational control mapping status card
  7. EvidenceCard          - Retrieved audit evidence card
  8. ComplianceFinding     - Compliance gap finding card with action buttons
  9. RiskAssessment        - Comprehensive risk level assessment summary
  10. SourceViewer         - Interactive citation source inspector
  11. ApprovalCard         - Human-in-the-Loop decision & signoff card
  12. ChallengeFinding     - Finding challenge & feedback form
  13. InvestigationControls - Dynamic agent steering controls
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GenUIComponent(BaseModel):
    """Base model for Generative UI Component Schema."""
    type: str = Field(..., description="Unique component registry type identifier")
    id: str = Field(..., description="Unique element ID")
    title: Optional[str] = None
    description: Optional[str] = None
    props: Dict[str, Any] = Field(default_factory=dict)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


def build_evidence_request_ui(
    control_id: str,
    control_name: str,
    requirement_code: str,
    description: Optional[str] = None,
    suggested_scopes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generates Generative UI specification for evidence request & scope selection."""
    if not suggested_scopes:
        suggested_scopes = [
            "AML onboarding",
            "Transaction monitoring",
            "Sanctions screening",
            "Entire AML framework",
        ]

    if not description:
        description = f"Found operational control '{control_name}' linked to {requirement_code}, but execution evidence is missing."

    return {
        "spec_version": "1.0",
        "layout": "stack",
        "components": [
            {
                "type": "EvidenceRequest",
                "id": f"ev-req-{control_id}",
                "title": f"⚠ Additional evidence required for {control_id}",
                "description": description,
                "props": {
                    "control_id": control_id,
                    "control_name": control_name,
                    "requirement_code": requirement_code,
                    "status": "UNVERIFIED",
                },
            },
            {
                "type": "DocumentUpload",
                "id": f"doc-up-{control_id}",
                "title": "Upload Supporting Audit Evidence",
                "props": {
                    "accepted_formats": [".pdf", ".docx", ".txt"],
                    "placeholder": "Drag & drop audit report, policy PDF, or evidence file here",
                },
            },
            {
                "type": "InvestigationScope",
                "id": f"scope-sel-{control_id}",
                "title": "Where should the agent investigate?",
                "props": {
                    "options": [
                        {"label": scope, "value": scope.lower().replace(" ", "_")}
                        for scope in suggested_scopes
                    ],
                    "default_value": "aml_onboarding",
                },
            },
            {
                "type": "InvestigationControls",
                "id": f"ctrls-{control_id}",
                "actions": [
                    {
                        "action_id": "STEER_INVESTIGATION",
                        "label": "⚡ Continue Investigation with Evidence & Scope",
                        "variant": "primary",
                    },
                    {
                        "action_id": "CONTINUE_WITHOUT_EVIDENCE",
                        "label": "➡️ Proceed Without Evidence",
                        "variant": "secondary",
                    },
                ],
            },
        ],
    }


def build_compliance_finding_ui(
    finding_id: str,
    requirement_code: str,
    control_id: str,
    evidence_snippet: str,
    risk_level: str = "HIGH",
) -> Dict[str, Any]:
    """Generates Generative UI specification for compliance finding review."""
    return {
        "spec_version": "1.0",
        "layout": "stack",
        "components": [
            {
                "type": "ComplianceFinding",
                "id": f"finding-{finding_id}",
                "title": f"Compliance Finding: {requirement_code}",
                "props": {
                    "finding_id": finding_id,
                    "requirement_code": requirement_code,
                    "control_id": control_id,
                    "evidence_snippet": evidence_snippet,
                    "risk_level": risk_level,
                },
                "actions": [
                    {"action_id": "APPROVE_FINDING", "label": "✓ Approve Finding", "variant": "success"},
                    {"action_id": "CHALLENGE_FINDING", "label": "💬 Challenge Finding", "variant": "warning"},
                    {"action_id": "EDIT_FINDING", "label": "✏ Edit Scope", "variant": "secondary"},
                    {"action_id": "REJECT_FINDING", "label": "✕ Reject", "variant": "danger"},
                ],
            }
        ],
    }


def build_approval_card_ui(
    approval_id: str,
    summary: str,
    risk_level: str,
    gaps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generates Generative UI specification for human approval card."""
    return {
        "spec_version": "1.0",
        "layout": "stack",
        "components": [
            {
                "type": "ApprovalCard",
                "id": f"appr-card-{approval_id}",
                "title": "⚠ HUMAN APPROVAL REQUIRED",
                "description": summary,
                "props": {
                    "approval_id": approval_id,
                    "risk_level": risk_level,
                    "gaps": gaps,
                },
                "actions": [
                    {"action_id": "APPROVED", "label": "✓ Approve & Synthesize Report", "variant": "success"},
                    {"action_id": "REVISE", "label": "💬 Request Revision", "variant": "warning"},
                    {"action_id": "REJECTED", "label": "✕ Reject Findings", "variant": "danger"},
                ],
            }
        ],
    }
