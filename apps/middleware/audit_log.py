"""
apps/middleware/audit_log.py
=============================
Request/Response audit trail middleware (stub).

Logs every request with: method, path, status, duration, and client IP.

TODO: Persist audit records to PostgreSQL audit_logs table.
TODO: Mask PII fields (account numbers, SSN) before logging.

Production equivalent: Centralized audit log service / SIEM integration.
"""

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

# Paths to exclude from audit logging (health checks / metrics)
_EXCLUDED_PATHS = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Structured audit log for every API request.

    Each request is assigned a unique request_id propagated in the
    X-Request-ID response header for distributed tracing.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Attach request_id to structlog context for this request
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            logger.info(
                "request_received",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )

            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                # TODO: log authenticated user_id once auth layer is implemented
            )

        response.headers["X-Request-ID"] = request_id
        return response
