"""
apps/middleware/rate_limiter.py
================================
Sliding-window rate limiter middleware (stub).

TODO: Replace the in-memory counter with Redis INCR + EXPIRE
      for distributed rate limiting in production.

Production equivalent: NGINX rate limiting / API Gateway throttling.
"""

import time
from collections import defaultdict

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# In-memory store: {client_ip: [(timestamp, count)]}
# TODO: Replace with Redis for multi-instance support
_request_counts: dict[str, list] = defaultdict(list)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.

    Limits: settings.rate_limit_requests per settings.rate_limit_window seconds.
    Currently uses in-memory store — replace with Redis for production.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = settings.rate_limit_window
        limit = settings.rate_limit_requests

        # Prune old entries outside the window
        _request_counts[client_ip] = [
            ts for ts in _request_counts[client_ip] if now - ts < window
        ]

        if len(_request_counts[client_ip]) >= limit:
            logger.warning("Rate limit exceeded", client_ip=client_ip)
            return Response(
                content='{"detail":"Rate limit exceeded","status":"too_many_requests"}',
                status_code=429,
                media_type="application/json",
            )

        _request_counts[client_ip].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(
            limit - len(_request_counts[client_ip])
        )
        return response
