"""
apps/main.py
============
FastAPI application factory.

Architecture flow (from 01_System_Architecture.md):
  User → FastAPI Gateway → Auth → Rate Limiter → Validation
       → LangGraph Orchestrator → Planner → Task Router
       → Specialist Agents → Verifier → Guardrails
       → Response → Audit Log → Metrics
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from apps.api.v1.router import v1_router
from apps.config import get_settings
from apps.middleware.audit_log import AuditLogMiddleware
from apps.middleware.rate_limiter import RateLimiterMiddleware

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle hooks."""
    logger.info(
        "Helix Finance AI starting",
        version=settings.app_version,
        env=settings.app_env,
    )
    # TODO: initialise DB connection pool (infrastructure/database.py)
    # TODO: initialise Redis connection (infrastructure/redis_client.py)
    # TODO: initialise Qdrant client (infrastructure/qdrant_client.py)
    # TODO: initialise MinIO client (infrastructure/minio_client.py)
    # TODO: initialise Langfuse tracing (observability/tracing.py)
    yield
    logger.info("Helix Finance AI shutting down")
    # TODO: close DB connection pool
    # TODO: close Redis connection


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise-grade Multi-Agent RAG platform for FinTech.\n\n"
            "**Architecture**: FastAPI Gateway → LangGraph Orchestrator → "
            "Specialist Agents (AML, KYC, Compliance) → RAG Pipeline → Response"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware (order: outermost first) ─────────────────────────
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(RateLimiterMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix=settings.api_prefix)

    # ── Prometheus metrics endpoint ───────────────────────────────────────
    if settings.prometheus_enabled:
        metrics_app = make_asgi_app()
        app.mount(settings.metrics_path, metrics_app)

    # ── Global exception handler ──────────────────────────────────────────
    @app.exception_handler(NotImplementedError)
    async def not_implemented_handler(request, exc):
        return JSONResponse(
            status_code=501,
            content={
                "detail": "This endpoint is not yet implemented.",
                "status": "not_implemented",
            },
        )

    return app


app = create_app()
