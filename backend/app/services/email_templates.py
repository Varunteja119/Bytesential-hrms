from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "emails"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)


def welcome_email(full_name: str, employee_code: str, temp_password: str, login_url: str) -> tuple[str, str]:
    subject = "Welcome to ByteSentinel — Your Account is Ready"
    template = _env.get_template("welcome_email.txt")
    body = template.render(full_name=full_name, employee_code=employee_code, temp_password=temp_password, login_url=login_url)
    return subject, body


def password_reset_email(reset_token: str, reset_url: str) -> tuple[str, str]:
    subject = "Reset Your ByteSentinel Password"
    template = _env.get_template("password_reset_email.txt")
    body = template.render(reset_token=reset_token, reset_url=reset_url)
    return subject, body
