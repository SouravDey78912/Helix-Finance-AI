"""
apps/api/v1/health.py
======================
Health check endpoints.

GET /health        — lightweight liveness probe
GET /health/ready  — readiness probe (checks all dependencies)
"""

from fastapi import APIRouter
from pydantic import BaseModel

from apps.config import get_settings

router = APIRouter()
settings = get_settings()


class HealthStatus(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str


class ReadinessStatus(BaseModel):
    status: str
    checks: dict[str, str]


@router.get(
    "",
    response_model=HealthStatus,
    summary="Liveness probe",
    description="Returns 200 OK when the application process is running.",
)
async def health_check() -> HealthStatus:
    return HealthStatus(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    summary="Readiness probe",
    description=(
        "Checks all downstream dependencies and returns their status.\n\n"
        "**TODO**: Implement actual connection checks for PostgreSQL, Redis, "
        "Qdrant, MinIO, and RabbitMQ."
    ),
)
async def readiness_check() -> ReadinessStatus:
    # TODO: ping each infrastructure dependency and report real status
    checks = {
        "postgresql": "not_implemented",
        "redis": "not_implemented",
        "qdrant": "not_implemented",
        "minio": "not_implemented",
        "rabbitmq": "not_implemented",
    }
    overall = "degraded"  # will be "ok" once all checks pass
    return ReadinessStatus(status=overall, checks=checks)
