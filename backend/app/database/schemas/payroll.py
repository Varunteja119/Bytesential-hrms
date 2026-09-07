import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.database.models.payroll import PayrollRunStatus


class PayrollConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    pf_rate_percent: float
    pf_wage_ceiling: float
    esi_rate_percent: float
    esi_wage_threshold: float
    pt_state: str
    pt_amount: float
    overtime_rate_multiplier: float


class PayrollConfigUpdate(BaseModel):
    pf_rate_percent: float = Field(gt=0)
    pf_wage_ceiling: float = Field(gt=0)
    esi_rate_percent: float = Field(ge=0)
    esi_wage_threshold: float = Field(ge=0)
    pt_state: str
    pt_amount: float = Field(ge=0)
    overtime_rate_multiplier: float = Field(gt=0)


class SalaryStructureCreate(BaseModel):
    employee_id: uuid.UUID
    basic: float = Field(gt=0)
    hra: float = Field(ge=0)
    other_allowances: float = Field(ge=0)
    effective_from: date


class SalaryStructureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    employee_id: uuid.UUID
    basic: float
    hra: float
    other_allowances: float
    effective_from: date


class PayrollRunCreate(BaseModel):
    period_year: int = Field(ge=2020, le=2100)
    period_month: int = Field(ge=1, le=12)


class PayrollRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    period_year: int
    period_month: int
    status: PayrollRunStatus
    hr_approved_by_id: uuid.UUID | None
    hr_approved_at: datetime | None
    finance_approved_by_id: uuid.UUID | None
    finance_approved_at: datetime | None
    paid_at: datetime | None
    payslip_count: int = 0

    @classmethod
    def from_orm_run(cls, run) -> "PayrollRunOut":
        return cls(
            id=run.id, period_year=run.period_year, period_month=run.period_month, status=run.status,
            hr_approved_by_id=run.hr_approved_by_id, hr_approved_at=run.hr_approved_at,
            finance_approved_by_id=run.finance_approved_by_id, finance_approved_at=run.finance_approved_at,
            paid_at=run.paid_at, payslip_count=len(run.payslips),
        )


class PayslipUpdate(BaseModel):
    """HR/Finance manual adjustments before approval -- TDS, overtime, bonus."""
    tds_amount: float | None = Field(default=None, ge=0)
    overtime_amount: float | None = Field(default=None, ge=0)
    bonus_amount: float | None = Field(default=None, ge=0)


class PayslipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    payroll_run_id: uuid.UUID
    employee_id: uuid.UUID
    basic: float
    hra: float
    other_allowances: float
    overtime_amount: float
    bonus_amount: float
    gross_salary: float
    days_in_period: int
    days_present: int
    days_on_leave: int
    days_lop: int
    pf_deduction: float
    esi_deduction: float
    pt_deduction: float
    tds_amount: float
    net_salary: float
    pdf_storage_key: str | None
