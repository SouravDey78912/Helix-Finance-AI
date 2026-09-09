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

### Ingest Sub-System
The document ingestion pipeline processes incoming files asynchronously using Celery and MinIO.

1. **Upload**: Files are POSTed to `/api/v1/documents/upload`.
2. **Object Storage**: The raw file is stored in MinIO via `infrastructure/minio_client.py`.
3. **Asynchronous Processing**: Celery task `workers/tasks/ingest_task.py` downloads the file and runs the pipeline stages:
   * **Parse (`rag/ingest/parser.py`)**: 
     - **PDF**: Handled via `pypdf.PdfReader` extracting text across all pages.
     - **DOCX (Word)**: Lightweight XML parser that reads text blocks from `word/document.xml` using `zipfile`.
     - **TXT/Markdown**: Decodes files with automatic fallback encodings (UTF-8, Latin-1, CP1252).
   * **Clean (`rag/ingest/cleaner.py`)**: 
     - Performs unicode normalization (NFKC).
     - Standardizes and collapses spaces and tabs.
     - Collapses consecutive newlines to double-newlines (`\n\n`) to retain paragraphs.
   * **Metadata & Entity Extraction (`rag/ingest/metadata_extractor.py`, `rag/ingest/entity_extractor.py`)**: 
     - Runs structured JSON schema extraction using LiteLLM to capture `doc_type`, `jurisdiction`, `effective_date`, `regulatory_body`, `topics`, and `language`.
     - Automatically parses compliance entities: `Regulation`, `Requirement`, `Internal Control`, and `Evidence` with relational IDs, storing them in chunk vector payloads.
     - Automatically falls back to a regex/keyword-based heuristic parser if the LLM is down or fails.
   * **Chunking (`rag/ingest/chunker.py`)**: 
     - Splits text using `langchain_text_splitters.RecursiveCharacterTextSplitter` by checking newlines and spaces.
     - Assigns a unique UUID to each chunk and injects the document metadata and extracted compliance entities for Qdrant payload filters.
   * **Embedding (`rag/ingest/embedder.py`)**: 
     - Generates 384-dimensional dense vectors using LiteLLM's async `aembedding` endpoint.
   * **Storage (`infrastructure/qdrant_client.py`)**: 
     - Upserts vectors, metadata payloads, and extracted structured entities using `PointStruct` batches into the Qdrant database.

### Compliance Gap Analysis Engine
The system features an automated, graph-based Compliance Gap Analysis Engine (`rag/compliance_graph.py`):

1. **Hierarchy Mapping**: Evaluates relationships across 4 domain tiers (`Regulation` $\rightarrow$ `Requirement` $\rightarrow$ `Internal Control` $\rightarrow$ `Evidence`).
2. **Missing Element Detection**:
   - Flagged as `HIGH` severity if a `Requirement` has no mapped `Internal Control`.
   - Flagged as `MEDIUM` severity if an `Internal Control` has no linked `Evidence`.
   - Flagged as `LOW` severity for minor administrative or date mismatches.
3. **Structured Response Integration**: During query execution (`apps/api/v1/chat.py` & `rag/pipeline.py`), compliance analysis outputs generate formatted markdown cards rendered dynamically in the front-end application interface.

### Query & Retrieval Sub-System
Retrieves context for natural language questions:

1. **Query Rewrite (`rag/query/rewriter.py`)**:
   - Uses LiteLLM to generate 3 alternative formulations/synonyms of the user's query to maximize retrieval recall. Falls back to original query on error.
2. **Hybrid Search (`rag/query/hybrid_search.py`)**:
   - Embeds each query variant concurrently.
   - Executes parallel vector search in Qdrant with optional payload filter conditions.
   - Combines results across variants using **Reciprocal Rank Fusion (RRF)** with standard constant $k=60$.
3. **Reranking (`rag/query/reranker.py`)**:
   - Re-evaluates top-K candidates using `sentence-transformers` CrossEncoder (`BAAI/bge-reranker-base`) for high semantic precision.
   - Safely falls back to vector/RRF search scores if the local CrossEncoder model is unavailable.
4. **Context Building (`rag/query/context_builder.py`)**:
   - Aggregates the top reranked chunks.
   - Computes tokens using `tiktoken` (falling back to character estimation if not present) to respect a strict context window token budget (default 3000).
   - Generates structured citations showing file references, chunk indices, and compliance entities.



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
