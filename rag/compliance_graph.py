"""
rag/compliance_graph.py
========================
Control Mapping & Compliance Gap Analysis Engine.

Builds a 4-tier graph linking:
  Regulation -> Requirement -> Internal Control -> Evidence

Analyzes graph structure to identify gaps:
  - HIGH Severity: Missing Control or Missing Evidence for Mandatory Requirement
  - MEDIUM Severity: Outdated Evidence / Deficient Control
  - LOW Severity: Non-critical recommendation gap
"""

from typing import List, Dict, Any
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ComplianceGap(BaseModel):
    severity: str = Field(description="HIGH | MEDIUM | LOW")
    requirement_id: str
    requirement_title: str
    control_id: str
    control_title: str
    evidence_id: str
    evidence_status: str = Field(description="AVAILABLE | MISSING | OUTDATED")
    summary: str


class ComplianceGraphEngine:
    """Engine for building compliance control maps and analyzing regulatory gaps."""

    def __init__(self):
        pass

    def build_graph_from_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organize raw extracted entities into a structured 4-tier map.
        """
        graph = {
            "regulations": [],
            "requirements": [],
            "controls": [],
            "evidence": [],
        }

        for idx, entity in enumerate(entities):
            e_type = entity.get("entity_type", "Requirement").upper()
            
            # Map entity to corresponding tier
            if "REGULATION" in e_type:
                graph["regulations"].append(entity)
            elif "CONTROL" in e_type:
                graph["controls"].append(entity)
            elif "EVIDENCE" in e_type or "REPORT" in e_type:
                graph["evidence"].append(entity)
            else:
                # Default to Requirement
                graph["requirements"].append(entity)

        logger.info("Compliance graph built", requirements=len(graph["requirements"]), controls=len(graph["controls"]), evidence=len(graph["evidence"]))
        return graph

    def analyze_gaps(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the compliance graph to detect control and evidence gaps.
        """
        gaps: List[ComplianceGap] = []
        requirements = graph.get("requirements", [])
        controls = graph.get("controls", [])
        evidence_list = graph.get("evidence", [])

        # Map controls by title/condition matching for demonstration mapping
        control_map = {c.get("title", f"C-{i}"): c for i, c in enumerate(controls)}
        evidence_map = {e.get("title", f"E-{i}"): e for i, e in enumerate(evidence_list)}

        for i, req in enumerate(requirements):
            req_title = req.get("title", f"Requirement R-{i+1}")
            obligation = req.get("obligation_level", "MANDATORY").upper()

            # Find matching control or check if missing
            matching_control = None
            for c_title, c_obj in control_map.items():
                if any(w in c_title.lower() for w in req_title.lower().split()[:3]):
                    matching_control = c_obj
                    break

            if not matching_control and obligation == "MANDATORY":
                # HIGH SEVERITY GAP: Mandatory Requirement with Missing Control
                gaps.append(
                    ComplianceGap(
                        severity="HIGH",
                        requirement_id=f"R-{100 + i}",
                        requirement_title=req_title,
                        control_id="MISSING",
                        control_title="No Internal Control Mapped",
                        evidence_id="MISSING",
                        evidence_status="MISSING",
                        summary=f"Mandatory requirement '{req_title}' has no operational control assigned."
                    )
                )

            elif matching_control:
                c_id = matching_control.get("entity_id", f"C-{200 + i}")
                c_title = matching_control.get("title", "Mapped Control")

                # Check evidence for the control
                matching_evidence = None
                for e_title, e_obj in evidence_map.items():
                    if any(w in e_title.lower() for w in c_title.lower().split()[:2]):
                        matching_evidence = e_obj
                        break

                if not matching_evidence:
                    # HIGH / MEDIUM GAP: Control exists but Evidence is Missing
                    severity = "HIGH" if obligation == "MANDATORY" else "MEDIUM"
                    gaps.append(
                        ComplianceGap(
                            severity=severity,
                            requirement_id=f"R-{100 + i}",
                            requirement_title=req_title,
                            control_id=c_id,
                            control_title=c_title,
                            evidence_id="MISSING",
                            evidence_status="MISSING",
                            summary=f"Control '{c_title}' has no supporting execution evidence logged."
                        )
                    )
                elif matching_evidence.get("status") == "OUTDATED":
                    # MEDIUM GAP: Evidence is Outdated
                    gaps.append(
                        ComplianceGap(
                            severity="MEDIUM",
                            requirement_id=f"R-{100 + i}",
                            requirement_title=req_title,
                            control_id=c_id,
                            control_title=c_title,
                            evidence_id=matching_evidence.get("entity_id", f"E-{300 + i}"),
                            evidence_status="OUTDATED",
                            summary=f"Evidence for control '{c_title}' is outdated."
                        )
                    )

        # Count summary totals
        high_count = sum(1 for g in gaps if g.severity == "HIGH")
        med_count = sum(1 for g in gaps if g.severity == "MEDIUM")
        low_count = sum(1 for g in gaps if g.severity == "LOW")

        logger.info("Compliance gap analysis complete", total_gaps=len(gaps), high=high_count, medium=med_count, low=low_count)

        return {
            "total_gaps_identified": len(gaps),
            "summary": {
                "high_severity": high_count,
                "medium_severity": med_count,
                "low_severity": low_count,
            },
            "gaps": [g.model_dump() for g in gaps],
        }


def run_compliance_gap_analysis(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper entry point to build graph and execute gap analysis."""
    engine = ComplianceGraphEngine()
    graph = engine.build_graph_from_entities(entities)
    return engine.analyze_gaps(graph)
