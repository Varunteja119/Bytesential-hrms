# ByteSentinel Backend — Phase 1

Foundation: authentication (JWT + Google OAuth2), RBAC, database schema, API architecture.

## Local dev (without Docker)

```bash
cp .env.example .env               # fill in SECRET_KEY (openssl rand -hex 32) and a real Postgres DATABASE_URL
pip install -r requirements.txt --break-system-packages
alembic upgrade head               # apply schema
python -m scripts.seed.seed_rbac   # create default roles/permissions + a superuser
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/api/docs

Default seeded superuser: `admin@bytesentinel.com` / `ChangeMe123!`
(override via `SEED_SUPERUSER_EMAIL` / `SEED_SUPERUSER_PASSWORD` env vars — change the password immediately in any shared environment).

## Local dev (with Docker)

```bash
docker compose up -d postgres redis
docker compose run --rm migrate     # applies migrations + seeds RBAC data
docker compose up backend
```

> Note: the docker-compose config here is written to the standard spec but hasn't been
> build-tested against a live Docker daemon in this environment — sanity-check `docker
compose up` locally before relying on it.

## Tests

```bash
python -m pytest tests/ -v
```

Tests run against an isolated in-memory SQLite DB (see `tests/conftest.py`) — no real
Postgres needed to run the suite.

## Adding a new migration

After changing/adding a model in `app/database/models/`:

```bash
alembic revision --autogenerate -m "add employee table"
alembic upgrade head
```

Always read the generated migration before applying it — autogenerate is good but not
perfect (e.g. it won't detect a column rename, only a drop+add).

## What's covered in Phase 1

- JWT access/refresh tokens + Google OAuth2 login
- RBAC (Role/Permission, `require_permission()` route guard)
- Password reset flow (reset-token email delivery is stubbed — logged, not sent — until
  the notifications service exists in a later phase)
- Rate limiting on login (5/min) and password-reset requests (3/min)
- Global exception handling (consistent JSON error shape, no raw tracebacks leaked)
- Request logging middleware (method/path/status/duration/request-id per request)
- Alembic migrations
- Seed script for default roles/permissions/superuser
- Test suite (pytest) covering auth + RBAC
- Dockerfile + docker-compose for local dev

## Phase 1: JWT auth, RBAC, DB schema, migrations, tests, Docker setup

- Register/login/refresh/me endpoints with access+refresh JWTs
- RBAC: Role/Permission models, require_permission() route guard
- Alembic migrations + seed script for default roles/permissions
- Password reset flow (email delivery stubbed, pending notifications service)
- Rate limiting, structured error handling, request logging
- pytest suite covering auth + RBAC (12 tests passing)
- Dockerfile + docker-compose for local dev

Known issue: Google OAuth2 is implemented but untested end-to-end —
no real Google credentials configured, no test coverage yet."
