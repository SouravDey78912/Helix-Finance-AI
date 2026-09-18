"""
tests/test_single_agent.py
===========================
Pytest test suite for Step 1 Single-Agent Interactive Workflow.
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from agents.single_agent import start_workflow, resume_workflow


@pytest.mark.asyncio
async def test_single_agent_workflow_execution():
    """Test full single-agent workflow execution up to human approval gate."""
    mock_rag_result = {
        "context_text": "AML Customer Due Diligence guidelines require beneficial ownership verification above 25% stake.",
        "sources": [{"filename": "AML_Policy_2026.pdf", "document_id": "doc-01"}],
        "chunks": [
            {
                "text": "AML Customer Due Diligence guidelines require beneficial ownership verification above 25% stake.",
                "metadata": {
                    "filename": "AML_Policy_2026.pdf",
                    "entities": [
                        {
                            "entity_id": "REQ-101",
                            "entity_type": "Requirement",
                            "title": "Beneficial Ownership Identification",
                            "obligation_level": "MANDATORY",
                        }
                    ],
                },
            }
        ],
    }

    with patch("agents.orchestrator._pipeline.query", new=AsyncMock(return_value=mock_rag_result)):
        query = "Investigate our AML onboarding compliance."
        session_id = "test-session-101"
        user_id = "user-test-01"

        state = await start_workflow(query=query, session_id=session_id, user_id=user_id)

        assert state["query"] == query
        assert state["session_id"] == session_id
        assert len(state["steps"]) >= 4
        assert state["investigation_status"] in ("WAITING_FOR_EVIDENCE", "INVESTIGATING")
        assert "retrieval_node" in state["agent_trace"]
        assert "analysis_node" in state["agent_trace"]
        assert "evidence_verifier_node" in state["agent_trace"]


@pytest.mark.asyncio
async def test_single_agent_approval_and_synthesis():
    """Test human approval submission and report synthesis resumption."""
    from agents.single_agent import steer_workflow

    mock_rag_result = {
        "context_text": "AML Customer Due Diligence guidelines.",
        "sources": [],
        "chunks": [],
    }

    mock_chunk_stream = AsyncMock()
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="## Executive Summary\nCompliance audit approved."))]
    
    async def _async_iter():
        yield mock_chunk
    
    mock_chunk_stream.__aiter__ = _async_iter

    with patch("agents.orchestrator._pipeline.query", new=AsyncMock(return_value=mock_rag_result)):
        with patch("litellm.acompletion", new=AsyncMock(return_value=mock_chunk_stream)):
            query = "Investigate our AML onboarding compliance."
            session_id = "test-session-102"
            user_id = "user-test-02"

            # Step 1: Start workflow (reaches evidence interrupt)
            state = await start_workflow(query=query, session_id=session_id, user_id=user_id)
            
            # Step 2: Provide steering/continue to reach approval gate
            steered_state = await steer_workflow(session_id=session_id, steering_instruction="Proceed as is")
            approval_id = steered_state.get("approval_id") or "appr-test-102"

            # Step 3: Submit Approval
            updated_state = await resume_workflow(
                session_id=session_id,
                approval_id=approval_id,
                decision="APPROVED",
                feedback="Proceed with high priority remediation.",
            )

            assert updated_state["approval_status"] == "APPROVED"
            assert updated_state["final_answer"] is not None
            assert "synthesis_node" in updated_state["agent_trace"]


@pytest.mark.asyncio
async def test_single_agent_evidence_steering():
    """Test collaborative evidence interrupt and workflow steering."""
    from agents.single_agent import steer_workflow

    mock_rag_result = {
        "context_text": "CDD guidelines require verified evidence.",
        "sources": [],
        "chunks": [],
    }

    with patch("agents.orchestrator._pipeline.query", new=AsyncMock(return_value=mock_rag_result)):
        query = "Verify CDD onboarding evidence."
        session_id = "test-session-steer-1"
        user_id = "user-test-steer"

        state = await start_workflow(query=query, session_id=session_id, user_id=user_id)
        assert state["investigation_status"] in ("WAITING_FOR_EVIDENCE", "INVESTIGATING")

        steered_state = await steer_workflow(
            session_id=session_id,
            steering_instruction="Search Q2 Internal Audit report",
            document_ids=["doc-q2-audit-99"],
        )

        assert steered_state["user_steering_instruction"] == "Search Q2 Internal Audit report"
        assert "doc-q2-audit-99" in steered_state["new_document_ids"]
        assert "evidence_verifier_node" in steered_state["agent_trace"]
