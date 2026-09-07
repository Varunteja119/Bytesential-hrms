"""
Payroll background tasks.

Deliberately thin: each task opens its own DB session and calls straight
into app/business/payroll.py, which is where the actual logic lives and
is tested directly (see tests/test_payroll.py). That split means this file
never needs its own business-logic tests -- it's just wiring.
"""
from app.database.connection.database import SessionLocal
from app.database.models.user import User
from app.workers.celery_app import celery_app


@celery_app.task(name="payroll.generate_run")
def generate_payroll_run_task(year: int, month: int, created_by_user_id: str) -> str:
    """
    Async equivalent of POST /payroll/runs. For a large employee count,
    generating every payslip inline in the HTTP request handler blocks
    that request for however long the calculation takes -- this lets a
    route enqueue the work instead: generate_payroll_run_task.delay(...).

    Not currently wired into the route (see app/api/v1/payroll/routes.py
    create_payroll_run docstring) -- the route still runs synchronously
    for now, since it's simpler to test and the employee counts involved
    so far don't require async. This task is the documented next step
    once that stops being true.
    """
    from app.business.payroll import generate_payroll_run
    import uuid

    db = SessionLocal()
    try:
        user = db.get(User, uuid.UUID(created_by_user_id))
        run = generate_payroll_run(db, year, month, user)
        return str(run.id)
    finally:
        db.close()
