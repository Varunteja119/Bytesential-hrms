import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.database.models.attendance import AttendanceStatus


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: AttendanceStatus
    work_hours: float | None
    is_late: bool
    notes: str | None


class AttendanceMarkRequest(BaseModel):
    """HR manual entry/correction — e.g. marking a holiday or a no-show absent."""

    date: date
    status: AttendanceStatus
    notes: str | None = None
