"""
Employee exit tracking -- the data foundation analytics/attrition work
needs. Kept as its own table (not fields bolted onto Employee) so a full
exit record persists even though the Employee row itself never gets
deleted, and so multiple people (HR conducting the exit interview, the
approving manager) can be recorded distinctly.
"""
import enum
from datetime import date as date_type

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ExitType(str, enum.Enum):
    RESIGNATION = "resignation"
    TERMINATION = "termination"
    RETIREMENT = "retirement"
    END_OF_CONTRACT = "end_of_contract"


class EmployeeExit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "employee_exits"

    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), unique=True, nullable=False)
    exit_type: Mapped[ExitType] = mapped_column(Enum(ExitType), nullable=False)
    exit_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)  # free-text reason, e.g. from exit interview
    exit_interview_notes: Mapped[str | None] = mapped_column(Text)
    recorded_by_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
