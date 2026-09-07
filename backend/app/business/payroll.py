"""
Payroll business logic.

See app/database/models/payroll.py module docstring for the statutory-rate
disclaimer -- everything computed here (PF, ESI, PT) uses whatever is
currently in PayrollConfig, which starts out seeded with PLACEHOLDER values.
TDS is never computed here -- it's set to 0 at generation time and must be
entered manually before finance approval.
"""
import calendar
from datetime import date as date_type, datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.database.models.attendance import Attendance, AttendanceStatus
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.payroll import PayrollConfig, PayrollRun, PayrollRunStatus, Payslip, SalaryStructure
from app.database.models.user import User


def get_current_salary_structure(db: Session, employee_id, as_of: date_type) -> SalaryStructure:
    structure = (
        db.query(SalaryStructure)
        .filter(SalaryStructure.employee_id == employee_id, SalaryStructure.effective_from <= as_of)
        .order_by(SalaryStructure.effective_from.desc())
        .first()
    )
    if structure is None:
        raise AppError(f"No salary structure defined for this employee as of {as_of}. Set one before running payroll.")
    return structure


def get_active_config(db: Session) -> PayrollConfig:
    config = db.query(PayrollConfig).order_by(PayrollConfig.created_at.desc()).first()
    if config is None:
        raise AppError("No payroll configuration exists. Run the seed script first.", status_code=500)
    return config


def _count_attendance_days(db: Session, employee_id, year: int, month: int) -> dict:
    days_in_month = calendar.monthrange(year, month)[1]
    records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= date_type(year, month, 1),
        Attendance.date <= date_type(year, month, days_in_month),
    ).all()

    present = sum(1 for r in records if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY, AttendanceStatus.HOLIDAY))
    on_leave = sum(1 for r in records if r.status == AttendanceStatus.ON_LEAVE)
    marked_days = len(records)
    lop = days_in_month - marked_days

    return {"days_in_month": days_in_month, "days_present": present, "days_on_leave": on_leave, "days_lop": lop}


def calculate_payslip(db: Session, employee: Employee, year: int, month: int, config: PayrollConfig) -> dict:
    """Pure calculation, returns a dict of field values -- no DB writes here,
    the caller decides whether to persist. Kept separate from generate_payroll_run
    so this specific math can be unit-tested in isolation."""
    period_end = date_type(year, month, calendar.monthrange(year, month)[1])
    structure = get_current_salary_structure(db, employee.id, period_end)
    attendance = _count_attendance_days(db, employee.id, year, month)

    payable_days = attendance["days_in_month"] - attendance["days_lop"]
    proration = payable_days / attendance["days_in_month"] if attendance["days_in_month"] else 0

    basic = round(structure.basic * proration, 2)
    hra = round(structure.hra * proration, 2)
    other_allowances = round(structure.other_allowances * proration, 2)
    gross_salary = round(basic + hra + other_allowances, 2)

    pf_deduction = round(min(basic, config.pf_wage_ceiling) * (config.pf_rate_percent / 100), 2)
    esi_deduction = round(gross_salary * (config.esi_rate_percent / 100), 2) if gross_salary < config.esi_wage_threshold else 0.0
    pt_deduction = config.pt_amount if gross_salary > 0 else 0.0

    net_salary = round(gross_salary - pf_deduction - esi_deduction - pt_deduction, 2)

    return {
        "basic": basic, "hra": hra, "other_allowances": other_allowances,
        "overtime_amount": 0.0, "bonus_amount": 0.0, "gross_salary": gross_salary,
        "days_in_period": attendance["days_in_month"], "days_present": attendance["days_present"],
        "days_on_leave": attendance["days_on_leave"], "days_lop": attendance["days_lop"],
        "pf_deduction": pf_deduction, "esi_deduction": esi_deduction, "pt_deduction": pt_deduction,
        "tds_amount": 0.0, "net_salary": net_salary,
    }


def generate_payroll_run(db: Session, year: int, month: int, created_by: User) -> PayrollRun:
    existing = db.query(PayrollRun).filter(PayrollRun.period_year == year, PayrollRun.period_month == month).first()
    if existing is not None:
        raise AppError(f"A payroll run for {year}-{month:02d} already exists (status: {existing.status.value}).")

    config = get_active_config(db)
    run = PayrollRun(period_year=year, period_month=month, created_by_id=created_by.id, status=PayrollRunStatus.DRAFT)
    db.add(run)
    db.flush()

    active_employees = db.query(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE).all()
    for employee in active_employees:
        try:
            values = calculate_payslip(db, employee, year, month, config)
        except AppError:
            continue  # no salary structure set -- skip, don't fail the whole run
        payslip = Payslip(payroll_run_id=run.id, employee_id=employee.id, **values)
        db.add(payslip)

    db.commit()
    db.refresh(run)
    return run


def approve_hr(db: Session, run: PayrollRun, approver: User) -> PayrollRun:
    if run.status != PayrollRunStatus.DRAFT:
        raise AppError(f"Cannot HR-approve a run that is '{run.status.value}' (expected 'draft').")
    run.status = PayrollRunStatus.HR_APPROVED
    run.hr_approved_by_id = approver.id
    run.hr_approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def approve_finance(db: Session, run: PayrollRun, approver: User) -> PayrollRun:
    if run.status != PayrollRunStatus.HR_APPROVED:
        raise AppError(f"Cannot finance-approve a run that is '{run.status.value}' (expected 'hr_approved').")
    run.status = PayrollRunStatus.FINANCE_APPROVED
    run.finance_approved_by_id = approver.id
    run.finance_approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def mark_paid(db: Session, run: PayrollRun) -> PayrollRun:
    if run.status != PayrollRunStatus.FINANCE_APPROVED:
        raise AppError(f"Cannot mark a run paid when it is '{run.status.value}' (expected 'finance_approved').")
    run.status = PayrollRunStatus.PAID
    run.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run
