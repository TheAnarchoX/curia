"""Celery application instance for the Curia worker."""

from celery import Celery

from apps.worker.app.config import WorkerSettings

settings = WorkerSettings()

celery_app = Celery("curia")

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["apps.worker.app.tasks"])
