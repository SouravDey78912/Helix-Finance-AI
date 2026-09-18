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
        assert state["needs_approval"] is True
        assert state["approval_status"] == "PENDING"
        assert state["approval_id"] is not None
        assert "retrieval_node" in state["agent_trace"]
        assert "analysis_node" in state["agent_trace"]
        assert "verification_node" in state["agent_trace"]


@pytest.mark.asyncio
async def test_single_agent_approval_and_synthesis():
    """Test human approval submission and report synthesis resumption."""
    mock_rag_result = {
        "context_text": "AML Customer Due Diligence guidelines.",
        "sources": [],
        "chunks": [],
    }

    mock_llm_choice = MagicMock()
    mock_llm_choice.message.content = "## Executive Summary\nCompliance audit approved."
    mock_llm_resp = MagicMock()
    mock_llm_resp.choices = [mock_llm_choice]

    with patch("agents.orchestrator._pipeline.query", new=AsyncMock(return_value=mock_rag_result)):
        with patch("litellm.acompletion", new=AsyncMock(return_value=mock_llm_resp)):
            query = "Investigate our AML onboarding compliance."
            session_id = "test-session-102"
            user_id = "user-test-02"

            # Step 1: Start workflow
            state = await start_workflow(query=query, session_id=session_id, user_id=user_id)
            approval_id = state["approval_id"]

            # Step 2: Submit Approval
            updated_state = await resume_workflow(
                session_id=session_id,
                approval_id=approval_id,
                decision="APPROVED",
                feedback="Proceed with high priority remediation.",
            )

            assert updated_state["approval_status"] == "APPROVED"
            assert updated_state["final_answer"] is not None
            assert "synthesis_node" in updated_state["agent_trace"]
