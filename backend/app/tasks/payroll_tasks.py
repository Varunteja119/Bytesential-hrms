"""
Payroll Celery tasks -- thin wrappers around app/business/payroll.py so
the actual calculation logic stays testable without a live worker.
"""
from app.workers.celery_app import celery_app


@celery_app.task(name="payroll.generate_run")
def generate_payroll_run_task(run_id: str) -> str:
    """
    Placeholder entry point for running payroll generation on a worker
    instead of inline in the HTTP request. Not currently wired into the
    API route (see app/api/v1/payroll/routes.py create_payroll_run) --
    that calls the business logic directly for simplicity/testability.
    For real async processing at scale, call this task's .delay(run_id)
    instead.
    """
    return run_id
