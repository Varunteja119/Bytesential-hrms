# ByteSentinel Backend — Phase 1 + Phase 2 + Phase 3

## Local dev (without Docker)

```bash
cp .env.example .env
pip install -r requirements.txt --break-system-packages
alembic upgrade head
python -m app.database.seed.seed_rbac
python -m app.database.seed.seed_payroll_config
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/api/docs
Default seeded superuser: `admin@bytesentinel.com` / `ChangeMe123!`

## Local dev (with Docker)

```bash
docker compose up -d postgres redis minio ollama mailpit pgadmin
docker compose exec ollama ollama pull qwen2.5:7b
docker compose exec ollama ollama pull nomic-embed-text
docker compose run --rm migrate
docker compose up backend
```

The `migrate` service runs both seed scripts automatically. To also run the
Celery worker (not required for anything synchronous today — see Known
Issues): `docker compose up celery_worker`.

## Tests

```bash
python -m pytest tests/ -v
```


87 tests, all passing, no live external services required (Ollama/MinIO/SMTP/Celery are all faked or called directly in tests).

## Known Issues

- **Google OAuth2** — implemented, untested against real credentials.
- **Ollama LLM client** — implemented, untested against a live Ollama instance.
- **MinIO storage client** — implemented, untested against a live MinIO instance.
- **Email/SMTP** — implemented and tested with a fake client; untested against real SMTP. `docker compose up mailpit` gives a local catcher at http://localhost:8025.
- **Celery worker** — implemented (`app/workers/celery_app.py`, `app/tasks/payroll_tasks.py`), the task logic is tested directly as a function call, but never run through a live broker/worker in this environment. Not currently wired into any API route (routes call the business logic synchronously) — the task exists as the documented next step once payroll's employee count needs async processing.
- **ChromaDB vector store** — verified end-to-end, runs in-process.
- **Payroll statutory rates (PF/ESI/PT) are PLACEHOLDER values**, stored as data in `PayrollConfig` (not hardcoded), specifically so they're updatable via `PATCH /payroll/config` without a code change once real numbers are confirmed with HR/Finance/legal. **Do not run real payroll against the seeded defaults.** TDS is never auto-calculated — it's a manually-entered amount per payslip.

## Project structure note

This backend was restructured partway through Phase 3 to match a structure
mandated by the team lead (see the ByteSentinel repo tree). Completed:
`core/` split into `middleware/`, `dependencies/`, `logging/`; `migrations/`
and `seed/` moved under `app/database/`; email templates moved to real files
under `app/templates/emails/`; `onboarding/` and `documents/` split into their
own `api/v1/` modules (URLs deliberately unchanged — see below); `workers/`,
`tasks/`, `scheduler/` added with a real Celery task for payroll.
**Not done:** a `database/repositories/` layer (routes/business logic still
query SQLAlchemy directly), dedicated `api/v1/roles/` and `api/v1/permissions/`
CRUD endpoints (roles/permissions are seed-managed only).

**Important:** `onboarding/` and `documents/` route handlers live in their own
files per the mandated structure, but are still mounted at the original
`/employees/...` URL prefix — this was deliberate, since the frontend team was
already integrating against those exact paths when the restructuring happened.
Changing the file a handler lives in did not change any URL, request shape,
or response shape anywhere in this restructuring.

## What's covered

**Phase 3c — Payroll:** Two-step approval workflow (HR → Finance, matching the
SRS's documented chain), attendance-driven proration (unmarked days = Loss of
Pay, deducted from gross before net salary), salary structure with revision
history (`SalaryStructure` rows keyed by `effective_from`, not one row per
employee). `PayrollConfig` holds PF/ESI/PT rates as **editable data**, not
hardcoded constants — see Known Issues above for why, and don't run real
payroll against the seeded placeholder values. TDS/overtime/bonus are
manually adjustable per payslip before HR approval locks it. A `finance_manager`
role was added (`payroll:approve_finance`) distinct from `hr_manager`
(`payroll:approve_hr`), since the SRS treats these as separate approval steps.
13 tests, including the full approval chain, an RBAC boundary test (HR cannot
finance-approve even holding `payroll:approve_hr`), and an LOP proration
scenario verified against hand-calculated expected values before being wired
into the API at all.

**Phase 3b — Leave:** Apply/approve/reject/cancel workflow with real balance
tracking per (employee, leave_type, year). ⚠️ ASSUMPTIONS (SRS doesn't specify
exact policy): annual allocations are casual=12, sick=12, earned=15, unpaid=uncapped
(`LEAVE_ALLOCATIONS` in `app/business/leave.py`); day counting is calendar days
inclusive, no weekend/holiday exclusion. **Approving a leave request writes
`ON_LEAVE` records into the Attendance table for every day in the range** — this
is the actual "Attendance → Leave" connection the SRS workflow diagram shows, not
two disconnected modules that merely share an employee_id. Overlapping leave
requests are rejected. 13 tests, including one that verifies the Attendance
write-back actually happens with the correct dates and status.

**Phase 3a — Attendance:** Self-service check-in/check-out with real business rules
(can't check in twice, can't check out without checking in first), late-arrival
detection and half-day marking based on configurable thresholds (`work_start_hour`,
`late_grace_minutes`, `half_day_hours_threshold` in settings — SRS doesn't specify
exact company policy numbers, these are sensible defaults meant to be adjusted).
HR can view any employee's attendance and manually mark/correct records (holidays,
absences). 13 tests, including a real timezone bug caught and fixed during
development (SQLite doesn't preserve timezone info on round-trip, unlike Postgres —
worth knowing if similar datetime arithmetic gets added elsewhere).

**Phase 1:** JWT auth (register/login/refresh/me/change-password), Google OAuth2 (untested), RBAC, DB schema, Alembic migrations, seed script, rate limiting, structured error handling, request logging.

**Phase 2a — Recruitment:** Jobs + Candidates with a state-machine pipeline (applied → screening → interview → hr_approval → offered → accepted/rejected/withdrawn), AI resume screening (upload, parse, LLM scoring, ChromaDB similarity search).

**Phase 2b — Employee Management:** Candidate → Employee provisioning, self-service profile vs HR-only fields, document upload + verification.

**Phase 2c — Onboarding:** Forced password change off temp password, required-document-type activation gate (Aadhaar/PAN/bank proof), onboarding status checklist endpoints.

**Email/Notifications:** Welcome email (temp password) on provisioning, password reset email — both best-effort (failures logged, don't break the underlying action).
