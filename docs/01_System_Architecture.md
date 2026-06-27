# System Architecture (Production Learning Architecture)

## Guiding Principle
Every component must:
1. Run locally for free.
2. Have a production equivalent.
3. Require minimal code changes when migrating.

---

## High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Gateway                             │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│   │  JWT Auth    │  │ Rate Limiter │  │  Request Validation │   │
│   └──────────────┘  └──────────────┘  └─────────────────────┘   │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              Audit Log Middleware                        │  │
│   └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               LangGraph Orchestrator                            │
│                                                                 │
│   Planner Agent  ──►  Task Router                               │
│                           │                                     │
│           ┌───────────────┼─────────────────┐                   │
│           ▼               ▼                 ▼                   │
│       Retriever      AML Agent          KYC Agent               │
│           │                                                     │
│           └───────────────┬─────────────────┘                   │
│                           │         Compliance Agent            │
│                           ▼               │                     │
│                       Verifier  ◄─────────┘                     │
│                           │                                     │
│                           ▼                                     │
│                       Guardrails                                │
│                           │                                     │
│                           ▼                                     │
│                     Final Response                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
     Audit Log (PostgreSQL)        Metrics (Prometheus)
```

---

## Infrastructure Mapping

| Component | Local (Free) | Production |
|---|---|---|
| API | FastAPI | FastAPI + Ingress |
| Auth | JWT (HS256) | OAuth2 / SSO (Azure AD, Okta) |
| Config | .env | Vault / Secret Manager |
| Database | PostgreSQL | HA PostgreSQL (RDS, Azure) |
| Cache | Redis | Redis Cluster / Redis Enterprise |
| Vector DB | Qdrant | Qdrant Cloud / Qdrant Cluster |
| Storage | MinIO | AWS S3 / Azure Blob |
| Queue | RabbitMQ | RabbitMQ Cluster / Apache Kafka |
| Workers | Celery | Celery / Temporal |
| Monitoring | Prometheus + Grafana | Managed Monitoring Stack |
| Tracing | Langfuse (self-hosted) | Langfuse Cloud |
| RAG Debug | Phoenix (self-hosted) | Phoenix |
| Evaluation | Ragas + DeepEval | Same |
| Deployment | Docker Compose | Kubernetes |

---

## Request Flow

```text
1.  Authenticate      — Validate JWT (security/jwt_handler.py)
2.  Authorize         — Check user roles / permissions
3.  Validate          — Pydantic schema validation (apps/schemas/)
4.  Rate Limit        — Sliding window (apps/middleware/rate_limiter.py)
5.  Planner           — Decompose query (agents/planner.py)
6.  Task Route        — Select agents (agents/task_router.py)
7.  Retrieval         — Hybrid RAG search (agents/retriever.py)
8.  Specialist Agents — AML / KYC / Compliance (agents/specialist/)
9.  Verification      — Consistency check (agents/verifier.py)
10. Guardrails        — Safety filters (agents/guardrails.py)
11. Response          — Structured answer with citations
12. Audit Log         — Persist to PostgreSQL (apps/middleware/audit_log.py)
13. Metrics           — Update Prometheus counters (observability/metrics.py)
```

---

## RAG Pipeline

### Ingest Pipeline
```text
Upload (POST /documents/upload)
  │
  ▼
Store in MinIO  (infrastructure/minio_client.py)
  │
  ▼
Queue Celery Task  (workers/tasks/ingest_task.py)
  │
  ├── Parse      (rag/ingest/parser.py)          PDF / DOCX / TXT → text
  ├── Clean      (rag/ingest/cleaner.py)          Normalise text
  ├── Metadata   (rag/ingest/metadata_extractor.py) Extract doc metadata
  ├── Chunk      (rag/ingest/chunker.py)          Split into overlapping chunks
  ├── Embed      (rag/ingest/embedder.py)          BAAI/bge-small-en-v1.5
  └── Store      (infrastructure/qdrant_client.py) Upsert to Qdrant
```

### Query Pipeline
```text
Query (POST /chat/query)
  │
  ├── Rewrite    (rag/query/rewriter.py)          HyDE + multi-query expansion
  ├── Search     (rag/query/hybrid_search.py)      Dense + Sparse (RRF fusion)
  ├── Rerank     (rag/query/reranker.py)           BAAI/bge-reranker-base
  ├── Context    (rag/query/context_builder.py)    Assemble LLM prompt context
  └── LLM        LiteLLM → Ollama/llama3 (local)
```

---

## Async Worker Architecture

```text
FastAPI (API process)
    │
    └── Enqueue task ──► RabbitMQ ──► Celery Worker(s)
                                           │
                                   ┌───────┴────────┐
                                   ▼                ▼
                            Ingest Queue      Eval Queue
                            (ingest_task)     (eval_task)
                                   │
                                   ▼
                            Result Backend (Redis)
```

---

## Why These Choices?

- **Qdrant**: Free, production-ready, supports hybrid search natively.
- **MinIO**: S3-compatible — zero code change to migrate to AWS S3.
- **RabbitMQ**: Simpler than Kafka for learning; same Celery interface.
- **Celery**: Production-proven background job framework with retry support.
- **LiteLLM**: Provider independence — swap Ollama → OpenAI → Azure with one env var.
- **LangGraph**: Explicit, auditable workflow orchestration (critical for FinTech).
- **Docker Compose**: Easy local setup matching production service topology.
- **Kubernetes**: Production simulation using same container images.

---

## Future Enterprise Migration

No application logic changes required to migrate:

| Local | Production |
|---|---|
| MinIO | AWS S3 / Azure Blob |
| Local PostgreSQL | Managed PostgreSQL (RDS / Azure) |
| Redis standalone | Redis Enterprise / ElastiCache |
| RabbitMQ | RabbitMQ Cluster / Apache Kafka |
| Docker Compose | Kubernetes (Helm charts) |
| Ollama LLM | Azure OpenAI / OpenAI / Gemini |
| HS256 JWT | OAuth2 PKCE / Azure AD |
| Self-hosted Langfuse | Langfuse Cloud |
