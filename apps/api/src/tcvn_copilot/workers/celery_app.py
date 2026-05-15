"""Celery application factory."""

from __future__ import annotations

from celery import Celery

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.logging import configure_logging

settings = get_settings()
configure_logging()

celery_app = Celery(
    "tcvn_copilot",
    broker=str(settings.celery_broker_url),
    backend=str(settings.celery_result_backend),
    include=["tcvn_copilot.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=60 * 30,  # 30 min hard cap
    task_soft_time_limit=60 * 25,
    worker_max_tasks_per_child=50,  # recycle to free memory after big runs
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
