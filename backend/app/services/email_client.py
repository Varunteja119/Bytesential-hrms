"""
Email client abstraction (SMTP).

Same reasoning as llm_client.py and storage.py: an interface so anything
that sends email is testable without a real SMTP server, and so swapping
SMTP for a transactional email API (SendGrid, SES) later is a one-file
change.

⚠️ SMTPEmailClient is UNTESTED against a live SMTP server in this
environment (no mail server available here). Standard smtplib usage —
verify with a real SMTP server (or a local dev catcher like MailHog/
Mailpit) before relying on it. See README Known Issues.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Protocol

from app.config.settings import settings

logger = logging.getLogger("bytesentinel.email")


class EmailClient(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SMTPEmailClient:
    def __init__(self, host: str, port: int, username: str | None, password: str | None, from_email: str, use_tls: bool):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    def send(self, to: str, subject: str, body: str) -> None:
        message = MIMEText(body, "plain")
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            # Logs loudly, then re-raises the raw exception (not AppError) so the
            # caller decides what to do. Some callers (password reset) should
            # swallow this and keep responding 202 regardless of email health;
            # others (employee provisioning) may want to surface it to HR. That
            # decision belongs at the call site, not baked in here.
            logger.error("Failed to send email to %s (subject=%r): %s", to, subject, exc)
            raise


def get_email_client() -> EmailClient:
    """FastAPI dependency — override with a fake in tests."""
    return SMTPEmailClient(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        use_tls=settings.smtp_use_tls,
    )
