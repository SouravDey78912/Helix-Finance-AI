# AI Financial Operations Platform (Production Learning Architecture)

## Vision
Build an enterprise-grade, Multi-Agent RAG platform for the FinTech domain using **100% free and open-source technologies for local development**, while designing every component so it can later be replaced with enterprise-managed services.

## Project Philosophy

Design like an enterprise.
Build with open source.

## Technology Matrix

| Layer | Local Development (Free) | Production Equivalent |
|---|---|---|
| API | FastAPI | FastAPI + NGINX/Ingress |
| Agent Framework | LangGraph | LangGraph |
| LLM Gateway | LiteLLM | LiteLLM |
| LLM | Ollama / OpenAI API | Azure OpenAI / OpenAI / Gemini |
| Embeddings | BAAI BGE / Nomic | Managed Embedding Service |
| Database | PostgreSQL | HA PostgreSQL |
| Cache | Redis | Redis Cluster |
| Vector DB | Qdrant | Qdrant Cluster / Qdrant Cloud |
| Object Storage | MinIO | AWS S3 / Azure Blob |
| Queue | RabbitMQ | RabbitMQ Cluster / Kafka |
| Workers | Celery | Celery / Temporal |
| Monitoring | Prometheus + Grafana | Managed Prometheus/Grafana |
| LLM Observability | Langfuse | Langfuse Cloud/Self-hosted |
| RAG Debugging | Phoenix | Phoenix |
| Evaluation | Ragas + DeepEval | Same |
| Deployment | Docker Compose | Kubernetes |
| CI/CD | GitHub Actions | GitHub Actions / ArgoCD |

## Engineering Goals
- Production architecture
- Security by design
- Observable AI
- Evaluatable AI
- Cloud-portable
- Beginner-friendly implementation

## Core Capabilities & Features
- **Hybrid RAG Pipeline**: Reciprocal Rank Fusion (RRF) query rewriting, dense vector search (Qdrant), and cross-encoder reranking.
- **Structured Entity & Requirement Extraction**: Automatic domain entity parsing (`Regulation`, `Requirement`, `Internal Control`, `Evidence`) during document ingestion using `rag/ingest/entity_extractor.py`.
- **Compliance Gap Analysis Engine**: Graph-based compliance relationship builder (`rag/compliance_graph.py`) identifying unmapped requirements and missing evidence with automated severity scoring (`HIGH`, `MEDIUM`, `LOW`).
- **Interactive Compliance Command Center**: Modern glassmorphism UI with real-time gap analysis cards, document manager, live query execution, and explicit PREVIEW state tags for target benchmark metrics.

## Repository
```text
apps/
agents/
rag/
  ingest/
    cleaner.py
    chunker.py
    embedder.py
    entity_extractor.py
    metadata_extractor.py
    parser.py
  query/
    context_builder.py
    hybrid_search.py
    reranker.py
    rewriter.py
  compliance_graph.py
  pipeline.py
security/
evaluation/
observability/
infrastructure/
docs/
tests/
```

