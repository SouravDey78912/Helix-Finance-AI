import pytest
from rag.compliance_graph import ComplianceGraphEngine, run_compliance_gap_analysis


def test_build_graph_from_entities():
    entities = [
        {"entity_type": "Requirement", "title": "Enhanced Due Diligence", "obligation_level": "MANDATORY"},
        {"entity_type": "Control", "title": "C-104 Senior Approval Control"},
        {"entity_type": "Evidence", "title": "E-332 Customer Verification Log"},
    ]

    engine = ComplianceGraphEngine()
    graph = engine.build_graph_from_entities(entities)

    assert len(graph["requirements"]) == 1
    assert len(graph["controls"]) == 1
    assert len(graph["evidence"]) == 1


def test_analyze_gaps_high_severity():
    # Mandatory requirement with no matching control
    entities = [
        {
            "entity_type": "Requirement",
            "title": "Periodic Customer Review",
            "obligation_level": "MANDATORY",
        }
    ]

    result = run_compliance_gap_analysis(entities)
    assert result["total_gaps_identified"] == 1
    assert result["summary"]["high_severity"] == 1
    assert result["gaps"][0]["severity"] == "HIGH"
    assert result["gaps"][0]["control_id"] == "MISSING"


def test_analyze_gaps_missing_evidence():
    # Control exists but missing evidence
    entities = [
        {
            "entity_type": "Requirement",
            "title": "Record Retention Requirement",
            "obligation_level": "MANDATORY",
        },
        {
            "entity_type": "Control",
            "title": "Record Retention Control C-302",
        },
    ]

    result = run_compliance_gap_analysis(entities)
    assert result["total_gaps_identified"] == 1
    assert result["gaps"][0]["evidence_status"] == "MISSING"
