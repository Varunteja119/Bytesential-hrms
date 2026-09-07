"""
Celery application instance.

⚠️ UNTESTED against a live worker in this environment (no Redis broker
or running worker available here — same tier as Ollama/MinIO). The task
logic itself (app/tasks/payroll_tasks.py) IS tested directly as a plain
function call, since that's what actually matters — Celery here is a thin
dispatch wrapper, not where the business logic lives.

To run for real: `celery -A app.workers.celery_app worker --loglevel=info`
"""
from celery import Celery

from app.config.settings import settings

celery_app = Celery("bytesentinel", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import task modules so Celery registers them when this app starts.
celery_app.autodiscover_tasks(["app.tasks"])
