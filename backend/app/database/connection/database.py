"""
SQLAlchemy engine + session factory.

Design choice: sync SQLAlchemy (not async) for Phase 1.
Reasoning: your AI services (LangGraph, Ollama calls) are already I/O heavy
and will run through Celery workers, not the request thread. Keeping the
CRUD layer sync keeps debugging simple early on; you can migrate to
`asyncpg` + `AsyncSession` later without changing the API contracts.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config.settings import settings

_engine_kwargs = {"pool_pre_ping": True}  # avoids "server closed the connection unexpectedly" after idle
if not settings.database_url.startswith("sqlite"):
    # SQLite's default pool (SingletonThreadPool) doesn't accept these — only relevant for
    # real connection-pooled backends like Postgres. Tests run on SQLite, so this keeps
    # the exact same `database.py` working in both prod and the test suite.
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base — every model in database/models/ inherits this."""
    pass


def get_db() -> Generator:
    """FastAPI dependency: one DB session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
