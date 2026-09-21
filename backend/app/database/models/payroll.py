import enum
from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "draft"
    HR_APPROVED = "hr_approved"
    FINANCE_APPROVED = "finance_approved"
    PAID = "paid"


class PayrollConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payroll_config"
    pf_rate_percent: Mapped[float] = mapped_column(Float, nullable=False)
    pf_wage_ceiling: Mapped[float] = mapped_column(Float, nullable=False)
    esi_rate_percent: Mapped[float] = mapped_column(Float, nullable=False)
    esi_wage_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    pt_state: Mapped[str] = mapped_column(String(100), nullable=False)
    pt_amount: Mapped[float] = mapped_column(Float, nullable=False)
    overtime_rate_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.5)
    updated_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class SalaryStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "salary_structures"
    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    basic: Mapped[float] = mapped_column(Float, nullable=False)
    hra: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    other_allowances: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    effective_from: Mapped[date_type] = mapped_column(Date, nullable=False)


class PayrollRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("period_year", "period_month", name="uq_payroll_run_period"),)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PayrollRunStatus] = mapped_column(Enum(PayrollRunStatus), default=PayrollRunStatus.DRAFT, nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hr_approved_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    hr_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finance_approved_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    finance_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payslips: Mapped[list["Payslip"]] = relationship(back_populates="payroll_run", cascade="all, delete-orphan")


class Payslip(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("payroll_run_id", "employee_id", name="uq_payslip_run_employee"),)
    payroll_run_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    payroll_run: Mapped["PayrollRun"] = relationship(back_populates="payslips")
    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    basic: Mapped[float] = mapped_column(Float, nullable=False)
    hra: Mapped[float] = mapped_column(Float, nullable=False)
    other_allowances: Mapped[float] = mapped_column(Float, nullable=False)
    overtime_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bonus_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gross_salary: Mapped[float] = mapped_column(Float, nullable=False)

    days_in_period: Mapped[int] = mapped_column(Integer, nullable=False)
    days_present: Mapped[int] = mapped_column(Integer, nullable=False)
    days_on_leave: Mapped[int] = mapped_column(Integer, nullable=False)
    days_lop: Mapped[int] = mapped_column(Integer, nullable=False)

    pf_deduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    esi_deduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pt_deduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tds_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    net_salary: Mapped[float] = mapped_column(Float, nullable=False)
    pdf_storage_key: Mapped[str | None] = mapped_column(String(500))
