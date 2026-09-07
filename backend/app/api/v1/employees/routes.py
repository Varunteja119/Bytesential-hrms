import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.employees.access import get_employee_or_404, get_own_employee_record
from app.business.employee_provisioning import provision_employee_from_candidate
from app.business.onboarding import validate_can_activate
from app.dependencies.auth import get_current_user, require_permission
from app.database.connection.database import get_db
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.recruitment import Candidate
from app.database.models.user import User
from app.database.schemas.employee import (
    EmployeeAdminUpdate,
    EmployeeOut,
    EmployeeProfileUpdate,
    ProvisionEmployeeRequest,
    ProvisionEmployeeResponse,
)
from app.services.email_client import EmailClient, get_email_client

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("/provision", response_model=ProvisionEmployeeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("employee:write"))])
def provision_employee(payload: ProvisionEmployeeRequest, db: Session = Depends(get_db), email_client: EmailClient = Depends(get_email_client)):
    candidate = db.get(Candidate, payload.candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    employee, temp_password = provision_employee_from_candidate(db, candidate, payload.department, payload.designation, payload.date_of_joining, email_client)
    return ProvisionEmployeeResponse(employee=EmployeeOut.model_validate(employee), temp_password=temp_password)


@router.get("", response_model=list[EmployeeOut], dependencies=[Depends(require_permission("employee:read"))])
def list_employees(db: Session = Depends(get_db)):
    return [EmployeeOut.model_validate(e) for e in db.query(Employee).all()]


@router.get("/me", response_model=EmployeeOut)
def get_my_employee_record(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return EmployeeOut.model_validate(get_own_employee_record(db, current_user))


@router.get("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(require_permission("employee:read"))])
def get_employee(employee_id: uuid.UUID, db: Session = Depends(get_db)):
    return EmployeeOut.model_validate(get_employee_or_404(db, employee_id))


@router.patch("/me", response_model=EmployeeOut)
def update_my_profile(payload: EmployeeProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = get_own_employee_record(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    required = [employee.phone, employee.address, employee.date_of_birth, employee.bank_account_number]
    employee.profile_completed = all(f is not None for f in required)
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(require_permission("employee:write"))])
def update_employee_admin(employee_id: uuid.UUID, payload: EmployeeAdminUpdate, db: Session = Depends(get_db)):
    employee = get_employee_or_404(db, employee_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)


@router.post("/{employee_id}/activate", response_model=EmployeeOut, dependencies=[Depends(require_permission("employee:write"))])
def activate_employee(employee_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = get_employee_or_404(db, employee_id)
    validate_can_activate(employee)
    employee.hr_verified = True
    employee.hr_verified_by_id = current_user.id
    employee.employment_status = EmploymentStatus.ACTIVE
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)
