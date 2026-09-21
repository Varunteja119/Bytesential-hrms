import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.business.leave import LEAVE_ALLOCATIONS, approve_leave, apply_leave, cancel_leave, get_or_create_balance, reject_leave
from app.dependencies.auth import get_current_user, require_permission
from app.database.connection.database import get_db
from app.database.models.employee import Employee
from app.database.models.leave import LeaveRequest
from app.database.models.user import User
from app.database.schemas.leave import LeaveApplyRequest, LeaveBalanceOut, LeaveRejectRequest, LeaveRequestOut

router = APIRouter(prefix="/leave", tags=["leave"])


def _get_own_employee_record(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record linked to your account")
    return employee


def _get_request_or_404(db: Session, request_id: uuid.UUID) -> LeaveRequest:
    request = db.get(LeaveRequest, request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave request not found")
    return request


@router.post("/apply", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def apply(payload: LeaveApplyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    request = apply_leave(db, employee, payload.leave_type, payload.start_date, payload.end_date, payload.reason)
    return LeaveRequestOut.model_validate(request)


@router.get("/me", response_model=list[LeaveRequestOut])
def get_my_leave_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    requests = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee.id).order_by(LeaveRequest.start_date.desc()).all()
    return [LeaveRequestOut.model_validate(r) for r in requests]


@router.get("/balance/me", response_model=list[LeaveBalanceOut])
def get_my_leave_balance(year: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    target_year = year or date.today().year
    balances = [get_or_create_balance(db, employee.id, lt, target_year) for lt in LEAVE_ALLOCATIONS]
    return [LeaveBalanceOut.from_orm_balance(b) for b in balances]


@router.post("/{request_id}/cancel", response_model=LeaveRequestOut)
def cancel(request_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    request = _get_request_or_404(db, request_id)
    updated = cancel_leave(db, request, employee)
    return LeaveRequestOut.model_validate(updated)


@router.get("", response_model=list[LeaveRequestOut], dependencies=[Depends(require_permission("leave:read"))])
def list_leave_requests(employee_id: uuid.UUID | None = None, status_filter: str | None = None, db: Session = Depends(get_db)):
    query = db.query(LeaveRequest)
    if employee_id is not None:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    if status_filter is not None:
        query = query.filter(LeaveRequest.status == status_filter)
    return [LeaveRequestOut.model_validate(r) for r in query.order_by(LeaveRequest.start_date.desc()).all()]


@router.post("/{request_id}/approve", response_model=LeaveRequestOut, dependencies=[Depends(require_permission("leave:approve"))])
def approve(request_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    request = _get_request_or_404(db, request_id)
    updated = approve_leave(db, request, current_user)
    return LeaveRequestOut.model_validate(updated)


@router.post("/{request_id}/reject", response_model=LeaveRequestOut, dependencies=[Depends(require_permission("leave:approve"))])
def reject(request_id: uuid.UUID, payload: LeaveRejectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    request = _get_request_or_404(db, request_id)
    updated = reject_leave(db, request, current_user, payload.rejection_reason)
    return LeaveRequestOut.model_validate(updated)
