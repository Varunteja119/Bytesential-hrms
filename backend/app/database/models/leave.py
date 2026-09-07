"""
Leave schema.

Design: LeaveBalance is a separate table from LeaveRequest (not computed
on the fly from a sum of approved requests) so a balance can be queried
cheaply and adjusted independently (e.g. a manual HR correction) without
recomputing across every historical request. Balances are per (employee,
leave_type, year) — allocations reset annually.

⚠️ ASSUMPTIONS (SRS doesn't specify exact policy numbers): annual
allocations below (LEAVE_ALLOCATIONS in business/leave.py), and day
counting treats every calendar day in the range as a leave day (no
weekend/holiday exclusion — company work-week policy isn't defined in
the SRS). Adjust once actual HR policy is confirmed.
"""
import enum
from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LeaveType(str, enum.Enum):
    CASUAL = "casual"
    SICK = "sick"
    EARNED = "earned"
    UNPAID = "unpaid"  # no balance cap — doesn't deduct from LeaveBalance


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
    decision_note: Mapped[str | None] = mapped_column(Text)  # rejection reason, or approval note
