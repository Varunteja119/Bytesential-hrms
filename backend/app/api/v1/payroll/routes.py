import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.business.payroll import approve_finance, approve_hr, generate_payroll_run, mark_paid
from app.core.exceptions import AppError
from app.database.connection.database import get_db
from app.database.models.employee import Employee
from app.database.models.payroll import PayrollConfig, PayrollRun, Payslip, SalaryStructure
from app.database.models.user import User
from app.database.schemas.payroll import (PayrollConfigOut, PayrollConfigUpdate, PayrollRunCreate, PayrollRunOut,
                                           PayslipOut, PayslipUpdate, SalaryStructureCreate, SalaryStructureOut)
from app.dependencies.auth import get_current_user, require_permission

router = APIRouter(prefix="/payroll", tags=["payroll"])


def _get_run_or_404(db: Session, run_id: uuid.UUID) -> PayrollRun:
    run = db.get(PayrollRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")
    return run


def _get_own_employee_record(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record linked to your account")
    return employee


@router.get("/config", response_model=PayrollConfigOut, dependencies=[Depends(require_permission("payroll:read"))])
def get_config(db: Session = Depends(get_db)):
    config = db.query(PayrollConfig).order_by(PayrollConfig.created_at.desc()).first()
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No payroll config exists yet -- run the seed script.")
    return PayrollConfigOut.model_validate(config)


@router.patch("/config", response_model=PayrollConfigOut, dependencies=[Depends(require_permission("payroll:manage"))])
def update_config(payload: PayrollConfigUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    config = db.query(PayrollConfig).order_by(PayrollConfig.created_at.desc()).first()
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No payroll config exists yet -- run the seed script.")
    for field, value in payload.model_dump().items():
        setattr(config, field, value)
    config.updated_by_id = current_user.id
    db.commit()
    db.refresh(config)
    return PayrollConfigOut.model_validate(config)


@router.post("/salary-structure", response_model=SalaryStructureOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("payroll:manage"))])
def set_salary_structure(payload: SalaryStructureCreate, db: Session = Depends(get_db)):
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    structure = SalaryStructure(**payload.model_dump())
    db.add(structure)
    db.commit()
    db.refresh(structure)
    return SalaryStructureOut.model_validate(structure)


@router.get("/salary-structure/{employee_id}", response_model=list[SalaryStructureOut], dependencies=[Depends(require_permission("payroll:read"))])
def get_salary_structure_history(employee_id: uuid.UUID, db: Session = Depends(get_db)):
    structures = db.query(SalaryStructure).filter(SalaryStructure.employee_id == employee_id).order_by(SalaryStructure.effective_from.desc()).all()
    return [SalaryStructureOut.model_validate(s) for s in structures]


@router.post("/runs", response_model=PayrollRunOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("payroll:manage"))])
def create_payroll_run(payload: PayrollRunCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = generate_payroll_run(db, payload.period_year, payload.period_month, current_user)
    return PayrollRunOut.from_orm_run(run)


@router.get("/runs", response_model=list[PayrollRunOut], dependencies=[Depends(require_permission("payroll:read"))])
def list_payroll_runs(db: Session = Depends(get_db)):
    runs = db.query(PayrollRun).order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc()).all()
    return [PayrollRunOut.from_orm_run(r) for r in runs]


@router.get("/runs/{run_id}", response_model=PayrollRunOut, dependencies=[Depends(require_permission("payroll:read"))])
def get_payroll_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    return PayrollRunOut.from_orm_run(_get_run_or_404(db, run_id))


@router.get("/runs/{run_id}/payslips", response_model=list[PayslipOut], dependencies=[Depends(require_permission("payroll:read"))])
def list_payslips(run_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    payslips = db.query(Payslip).filter(Payslip.payroll_run_id == run_id).all()
    return [PayslipOut.model_validate(p) for p in payslips]


@router.patch("/payslips/{payslip_id}", response_model=PayslipOut, dependencies=[Depends(require_permission("payroll:manage"))])
def update_payslip(payslip_id: uuid.UUID, payload: PayslipUpdate, db: Session = Depends(get_db)):
    payslip = db.get(Payslip, payslip_id)
    if payslip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payslip not found")
    run = _get_run_or_404(db, payslip.payroll_run_id)
    if run.status.value != "draft":
        raise AppError(f"Cannot adjust a payslip on a run that is already '{run.status.value}'.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(payslip, field, value)
    payslip.net_salary = round(payslip.gross_salary + payslip.overtime_amount + payslip.bonus_amount
                                - payslip.pf_deduction - payslip.esi_deduction - payslip.pt_deduction - payslip.tds_amount, 2)
    db.commit()
    db.refresh(payslip)
    return PayslipOut.model_validate(payslip)


@router.post("/runs/{run_id}/approve-hr", response_model=PayrollRunOut, dependencies=[Depends(require_permission("payroll:approve_hr"))])
def approve_run_hr(run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = _get_run_or_404(db, run_id)
    updated = approve_hr(db, run, current_user)
    return PayrollRunOut.from_orm_run(updated)


@router.post("/runs/{run_id}/approve-finance", response_model=PayrollRunOut, dependencies=[Depends(require_permission("payroll:approve_finance"))])
def approve_run_finance(run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = _get_run_or_404(db, run_id)
    updated = approve_finance(db, run, current_user)
    return PayrollRunOut.from_orm_run(updated)


@router.post("/runs/{run_id}/mark-paid", response_model=PayrollRunOut, dependencies=[Depends(require_permission("payroll:manage"))])
def mark_run_paid(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    updated = mark_paid(db, run)
    return PayrollRunOut.from_orm_run(updated)


@router.get("/payslips/me", response_model=list[PayslipOut])
def get_my_payslips(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    payslips = db.query(Payslip).filter(Payslip.employee_id == employee.id).all()
    return [PayslipOut.model_validate(p) for p in payslips]
