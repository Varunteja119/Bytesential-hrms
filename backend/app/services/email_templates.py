"""
Email content templates.

Plain Python functions rather than Jinja/templates-on-disk — there are
only two emails right now and neither needs conditional logic or partials.
If the template count grows past a handful, revisit and move these into
app/templates/emails/ as real files per the architecture doc's layout.
"""


def welcome_email(full_name: str, employee_code: str, temp_password: str, login_url: str) -> tuple[str, str]:
    """Returns (subject, body). Sent on employee provisioning."""
    subject = "Welcome to ByteSentinel — Your Account is Ready"
    body = f"""Hi {full_name},

Welcome aboard! Your employee account has been created.

  Employee ID: {employee_code}
  Temporary Password: {temp_password}

Please log in at {login_url} and change your password before continuing —
you won't be able to complete onboarding until you do.

If you have any questions, reach out to HR.

— ByteSentinel HR
"""
    return subject, body


def password_reset_email(reset_token: str, reset_url: str) -> tuple[str, str]:
    """Returns (subject, body). Sent on password reset request."""
    subject = "Reset Your ByteSentinel Password"
    body = f"""Hi,

We received a request to reset your ByteSentinel password.

Reset your password here: {reset_url}?token={reset_token}

This link expires in 15 minutes. If you didn't request this, you can
safely ignore this email — your password won't be changed.

— ByteSentinel HR
"""
    return subject, body
