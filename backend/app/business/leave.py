from datetime import date as date_type, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.exceptions import AppError
from app.database.models.attendance import Attendance, AttendanceStatus
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.leave import LeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from app.database.models.user import User

LEAVE_ALLOCATIONS: dict[LeaveType, int] = {LeaveType.CASUAL: 12, LeaveType.SICK: 12, LeaveType.EARNED: 15}


def calculate_days(start_date: date_type, end_date: date_type) -> int:
    return (end_date - start_date).days + 1


def get_or_create_balance(db: Session, employee_id, leave_type: LeaveType, year: int) -> LeaveBalance:
    balance = db.query(LeaveBalance).filter(LeaveBalance.employee_id == employee_id, LeaveBalance.leave_type == leave_type, LeaveBalance.year == year).first()
    if balance is None:
        allocated = LEAVE_ALLOCATIONS.get(leave_type, 0)
        balance = LeaveBalance(employee_id=employee_id, leave_type=leave_type, year=year, allocated_days=allocated, used_days=0)
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def apply_leave(db: Session, employee: Employee, leave_type: LeaveType, start_date: date_type, end_date: date_type, reason: str | None) -> LeaveRequest:
    if employee.employment_status != EmploymentStatus.ACTIVE:
        raise AppError("Only active employees can apply for leave.")
    if end_date < start_date:
        raise AppError("end_date cannot be before start_date.")
    days = calculate_days(start_date, end_date)
    if leave_type != LeaveType.UNPAID:
        balance = get_or_create_balance(db, employee.id, leave_type, start_date.year)
        remaining = balance.allocated_days - balance.used_days
        if days > remaining:
            raise AppError(f"Insufficient {leave_type.value} leave balance: requested {days} day(s), {remaining} remaining.")
    overlapping = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
        LeaveRequest.start_date <= end_date, LeaveRequest.end_date >= start_date,
    ).first()
    if overlapping is not None:
        raise AppError("You already have a pending or approved leave request that overlaps these dates.")
    request = LeaveRequest(employee_id=employee.id, leave_type=leave_type, start_date=start_date, end_date=end_date,
                            days_requested=days, reason=reason, status=LeaveStatus.PENDING)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_leave(db: Session, request: LeaveRequest, approver: User, note: str | None = None) -> LeaveRequest:
    if request.status != LeaveStatus.PENDING:
        raise AppError(f"Cannot approve a request that is already '{request.status.value}'.")
    if request.leave_type != LeaveType.UNPAID:
        balance = get_or_create_balance(db, request.employee_id, request.leave_type, request.start_date.year)
        balance.used_days += request.days_requested
    request.status = LeaveStatus.APPROVED
    request.decided_by_id = approver.id
    request.decided_at = datetime.now(timezone.utc)
    request.decision_note = note
    current = request.start_date
    while current <= request.end_date:
        att = db.query(Attendance).filter(Attendance.employee_id == request.employee_id, Attendance.date == current).first()
        if att is None:
            att = Attendance(employee_id=request.employee_id, date=current)
            db.add(att)
        att.status = AttendanceStatus.ON_LEAVE
        att.notes = f"Approved {request.leave_type.value} leave (request {request.id})"
        current += timedelta(days=1)
    db.commit()
    db.refresh(request)
    return request


def reject_leave(db: Session, request: LeaveRequest, approver: User, rejection_reason: str) -> LeaveRequest:
    if request.status != LeaveStatus.PENDING:
        raise AppError(f"Cannot reject a request that is already '{request.status.value}'.")
    request.status = LeaveStatus.REJECTED
    request.decided_by_id = approver.id
    request.decided_at = datetime.now(timezone.utc)
    request.decision_note = rejection_reason
    db.commit()
    db.refresh(request)
    return request


def cancel_leave(db: Session, request: LeaveRequest, employee: Employee) -> LeaveRequest:
    if request.employee_id != employee.id:
        raise AppError("You can only cancel your own leave requests.", status_code=403)
    if request.status != LeaveStatus.PENDING:
        raise AppError(f"Cannot cancel a request that is already '{request.status.value}'. Only pending requests can be cancelled.")
    request.status = LeaveStatus.CANCELLED
    db.commit()
    db.refresh(request)
    return request
