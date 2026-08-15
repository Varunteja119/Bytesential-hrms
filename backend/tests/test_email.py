from app.services.email_templates import password_reset_email, welcome_email


def test_welcome_email_contains_credentials():
    subject, body = welcome_email("Jane Doe", "EMP-000001", "TempPass123", "http://localhost:3000/login")
    assert "Jane Doe" in body
    assert "EMP-000001" in body
    assert "TempPass123" in body
    assert "http://localhost:3000/login" in body
    assert "Welcome" in subject


def test_password_reset_email_contains_token_link():
    subject, body = password_reset_email("abc123token", "http://localhost:3000/reset-password")
    assert "http://localhost:3000/reset-password?token=abc123token" in body
    assert "expires in 15 minutes" in body
    assert "Reset" in subject
