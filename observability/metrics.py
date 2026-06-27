"""
observability/metrics.py
=========================
Prometheus metrics definitions.

Local:       Prometheus + Grafana in Docker Compose (free)
Production:  Managed Prometheus / Grafana Cloud

Metrics exposed at GET /metrics (mounted by apps/main.py).

TODO: Instrument actual request handlers with these metrics.
TODO: Add LLM-specific metrics (token usage, latency per model).
"""

from prometheus_client import Counter, Gauge, Histogram

# ── HTTP Metrics ──────────────────────────────────────────────────────────────
http_requests_total = Counter(
    "helix_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "helix_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── RAG Pipeline Metrics ──────────────────────────────────────────────────────
rag_queries_total = Counter(
    "helix_rag_queries_total",
    "Total RAG queries processed",
    ["status"],  # success | error
)

rag_retrieval_duration_seconds = Histogram(
    "helix_rag_retrieval_duration_seconds",
    "Time spent in RAG retrieval pipeline",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

rag_chunks_retrieved = Histogram(
    "helix_rag_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=[1, 3, 5, 10, 20],
)

# ── Document Ingestion Metrics ────────────────────────────────────────────────
documents_ingested_total = Counter(
    "helix_documents_ingested_total",
    "Total documents ingested",
    ["status"],  # success | failed
)

ingestion_duration_seconds = Histogram(
    "helix_ingestion_duration_seconds",
    "Document ingestion duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ── Agent Metrics ─────────────────────────────────────────────────────────────
agent_invocations_total = Counter(
    "helix_agent_invocations_total",
    "Total agent invocations",
    ["agent_name", "status"],
)

agent_duration_seconds = Histogram(
    "helix_agent_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_name"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ── LLM Metrics ───────────────────────────────────────────────────────────────
llm_tokens_used_total = Counter(
    "helix_llm_tokens_used_total",
    "Total LLM tokens consumed",
    ["model", "type"],  # type: prompt | completion
)

# ── Guardrails Metrics ────────────────────────────────────────────────────────
guardrails_triggered_total = Counter(
    "helix_guardrails_triggered_total",
    "Total guardrail triggers",
    ["trigger_type"],  # pii | hallucination | toxicity | compliance
)
