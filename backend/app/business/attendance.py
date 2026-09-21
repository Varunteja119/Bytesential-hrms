from datetime import date as date_type, datetime, time, timedelta, timezone
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.core.exceptions import AppError
from app.database.models.attendance import Attendance, AttendanceStatus
from app.database.models.employee import Employee, EmploymentStatus


def _get_or_create_today_record(db: Session, employee_id, today: date_type) -> Attendance:
    record = db.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.date == today).first()
    if record is None:
        record = Attendance(employee_id=employee_id, date=today, status=AttendanceStatus.PRESENT)
        db.add(record)
    return record


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _is_late(check_in_time: datetime) -> bool:
    check_in_time = _ensure_aware(check_in_time)
    work_start = time(hour=settings.work_start_hour, minute=settings.work_start_minute)
    scheduled_start = datetime.combine(check_in_time.date(), work_start, tzinfo=check_in_time.tzinfo)
    grace_cutoff = scheduled_start + timedelta(minutes=settings.late_grace_minutes)
    return check_in_time > grace_cutoff


def record_check_in(db: Session, employee: Employee) -> Attendance:
    if employee.employment_status != EmploymentStatus.ACTIVE:
        raise AppError("Only active employees can mark attendance. Complete onboarding and activation first.")
    now = datetime.now(timezone.utc)
    today = now.date()
    record = _get_or_create_today_record(db, employee.id, today)
    if record.check_in_time is not None:
        raise AppError("Already checked in today.")
    record.check_in_time = now
    record.is_late = _is_late(now)
    record.status = AttendanceStatus.PRESENT
    db.commit()
    db.refresh(record)
    return record


def record_check_out(db: Session, employee: Employee) -> Attendance:
    now = datetime.now(timezone.utc)
    today = now.date()
    record = db.query(Attendance).filter(Attendance.employee_id == employee.id, Attendance.date == today).first()
    if record is None or record.check_in_time is None:
        raise AppError("Must check in before checking out.")
    if record.check_out_time is not None:
        raise AppError("Already checked out today.")
    record.check_out_time = now
    work_seconds = (now - _ensure_aware(record.check_in_time)).total_seconds()
    record.work_hours = round(work_seconds / 3600, 2)
    if record.work_hours < settings.half_day_hours_threshold:
        record.status = AttendanceStatus.HALF_DAY
    db.commit()
    db.refresh(record)
    return record
