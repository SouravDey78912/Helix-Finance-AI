"""
tests/test_evaluation.py
=========================
Pytest unit tests for Ragas, DeepEval evaluation runners & REST API endpoints.
"""

import pytest
from evaluation.ragas_eval import run_ragas_evaluation
from evaluation.deepeval_eval import run_deepeval_evaluation


@pytest.mark.asyncio
async def test_ragas_evaluation_execution():
    """Test Ragas evaluation calculation and gauge metric updating."""
    sample_dataset = [
        {
            "question": "What is the mandatory threshold for beneficial ownership verification?",
            "answer": "Beneficial ownership verification is required for corporate entities holding >25% stake.",
            "contexts": ["FinCEN CDD Rule requires financial institutions to identify beneficial owners holding 25% or more equity."],
            "ground_truth": ">25% ownership stake threshold",
        }
    ]

    results = await run_ragas_evaluation(sample_dataset)

    assert "faithfulness" in results
    assert "answer_relevancy" in results
    assert "context_precision" in results
    assert 0.0 <= results["faithfulness"] <= 1.0
    assert 0.0 <= results["answer_relevancy"] <= 1.0


@pytest.mark.asyncio
async def test_deepeval_evaluation_execution():
    """Test DeepEval evaluation calculation and compliance scoring."""
    sample_dataset = [
        {
            "input": "What are customer due diligence steps?",
            "actual_output": "CDD steps include customer identification, beneficial owner verification, and ongoing monitoring.",
            "retrieval_context": ["Customer due diligence mandates verification of customer identity and beneficial owners."],
        }
    ]

    results = await run_deepeval_evaluation(sample_dataset)

    assert "hallucination" in results
    assert "fintech_compliance_score" in results
    assert 0.0 <= results["hallucination"] <= 1.0
    assert 0.0 <= results["fintech_compliance_score"] <= 1.0


@pytest.mark.asyncio
async def test_evaluation_api_endpoints():
    """Test evaluation REST API router endpoints using httpx AsyncClient."""
    from httpx import AsyncClient, ASGITransport
    from apps.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET summary endpoint
        response = await client.get("/api/v1/evaluation/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "HEALTHY"
        assert "ragas" in data
        assert "deepeval" in data

        # POST run endpoint
        payload = {
            "dataset": [
                {
                    "question": "Explain KYC verification requirements.",
                    "answer": "KYC requires customer ID verification and risk profiling.",
                    "contexts": ["KYC rules require identity verification and ongoing risk monitoring."],
                }
            ]
        }
        post_resp = await client.post("/api/v1/evaluation/run", json=payload)
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["status"] == "COMPLETED"
        assert "ragas_metrics" in post_data
        assert "deepeval_metrics" in post_data
