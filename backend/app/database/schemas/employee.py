import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.database.models.employee import DocumentType, EmploymentStatus


class ProvisionEmployeeRequest(BaseModel):
    candidate_id: uuid.UUID
    department: str = Field(min_length=1, max_length=100)
    designation: str = Field(min_length=1, max_length=100)
    date_of_joining: date


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    user_id: uuid.UUID
    candidate_id: uuid.UUID | None
    department: str
    designation: str
    date_of_joining: date
    reporting_manager_id: uuid.UUID | None
    employment_status: EmploymentStatus

    phone: str | None
    address: str | None
    date_of_birth: date | None
    gender: str | None
    aadhaar_number: str | None
    pan_number: str | None
    bank_account_number: str | None
    bank_ifsc: str | None
    bank_name: str | None

    profile_completed: bool
    hr_verified: bool


class ProvisionEmployeeResponse(BaseModel):
    employee: EmployeeOut
    temp_password: str


class EmployeeProfileUpdate(BaseModel):
    """Self-service fields — what the employee themself can fill in during onboarding.
    Deliberately excludes department/designation/status/manager — those are HR-only."""

    phone: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    aadhaar_number: str | None = None
    pan_number: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_name: str | None = None


class EmployeeAdminUpdate(BaseModel):
    """HR-only fields."""

    department: str | None = None
    designation: str | None = None
    reporting_manager_id: uuid.UUID | None = None
    employment_status: EmploymentStatus | None = None


class EmployeeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    document_type: DocumentType
    original_filename: str
    verified: bool
