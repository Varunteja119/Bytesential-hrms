"""
Attendance schema.

Design: one Attendance row per (employee, date) — enforced by a unique
constraint — rather than a raw event log of check-in/check-out timestamps.
This matches how attendance is actually consumed downstream (Leave and
Payroll, per SRS section 7's workflow chain, need "was this employee
present on this date" and "how many hours did they work", not a stream
of punch events). If a genuine multi-shift/multiple-punches-per-day
requirement shows up later, this would need revisiting — noted here
rather than over-built now.
"""
import enum
from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"     # set by the Leave module once it exists, not by check-in/out
    HOLIDAY = "holiday"       # set by HR for company holidays
    WEEKEND = "weekend"       # reserved for a future auto-marking job, not set anywhere yet


class Attendance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),)

    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    employee = relationship("Employee")

    date: Mapped[date_type] = mapped_column(Date, nullable=False)

    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    work_hours: Mapped[float | None] = mapped_column(Float)  # computed on check-out
    is_late: Mapped[bool] = mapped_column(default=False)

    notes: Mapped[str | None] = mapped_column(Text)  # HR remarks on manual corrections
