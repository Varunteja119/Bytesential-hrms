import uuid
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from app.database.models.analytics import ExitType


class ExitCreate(BaseModel):
    employee_id: uuid.UUID
    exit_type: ExitType
    exit_date: date
    notice_period_days: int | None = None
    reason: str | None = None
    exit_interview_notes: str | None = None


class ExitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    employee_id: uuid.UUID
    exit_type: ExitType
    exit_date: date
    notice_period_days: int | None
    reason: str | None
    exit_interview_notes: str | None


class HeadcountItem(BaseModel):
    department: str
    headcount: int


class AttendanceSummary(BaseModel):
    total_records: int
    late_count: int
    late_rate_percent: float


class LeaveUtilizationItem(BaseModel):
    leave_type: str
    total_days_taken: int


class PayrollCostItem(BaseModel):
    month: int
    total_net_salary: float


class AttritionSignals(BaseModel):
    tenure_days: int
    late_arrivals_last_90_days: int
    leave_days_last_90_days: int
    latest_manager_rating: int | None
    latest_ai_recommendation: str | None


class AttritionRiskOut(BaseModel):
    employee_id: uuid.UUID
    risk_level: str
    reasoning: str
    signals: AttritionSignals
    disclaimer: str
