import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.business.employee_provisioning import provision_employee_from_candidate
from app.business.onboarding import compute_onboarding_status, validate_can_activate
from app.core.dependencies import get_current_user, require_permission
from app.core.exceptions import AppError
from app.database.connection.database import get_db
from app.database.models.employee import DocumentType, Employee, EmployeeDocument, EmploymentStatus
from app.database.models.recruitment import Candidate
from app.database.models.user import User
from app.database.schemas.employee import (
    EmployeeAdminUpdate,
    EmployeeDocumentOut,
    EmployeeOut,
    EmployeeProfileUpdate,
    ProvisionEmployeeRequest,
    ProvisionEmployeeResponse,
)
from app.services.storage import StorageClient, get_storage_client
from app.services.email_client import EmailClient, get_email_client

router = APIRouter(prefix="/employees", tags=["employees"])


def _get_employee_or_404(db: Session, employee_id: uuid.UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


def _get_own_employee_record(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record linked to your account")
    return employee


def _require_self_or_permission(employee: Employee, user: User, permission_code: str) -> None:
    """Lets an employee act on their own record, OR someone with the given
    permission act on any record (e.g. HR uploading a document on a new
    hire's behalf). Used anywhere self-service and HR-assisted overlap."""
    if employee.user_id == user.id:
        return
    if user.is_superuser or user.has_permission(permission_code):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only access your own employee record")


# --- Provisioning ---

@router.post(
    "/provision",
    response_model=ProvisionEmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("employee:write"))],
)
def provision_employee(
    payload: ProvisionEmployeeRequest,
    db: Session = Depends(get_db),
    email_client: EmailClient = Depends(get_email_client),
):
    candidate = db.get(Candidate, payload.candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")

    employee, temp_password = provision_employee_from_candidate(
        db, candidate, payload.department, payload.designation, payload.date_of_joining, email_client
    )  # raises AppError (400) if candidate isn't accepted / already provisioned / email collision
    return ProvisionEmployeeResponse(employee=EmployeeOut.model_validate(employee), temp_password=temp_password)


# --- Listing / lookup ---

@router.get("", response_model=list[EmployeeOut], dependencies=[Depends(require_permission("employee:read"))])
def list_employees(db: Session = Depends(get_db)):
    return [EmployeeOut.model_validate(e) for e in db.query(Employee).all()]


@router.get("/me", response_model=EmployeeOut)
def get_my_employee_record(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return EmployeeOut.model_validate(_get_own_employee_record(db, current_user))


@router.get("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(require_permission("employee:read"))])
def get_employee(employee_id: uuid.UUID, db: Session = Depends(get_db)):
    return EmployeeOut.model_validate(_get_employee_or_404(db, employee_id))


# --- Profile updates ---

@router.patch("/me", response_model=EmployeeOut)
def update_my_profile(
    payload: EmployeeProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Self-service profile completion — per SRS onboarding step 'Profile Completion'."""
    employee = _get_own_employee_record(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)

    # Consider the profile "complete" once the core onboarding fields are all filled in.
    required = [employee.phone, employee.address, employee.date_of_birth, employee.bank_account_number]
    employee.profile_completed = all(f is not None for f in required)

    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_permission("employee:write"))],
)
def update_employee_admin(employee_id: uuid.UUID, payload: EmployeeAdminUpdate, db: Session = Depends(get_db)):
    """HR-only fields: department, designation, reporting manager, employment status."""
    employee = _get_employee_or_404(db, employee_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)


# --- Documents ---

@router.post("/{employee_id}/documents", response_model=EmployeeDocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    employee_id: uuid.UUID,
    document_type: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageClient = Depends(get_storage_client),
):
    employee = _get_employee_or_404(db, employee_id)
    _require_self_or_permission(employee, current_user, "employee:write")

    try:
        from app.database.models.employee import DocumentType

        doc_type = DocumentType(document_type)
    except ValueError:
        raise AppError(f"Invalid document_type. Must be one of: {', '.join(t.value for t in DocumentType)}")

    content = file.file.read()
    storage_key = f"employee-documents/{employee_id}/{doc_type.value}/{file.filename}"
    storage.upload(storage_key, content, file.content_type or "application/octet-stream")

    document = EmployeeDocument(
        employee_id=employee_id,
        document_type=doc_type,
        storage_key=storage_key,
        original_filename=file.filename,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return EmployeeDocumentOut.model_validate(document)


@router.get("/{employee_id}/documents", response_model=list[EmployeeDocumentOut])
def list_documents(employee_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_employee_or_404(db, employee_id)
    _require_self_or_permission(employee, current_user, "employee:read")
    return [EmployeeDocumentOut.model_validate(d) for d in employee.documents]


@router.patch(
    "/{employee_id}/documents/{document_id}/verify",
    response_model=EmployeeDocumentOut,
    dependencies=[Depends(require_permission("employee:write"))],
)
def verify_document(
    employee_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    document = db.get(EmployeeDocument, document_id)
    if document is None or document.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    document.verified = True
    document.verified_by_id = current_user.id
    db.commit()
    db.refresh(document)
    return EmployeeDocumentOut.model_validate(document)


# --- Onboarding status ---

@router.get("/me/onboarding-status")
def get_my_onboarding_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    return compute_onboarding_status(employee)


@router.get("/{employee_id}/onboarding-status")
def get_onboarding_status(employee_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_employee_or_404(db, employee_id)
    _require_self_or_permission(employee, current_user, "employee:read")
    return compute_onboarding_status(employee)


# --- Activation ---

@router.post(
    "/{employee_id}/activate",
    response_model=EmployeeOut,
    dependencies=[Depends(require_permission("employee:write"))],
)
def activate_employee(employee_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Per SRS: 'HR verifies and activates employee account' — the final onboarding step."""
    employee = _get_employee_or_404(db, employee_id)

    validate_can_activate(employee)  # raises AppError (400) with the specific missing piece

    employee.hr_verified = True
    employee.hr_verified_by_id = current_user.id
    employee.employment_status = EmploymentStatus.ACTIVE
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)
