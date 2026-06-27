"""
infrastructure/rabbitmq_client.py
===================================
RabbitMQ connection helpers and Celery broker configuration.

Local:       RabbitMQ in Docker Compose (free)
Production:  RabbitMQ Cluster / Apache Kafka

The Celery broker URL is configured in apps/config.py.
This module provides utility helpers for direct AMQP interactions
if needed outside the Celery task framework.

Migration path: Change CELERY_BROKER_URL to Kafka URL — minimal code change.
"""

import structlog

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def get_broker_url() -> str:
    """Return the Celery broker URL from settings."""
    return settings.celery_broker_url


def get_result_backend_url() -> str:
    """Return the Celery result backend URL from settings."""
    return settings.celery_result_backend


async def check_rabbitmq_health() -> bool:
    """
    Check if RabbitMQ is reachable.

    TODO: Implement connection attempt using aio-pika.
    Returns True if healthy, False otherwise.
    """
    raise NotImplementedError("RabbitMQ health check not yet implemented")
