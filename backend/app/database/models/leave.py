import enum
from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LeaveType(str, enum.Enum):
    CASUAL = "casual"
    SICK = "sick"
    EARNED = "earned"
    UNPAID = "unpaid"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveBalance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "leave_balances"
    __table_args__ = (UniqueConstraint("employee_id", "leave_type", "year", name="uq_leave_balance_employee_type_year"),)
    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_days: Mapped[int] = mapped_column(Integer, nullable=False)
    used_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class LeaveRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "leave_requests"
    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    employee = relationship("Employee", foreign_keys=[employee_id])
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    start_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    end_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    days_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    decided_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
