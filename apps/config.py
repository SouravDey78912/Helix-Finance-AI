"""
apps/config.py
==============
Centralised settings loaded from environment variables / .env file.
All infrastructure connection strings live here — swap values in .env
to migrate between local Docker and production managed services.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "Helix Finance AI"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # ── Security ──────────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_super_secret_key_at_least_32_chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""


    # ── Rate Limiting ─────────────────────────────────────────────────────
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # ── PostgreSQL ────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "helix_finance"
    postgres_user: str = "helix_user"
    postgres_password: str = "helix_pass"
    database_url: str = (
        "postgresql+asyncpg://helix_user:helix_pass@localhost:5432/helix_finance"
    )

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"

    # ── Qdrant ────────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "helix_docs"
    qdrant_api_key: str = ""

    # ── MinIO ─────────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "helix-documents"
    minio_secure: bool = False

    # ── RabbitMQ / Celery ─────────────────────────────────────────────────
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── LLM / LiteLLM ────────────────────────────────────────────────────
    litellm_model: str = "ollama/llama3"
    litellm_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""

    # ── Embeddings ────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # ── Langfuse ──────────────────────────────────────────────────────────
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # ── Prometheus ────────────────────────────────────────────────────────
    prometheus_enabled: bool = True
    metrics_path: str = "/metrics"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
