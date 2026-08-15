"""
Employee provisioning: turns an ACCEPTED candidate into a real User + Employee.

This is the pivot point in the SRS workflow: "Candidate Accepts Offer ->
Employee ID & Temporary Password Generated -> Employee Login". Kept as its
own business-logic function (not inline in the route) because it touches
three concerns at once — code generation, User creation, Employee creation
— and needs to be transactional: either all three happen or none do.
"""
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
    """
    Sequential EMP-000001 style code.

    NOTE: this counts existing rows, which has a race condition under
    concurrent provisioning (two simultaneous hires could collide on the
    same number). Acceptable for now given HR onboarding is a low-frequency,
    typically-one-at-a-time action; if that assumption stops holding, switch
    this to a DB sequence.
    """
    count = db.query(func.count(Employee.id)).scalar() or 0
    return f"EMP-{count + 1:06d}"


def generate_temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def provision_employee_from_candidate(
    db: Session,
    candidate: Candidate,
    department: str,
    designation: str,
    date_of_joining: date,
    email_client: EmailClient,
) -> tuple[Employee, str]:
    """
    Returns (employee, temp_password). Raises AppError if the candidate
    isn't in a hireable state or has already been provisioned.

    The temp password is emailed to the candidate (welcome_email template)
    AND still returned in the API response — the API response stays as a
    fallback in case email delivery fails (SMTP down, wrong address, etc.),
    since there's no retry/dead-letter mechanism for failed sends yet.
    Once email delivery is verified reliable in production, consider
    dropping the temp password from the API response for better security
    posture (right now it's technically visible to whoever calls this
    endpoint, not just the new hire).
    """
    if candidate.status != CandidateStatus.ACCEPTED:
        raise AppError(
            f"Candidate must be in 'accepted' status to provision as an employee (currently '{candidate.status.value}')."
        )

    existing = db.query(Employee).filter(Employee.candidate_id == candidate.id).first()
    if existing is not None:
        raise AppError(f"Candidate has already been provisioned as employee {existing.employee_code}.")

    if db.query(User).filter(User.email == candidate.email).first() is not None:
        raise AppError(f"A user account already exists for {candidate.email}.")

    employee_role = db.query(Role).filter(Role.name == _EMPLOYEE_ROLE_NAME).first()
    if employee_role is None:
        raise AppError(f"Default '{_EMPLOYEE_ROLE_NAME}' role not found — run the seed script first.", status_code=500)

    temp_password = generate_temp_password()
    user = User(
        email=candidate.email,
        hashed_password=hash_password(temp_password),
        full_name=candidate.full_name,
        roles=[employee_role],
        must_change_password=True,  # forces a real password before onboarding can complete
    )
    db.add(user)
    db.flush()  # populate user.id without committing yet — provisioning is one atomic transaction

    employee = Employee(
        employee_code=generate_employee_code(db),
        user_id=user.id,
        candidate_id=candidate.id,
        department=department,
        designation=designation,
        date_of_joining=date_of_joining,
        phone=candidate.phone,
        employment_status=EmploymentStatus.PENDING_ACTIVATION,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    subject, body = welcome_email(candidate.full_name, employee.employee_code, temp_password, f"{settings.frontend_url}/login")
    try:
        email_client.send(candidate.email, subject, body)
    except Exception:
        # Don't let a down SMTP server fail the whole provisioning transaction —
        # the employee record is already committed; HR can relay the temp
        # password manually (it's still in this function's return value).
        logger.error("Welcome email failed to send to %s — temp password must be relayed manually.", candidate.email)

    return employee, temp_password
