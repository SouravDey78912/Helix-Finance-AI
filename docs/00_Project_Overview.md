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

## Repository
```text
apps/
agents/
rag/
security/
evaluation/
observability/
infrastructure/
docs/
tests/
```
