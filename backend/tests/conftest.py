"""
Test fixtures.

Uses an in-memory SQLite DB per test (via a StaticPool so the single
connection is shared across the request thread), overriding the app's
`get_db` dependency. This keeps tests fast and fully isolated from
whatever Postgres instance is configured in .env — no real DB needed to
run the suite.
"""
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
def client(db_session):
    from app.core.rate_limit import limiter

    limiter.reset()  # all tests share one process -> one in-memory limiter; reset per test

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
