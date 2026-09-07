import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.business.attendance import record_check_in, record_check_out
from app.dependencies.auth import get_current_user, require_permission
from app.database.connection.database import get_db
from app.database.models.attendance import Attendance
from app.database.models.employee import Employee
from app.database.models.user import User
from app.database.schemas.attendance import AttendanceMarkRequest, AttendanceOut

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _get_own_employee_record(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record linked to your account")
    return employee


def _require_self_or_permission(employee: Employee, user: User, permission_code: str) -> None:
    if employee.user_id == user.id:
        return
    if user.is_superuser or user.has_permission(permission_code):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only access your own attendance records")


@router.post("/check-in", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def check_in(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    record = record_check_in(db, employee)  # raises AppError (400) on double check-in or inactive employee
    return AttendanceOut.model_validate(record)


@router.post("/check-out", response_model=AttendanceOut)
def check_out(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    record = record_check_out(db, employee)  # raises AppError (400) if no check-in yet or already checked out
    return AttendanceOut.model_validate(record)


@router.get("/me", response_model=list[AttendanceOut])
def get_my_attendance(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = _get_own_employee_record(db, current_user)
    query = db.query(Attendance).filter(Attendance.employee_id == employee.id)
    if start_date is not None:
        query = query.filter(Attendance.date >= start_date)
    if end_date is not None:
        query = query.filter(Attendance.date <= end_date)
    return [AttendanceOut.model_validate(r) for r in query.order_by(Attendance.date.desc()).all()]


@router.get("/{employee_id}", response_model=list[AttendanceOut])
def get_employee_attendance(
    employee_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    _require_self_or_permission(employee, current_user, "attendance:read")

    query = db.query(Attendance).filter(Attendance.employee_id == employee_id)
    if start_date is not None:
        query = query.filter(Attendance.date >= start_date)
    if end_date is not None:
        query = query.filter(Attendance.date <= end_date)
    return [AttendanceOut.model_validate(r) for r in query.order_by(Attendance.date.desc()).all()]


@router.post(
    "/{employee_id}/mark",
    response_model=AttendanceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("attendance:write"))],
)
def mark_attendance(employee_id: uuid.UUID, payload: AttendanceMarkRequest, db: Session = Depends(get_db)):
    """
    HR manual entry/correction — e.g. marking a company holiday across
    employees, or recording an absence for someone who never checked in.
    Upserts: one record per (employee, date), same rule as check-in/out.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")

    record = db.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.date == payload.date).first()
    if record is None:
        record = Attendance(employee_id=employee_id, date=payload.date)
        db.add(record)

    record.status = payload.status
    record.notes = payload.notes
    db.commit()
    db.refresh(record)
    return AttendanceOut.model_validate(record)
