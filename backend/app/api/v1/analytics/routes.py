import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.business.analytics import (
    assess_attrition_risk, get_attendance_summary, get_headcount_by_department, get_leave_utilization, get_payroll_cost_trend,
)
from app.database.connection.database import get_db
from app.database.models.analytics import EmployeeExit
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.user import User
from app.database.schemas.analytics import (
    AttendanceSummary, AttritionRiskOut, ExitCreate, ExitOut, HeadcountItem, LeaveUtilizationItem, PayrollCostItem,
)
from app.dependencies.auth import get_current_user, require_permission
from app.services.llm_client import LLMClient, get_llm_client

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/headcount", response_model=list[HeadcountItem], dependencies=[Depends(require_permission("analytics:read"))])
def headcount_by_department(db: Session = Depends(get_db)):
    return get_headcount_by_department(db)


@router.get("/attendance-summary", response_model=AttendanceSummary, dependencies=[Depends(require_permission("analytics:read"))])
def attendance_summary(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    return get_attendance_summary(db, start, end)


@router.get("/leave-utilization", response_model=list[LeaveUtilizationItem], dependencies=[Depends(require_permission("analytics:read"))])
def leave_utilization(year: int | None = None, db: Session = Depends(get_db)):
    return get_leave_utilization(db, year or date.today().year)


@router.get("/payroll-cost-trend", response_model=list[PayrollCostItem], dependencies=[Depends(require_permission("analytics:read"))])
def payroll_cost_trend(year: int | None = None, db: Session = Depends(get_db)):
    return get_payroll_cost_trend(db, year or date.today().year)


@router.get(
    "/attrition-risk/{employee_id}",
    response_model=AttritionRiskOut,
    dependencies=[Depends(require_permission("analytics:attrition_risk"))],
)
def attrition_risk(employee_id: uuid.UUID, db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_client)):
    """
    Advisory, per-employee, on-demand only -- see app/business/analytics.py
    module docstring for why this is deliberately not a batch/mass-scoring
    endpoint, and why it's a qualitative LLM assessment rather than a
    trained predictive model (no historical exit dataset exists yet).
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    result = assess_attrition_risk(db, employee, llm)
    return AttritionRiskOut(employee_id=employee.id, **{k: v for k, v in result.items() if k != "employee_id"})


# --- Employee exits ---

@router.post("/exits", response_model=ExitOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("employee:exit"))])
def record_exit(payload: ExitCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")

    existing = db.query(EmployeeExit).filter(EmployeeExit.employee_id == payload.employee_id).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An exit record already exists for this employee")

    exit_record = EmployeeExit(**payload.model_dump(), recorded_by_id=current_user.id)
    db.add(exit_record)
    employee.employment_status = EmploymentStatus.TERMINATED  # covers resignation/termination/retirement/end-of-contract alike
    db.commit()
    db.refresh(exit_record)
    return ExitOut.model_validate(exit_record)


@router.get("/exits", response_model=list[ExitOut], dependencies=[Depends(require_permission("analytics:read"))])
def list_exits(db: Session = Depends(get_db)):
    return [ExitOut.model_validate(e) for e in db.query(EmployeeExit).all()]
