from __future__ import annotations

from celery import Celery

from app.core.settings import settings

celery_app = Celery(
    "pdc",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.jobs.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)
