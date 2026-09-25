"""
apps/api/v1/evaluation.py
==========================
REST API routes for RAG and Agent evaluation trigger & quality score query.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from evaluation.ragas_eval import run_ragas_evaluation
from evaluation.deepeval_eval import run_deepeval_evaluation

router = APIRouter()


class EvalItem(BaseModel):
    question: str = Field(..., description="User query or test question")
    answer: str = Field(..., description="Model generated response")
    contexts: List[str] = Field(default_factory=list, description="Retrieved RAG context chunks")
    ground_truth: Optional[str] = Field(default=None, description="Expected ground truth answer")


class EvaluationRunRequest(BaseModel):
    dataset: List[EvalItem] = Field(..., min_length=1, description="Evaluation dataset items")


class EvaluationRunResponse(BaseModel):
    status: str = "COMPLETED"
    ragas_metrics: Dict[str, float]
    deepeval_metrics: Dict[str, float]


@router.post("/run", response_model=EvaluationRunResponse, summary="Execute Ragas & DeepEval Evaluation")
async def execute_evaluation(payload: EvaluationRunRequest):
    """
    Run Ragas (Faithfulness, Relevancy, Precision) & DeepEval (Hallucination, Compliance) evaluation.
    Updates Prometheus gauges for real-time Grafana dashboard monitoring.
    """
    try:
        raw_dataset = [item.model_dump() for item in payload.dataset]
        
        # Prepare DeepEval input mapping
        deepeval_dataset = [
            {
                "input": item.get("question"),
                "actual_output": item.get("answer"),
                "expected_output": item.get("ground_truth"),
                "retrieval_context": item.get("contexts"),
            }
            for item in raw_dataset
        ]

        ragas_results = await run_ragas_evaluation(raw_dataset)
        deepeval_results = await run_deepeval_evaluation(deepeval_dataset)

        return EvaluationRunResponse(
            status="COMPLETED",
            ragas_metrics=ragas_results,
            deepeval_metrics=deepeval_results,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation execution failed: {str(exc)}",
        )


@router.get("/summary", summary="Get Latest Evaluation Metrics")
async def get_latest_evaluation_summary():
    """
    Get latest evaluation score benchmarks.
    """
    sample_eval = [
        {
            "question": "What is the mandatory threshold for beneficial ownership verification?",
            "answer": "Beneficial ownership verification is required for corporate entities holding >25% stake under FinCEN CDD rule.",
            "contexts": ["FinCEN CDD Rule requires financial institutions to identify beneficial owners holding 25% or more equity."],
            "ground_truth": ">25% ownership stake threshold",
        }
    ]
    ragas_results = await run_ragas_evaluation(sample_eval)
    deepeval_results = await run_deepeval_evaluation(sample_eval)

    return {
        "status": "HEALTHY",
        "ragas": ragas_results,
        "deepeval": deepeval_results,
    }
