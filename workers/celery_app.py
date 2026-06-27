"""
workers/celery_app.py
======================
Celery application instance.

Broker:          RabbitMQ (local Docker) → RabbitMQ Cluster / Kafka (production)
Result Backend:  Redis

Local run:
    celery -A workers.celery_app worker --loglevel=info

Production: Deploy as separate Kubernetes pod or use Temporal for durability.
"""

from celery import Celery

from infrastructure.rabbitmq_client import get_broker_url, get_result_backend_url

celery_app = Celery(
    "helix_finance",
    broker=get_broker_url(),
    backend=get_result_backend_url(),
    include=[
        "workers.tasks.ingest_task",
        "workers.tasks.eval_task",
    ],
)

# ── Configuration ─────────────────────────────────────────────────────────────
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                    # re-queue on worker crash
    worker_prefetch_multiplier=1,           # fair dispatch
    task_routes={
        "workers.tasks.ingest_task.*": {"queue": "ingest"},
        "workers.tasks.eval_task.*": {"queue": "evaluation"},
    },
)
