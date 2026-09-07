import enum
from datetime import date
from sqlalchemy import Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EmploymentStatus(str, enum.Enum):
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class DocumentType(str, enum.Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    EDUCATION_CERTIFICATE = "education_certificate"
    EXPERIENCE_CERTIFICATE = "experience_certificate"
    BANK_PROOF = "bank_proof"
    OTHER = "other"


class Employee(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("candidate_id", name="uq_employee_candidate"),)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    user = relationship("User", foreign_keys=[user_id])
    candidate_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    reporting_manager_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"))
    reporting_manager = relationship("Employee", remote_side="Employee.id")
    employment_status: Mapped[EmploymentStatus] = mapped_column(Enum(EmploymentStatus), default=EmploymentStatus.PENDING_ACTIVATION, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(30))
    aadhaar_number: Mapped[str | None] = mapped_column(String(20))
    pan_number: Mapped[str | None] = mapped_column(String(20))
    bank_account_number: Mapped[str | None] = mapped_column(String(30))
    bank_ifsc: Mapped[str | None] = mapped_column(String(20))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    profile_completed: Mapped[bool] = mapped_column(default=False)
    hr_verified: Mapped[bool] = mapped_column(default=False)
    hr_verified_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    documents: Mapped[list["EmployeeDocument"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class EmployeeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "employee_documents"
    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    employee: Mapped["Employee"] = relationship(back_populates="documents")
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(default=False)
    verified_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
