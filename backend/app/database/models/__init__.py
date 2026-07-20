"""
Import every model here so Base.metadata knows about all tables before
Alembic autogenerate or create_all() runs. This is the single place that
grows as you add employee.py, leave.py, payroll.py, etc. in later phases.
"""
from app.database.models.user import User  # noqa: F401
from app.database.models.rbac import Role, Permission  # noqa: F401
