"""
Centralized app configuration.

Why pydantic-settings instead of plain os.environ:
- Type validation happens at startup (fail fast, not at request time).
- One object (`settings`) is imported everywhere instead of scattered
  os.getenv() calls, which makes it obvious what config the app depends on.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "ByteSentinel AI ERP"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OAuth2 (Google) — optional in dev
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    # lru_cache => .env is parsed once per process, not on every import/request
    return Settings()


settings = get_settings()
