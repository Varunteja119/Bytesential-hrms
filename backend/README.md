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

**Known noise:** if you generate migrations against a local SQLite DB (as this project's
own migrations were developed against, absent a live Postgres in that environment),
autogenerate will falsely report every existing UUID column as `NUMERIC -> UUID`. This
is a SQLite-reflection artifact (SQLite has no native UUID type) — those `alter_column`
calls do nothing real and were manually stripped from this project's migration files.
If you generate migrations against your actual Postgres instance instead, you won't see
this at all — worth doing once Postgres is your default local dev DB.

## Known Issues

- **Google OAuth2 login is untested end-to-end.** The code (`app/api/v1/auth/oauth.py`)
  follows the standard Authlib pattern, but no one has run it against real Google Cloud
  Console credentials yet (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are blank in
  `.env.example`), and there's no automated test coverage for it.

- **Ollama LLM integration (`app/services/llm_client.py`) is untested against a live
  Ollama instance.** The HTTP contract follows Ollama's documented `/api/generate` and
  `/api/embeddings` endpoints, but was only verified with a fake client in tests. Before
  relying on it: `docker compose up ollama`, pull a model (`docker compose exec ollama
ollama pull qwen2.5:7b` and `... pull nomic-embed-text`), then run a real screening
  call and confirm the response shape matches what `parse_screening_response()` expects.

- **MinIO storage integration (`app/services/storage.py`) is untested against a live
  MinIO instance.** Standard boto3 S3-client usage, verified only with an in-memory fake
  in tests. Confirm `docker compose up minio` + a real resume upload works before
  depending on it.

- **Email/SMTP integration (`app/services/email_client.py`) is untested against a live
  SMTP server.** Standard `smtplib` usage, verified only with a fake client in tests
  (`FakeEmailClient` in `tests/conftest.py`) — content/recipient/timing are all tested,
  actual delivery is not. `docker compose up mailpit` gives you a local SMTP catcher
  with a web UI at `http://localhost:8025` to see exactly what gets sent without
  needing real mail credentials — confirm a password reset and an employee welcome
  email both arrive there before trusting this in anything real. This closes what was
  previously a complete gap (nothing sent email at all, only logged) — welcome emails
  (with temp password) and password reset emails are both wired in now.

- **ChromaDB vector store IS verified** (`app/services/vector_store.py`) — it runs
  in-process, so unlike the three above, this one has been tested end-to-end with real
  embeddings/queries, not just fakes. You may see `Failed to send telemetry event`
  warnings in logs from this ChromaDB version — cosmetic only, doesn't affect results.

**JWT auth, RBAC, DB schema/migrations, and the recruitment/employee/onboarding
pipelines are all tested and working.** Don't build frontend integration against
Google OAuth, live LLM scoring, live resume/document upload, or live email delivery
until the items above are verified and this note is updated.

## What's covered — Email/notifications

- Welcome email (employee code + temp password) sent on employee provisioning
- Password reset email (with working reset link) sent on reset request
- Both are best-effort: a down SMTP server logs an error but doesn't fail the
  underlying action (provisioning still succeeds, password reset still returns 202) —
  the temp password is also still returned in the API response as a fallback delivery
  path until email delivery is verified reliable
- 8 new tests: 2 pure template tests + 6 integration tests asserting actual email
  content/recipients via a fake SMTP client (previously: zero tests existed for
  password reset at all, in any phase)

## What's covered in Phase 2c — Onboarding

- **Fixed a real gap found in 2b's activation logic**: activation previously only
  checked for _unverified_ documents, which passed vacuously when an employee had
  uploaded _zero_ documents. Activation now requires three specific document types
  (Aadhaar, PAN, bank proof — `app/business/onboarding.py:REQUIRED_DOCUMENT_TYPES`)
  to be both present and verified.
- Forced password change: new hires get `must_change_password=True` on provisioning;
  `POST /auth/change-password` clears it. Activation is now also blocked until this
  happens — a temp password can no longer be the account's permanent password.
- Onboarding status/checklist endpoints (`GET /employees/me/onboarding-status` and
  `/employees/{id}/onboarding-status`) — shows exactly what's outstanding: password
  changed?, profile complete?, which required documents are uploaded/verified?,
  ready for activation?
- 7 new tests, all passing, specifically targeting the gap above and each activation
  precondition independently

## What's covered in Phase 2b — Employee Management

- Employee provisioning: converts an ACCEPTED candidate into a real User + Employee
  account, generating a sequential employee code and a one-time temp password (no
  email delivery yet — same known limitation as password reset, see below)
- Self-service profile completion (phone, address, DOB, bank details, Aadhaar/PAN) —
  separate from HR-only fields (department, designation, manager, status), enforced
  at the schema level so an employee literally cannot submit a department change
- Document upload (Aadhaar, PAN, certificates, bank proof) + HR verification workflow
- Activation gate: employment_status only flips to ACTIVE once profile is complete
  AND all uploaded documents are HR-verified — matches the SRS's documented
  "HR verifies and activates employee account" step
- 9 tests covering the full path: provision → temp-password login → profile
  completion → document upload → HR verification → activation, plus the RBAC
  boundary (an employee cannot view another employee's record)

## What's covered in Phase 2a — Recruitment

- Job postings + Candidates with a real state-machine pipeline (applied → screening →
  interview → hr_approval → offered → accepted/rejected/withdrawn) — illegal transitions
  are rejected, not just accepted and ignored
- Resume upload (PDF/DOCX) with text extraction, cached on the candidate record
- AI resume screening: builds a prompt from job requirements + resume text, calls the
  LLM, robustly parses its response (handles markdown-fenced JSON, preambles, etc.),
  stores score + summary, auto-advances the candidate's pipeline stage
- Candidate resume embeddings indexed in ChromaDB; "find similar candidates for this
  job" endpoint using real vector similarity search across the whole candidate pool
- All AI service integrations (LLM, storage, vector store) are behind abstract
  interfaces with dependency injection — swappable and independently testable

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
