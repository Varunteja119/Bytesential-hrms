import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from app.database.models.leave import LeaveStatus, LeaveType


class LeaveApplyRequest(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str | None = None


class LeaveDecisionRequest(BaseModel):
    note: str | None = None


class LeaveRejectRequest(BaseModel):
    rejection_reason: str


class LeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    employee_id: uuid.UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_requested: int
    reason: str | None
    status: LeaveStatus
    decided_by_id: uuid.UUID | None
    decided_at: datetime | None
    decision_note: str | None


class LeaveBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_type: LeaveType
    year: int
    allocated_days: int
    used_days: int
    remaining_days: int

    @classmethod
    def from_orm_balance(cls, balance) -> "LeaveBalanceOut":
        return cls(leave_type=balance.leave_type, year=balance.year, allocated_days=balance.allocated_days,
                    used_days=balance.used_days, remaining_days=balance.allocated_days - balance.used_days)
