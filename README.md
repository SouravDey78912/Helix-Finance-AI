# Helix Finance AI 🏦

> **AI Financial Operations Platform** — Enterprise-grade Multi-Agent RAG for FinTech
>
> *Design like an enterprise. Build with open source.*

---

## Overview

Helix Finance AI is a **production-learning architecture** for building AI-powered financial operations. It implements a full Multi-Agent RAG (Retrieval-Augmented Generation) pipeline with specialist agents for AML, KYC, and Compliance analysis.

Built with **100% free, open-source technologies** locally — designed so every component can be replaced with enterprise-managed services without changing application code.

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your local settings (defaults work with Docker Compose)
```

### 4. Start infrastructure services

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

### 5. Run the API

```bash
python main.py
# OR
uvicorn apps.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open the API docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/api/v1/health
- **Metrics**: http://localhost:8000/metrics

---

## Project Structure

```
helix-finance-ai/
│
├── apps/               # FastAPI application (gateway, routes, middleware, schemas)
│   ├── api/v1/         # Route handlers (auth, chat, documents, aml, kyc, compliance)
│   ├── middleware/     # Rate limiter + audit log
│   ├── schemas/        # Pydantic request/response models
│   ├── config.py       # Centralised settings from .env
│   ├── dependencies.py # Shared FastAPI dependencies
│   └── main.py         # FastAPI app factory
│
├── agents/             # LangGraph orchestration layer
│   ├── orchestrator.py # Graph builder and runner
│   ├── planner.py      # Planner agent
│   ├── task_router.py  # Task routing agent
│   ├── retriever.py    # RAG retriever agent
│   ├── verifier.py     # Output verification agent
│   ├── guardrails.py   # Safety and compliance filters
│   └── specialist/     # AML, KYC, Compliance specialist agents
│
├── rag/                # RAG pipeline
│   ├── ingest/         # Parse → Clean → Metadata → Chunk → Embed → Qdrant
│   └── query/          # Rewrite → Hybrid Search → Rerank → Context Builder
│
├── security/           # JWT handler + bcrypt password hashing
├── evaluation/         # Ragas + DeepEval evaluation
├── observability/      # Prometheus metrics + Langfuse tracing
├── infrastructure/     # DB, Redis, Qdrant, MinIO, RabbitMQ clients
│   └── docker/         # docker-compose.yml + prometheus.yml
├── workers/            # Celery background tasks (ingest, evaluation)
└── tests/              # Pytest test suite
```

---

## API Endpoints

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| GET | `/api/v1/health` | Liveness probe | ✅ Implemented |
| GET | `/api/v1/health/ready` | Readiness probe | 🔧 Stub |
| POST | `/api/v1/auth/login` | User login | 🔧 Stub |
| POST | `/api/v1/auth/refresh` | Refresh token | 🔧 Stub |
| POST | `/api/v1/auth/logout` | Logout | 🔧 Stub |
| GET | `/api/v1/auth/me` | Current user | 🔧 Stub |
| POST | `/api/v1/chat/query` | RAG query | 🔧 Stub |
| POST | `/api/v1/documents/upload` | Upload document | 🔧 Stub |
| GET | `/api/v1/documents` | List documents | 🔧 Stub |
| GET | `/api/v1/documents/{id}` | Get document | 🔧 Stub |
| DELETE | `/api/v1/documents/{id}` | Delete document | 🔧 Stub |
| POST | `/api/v1/aml/analyze` | AML analysis | 🔧 Stub |
| POST | `/api/v1/kyc/verify` | KYC verification | 🔧 Stub |
| POST | `/api/v1/compliance/check` | Compliance check | 🔧 Stub |
| GET | `/metrics` | Prometheus metrics | ✅ Implemented |

---

## Technology Stack

| Layer | Local (Free) | Production |
|---|---|---|
| API | FastAPI + Uvicorn | FastAPI + NGINX/Ingress |
| Agents | LangGraph | LangGraph |
| LLM Gateway | LiteLLM | LiteLLM |
| LLM | Ollama/llama3 | Azure OpenAI / GPT-4o |
| Embeddings | BAAI/bge-small-en-v1.5 | Managed Embedding Service |
| Database | PostgreSQL | HA PostgreSQL |
| Cache | Redis | Redis Cluster |
| Vector DB | Qdrant | Qdrant Cloud |
| Storage | MinIO | AWS S3 / Azure Blob |
| Queue | RabbitMQ | RabbitMQ Cluster / Kafka |
| Workers | Celery | Celery / Temporal |
| Monitoring | Prometheus + Grafana | Managed Monitoring |
| LLM Tracing | Langfuse | Langfuse Cloud |
| RAG Debug | Phoenix | Phoenix |
| Evaluation | Ragas + DeepEval | Same |
| Deployment | Docker Compose | Kubernetes |

---

## Infrastructure Services (Docker)

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

| Service | URL | Credentials |
|---|---|---|
| PostgreSQL | localhost:5432 | helix_user / helix_pass |
| Redis | localhost:6379 | — |
| Qdrant | localhost:6333 | — |
| Qdrant Dashboard | localhost:6333/dashboard | — |
| MinIO API | localhost:9000 | minioadmin / minioadmin |
| MinIO Console | localhost:9001 | minioadmin / minioadmin |
| RabbitMQ AMQP | localhost:5672 | guest / guest |
| RabbitMQ Management | localhost:15672 | guest / guest |
| Prometheus | localhost:9090 | — |
| Grafana | localhost:3001 | admin / admin |