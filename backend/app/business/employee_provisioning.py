import logging
import secrets
import string
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AppError
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.rbac import Role
from app.database.models.recruitment import Candidate, CandidateStatus
from app.database.models.user import User
from app.security.password import hash_password
from app.services.email_client import EmailClient
from app.services.email_templates import welcome_email

logger = logging.getLogger("bytesentinel.employee_provisioning")
_EMPLOYEE_ROLE_NAME = "employee"


def generate_employee_code(db: Session) -> str:
    count = db.query(func.count(Employee.id)).scalar() or 0
    return f"EMP-{count + 1:06d}"


def generate_temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def provision_employee_from_candidate(db: Session, candidate: Candidate, department: str, designation: str, date_of_joining: date, email_client: EmailClient):
    if candidate.status != CandidateStatus.ACCEPTED:
        raise AppError(f"Candidate must be in 'accepted' status to provision as an employee (currently '{candidate.status.value}').")

    existing = db.query(Employee).filter(Employee.candidate_id == candidate.id).first()
    if existing is not None:
        raise AppError(f"Candidate has already been provisioned as employee {existing.employee_code}.")

    if db.query(User).filter(User.email == candidate.email).first() is not None:
        raise AppError(f"A user account already exists for {candidate.email}.")

    employee_role = db.query(Role).filter(Role.name == _EMPLOYEE_ROLE_NAME).first()
    if employee_role is None:
        raise AppError(f"Default '{_EMPLOYEE_ROLE_NAME}' role not found — run the seed script first.", status_code=500)

    temp_password = generate_temp_password()
    user = User(email=candidate.email, hashed_password=hash_password(temp_password), full_name=candidate.full_name,
                roles=[employee_role], must_change_password=True)
    db.add(user)
    db.flush()

    employee = Employee(employee_code=generate_employee_code(db), user_id=user.id, candidate_id=candidate.id,
                         department=department, designation=designation, date_of_joining=date_of_joining,
                         phone=candidate.phone, employment_status=EmploymentStatus.PENDING_ACTIVATION)
    db.add(employee)
    db.commit()
    db.refresh(employee)

    subject, body = welcome_email(candidate.full_name, employee.employee_code, temp_password, f"{settings.frontend_url}/login")
    try:
        email_client.send(candidate.email, subject, body)
    except Exception:
        logger.error("Welcome email failed to send to %s — temp password must be relayed manually.", candidate.email)

    return employee, temp_password
