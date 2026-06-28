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


from infrastructure.database import init_db, engine
from infrastructure.redis_client import get_redis_client, close_redis

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle hooks."""
    logger.info(
        "Helix Finance AI starting",
        version=settings.app_version,
        env=settings.app_env,
    )
    # Initialise DB tables (Development only auto-creates tables)
    if settings.app_env == "development":
        logger.info("Initializing database tables for development")
        try:
            await init_db()
        except Exception as e:
            logger.error("Failed to initialize database tables", error=str(e))

    # Initialise Redis connection
    try:
        await get_redis_client()
    except Exception as e:
        logger.error("Failed to initialize Redis connection", error=str(e))
        
    yield
    logger.info("Helix Finance AI shutting down")
    # Close Redis connection
    await close_redis()
    # Close DB connection pool
    await engine.dispose()
    logger.info("Database connection pool disposed")



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
