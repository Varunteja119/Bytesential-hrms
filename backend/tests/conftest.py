import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database.models  # noqa: F401 -- registers all models before Base.metadata.create_all()
from app.database.connection.database import Base, get_db
from app.main import app  # must be imported last: this binds `app` to the FastAPI instance
from app.services.email_client import get_email_client


class FakeEmailClient:
    """Captures sent emails in memory instead of hitting real SMTP."""

    def __init__(self):
        self.sent: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def fake_email_client():
    return FakeEmailClient()


@pytest.fixture()
def client(db_session, fake_email_client):
    from app.core.rate_limit import limiter

    limiter.reset()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_client] = lambda: fake_email_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
