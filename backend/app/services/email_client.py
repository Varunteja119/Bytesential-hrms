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
            logger.error("Failed to send email to %s (subject=%r): %s", to, subject, exc)
            raise


def get_email_client() -> EmailClient:
    return SMTPEmailClient(host=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_username,
                            password=settings.smtp_password, from_email=settings.smtp_from_email, use_tls=settings.smtp_use_tls)
