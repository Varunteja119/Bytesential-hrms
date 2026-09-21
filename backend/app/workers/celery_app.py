"""
Celery app instance. UNTESTED against a live worker/broker in this
environment (no Redis broker available here) -- task logic itself is
tested directly as a function call in tests/test_payroll.py, but running
this through an actual Celery worker process hasn't been verified.
"""
from celery import Celery
from app.config.settings import settings

celery_app = Celery("bytesentinel", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

celery_app.autodiscover_tasks(["app.tasks"])
