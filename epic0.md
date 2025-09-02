Epic E0 — Dev Environment & Scaffolding (detailed tickets)

Estimated duration for a junior: ~3–5 dev days total. Assign tickets independently.

T0.1 — Repository bootstrap (FastAPI + SQLModel)

Why: Create the minimal runnable API.
Deliverables:

Files & paths:

app/main.py (creates FastAPI app, includes routers)

app/config.py (Pydantic Settings: APP_ENV, DATABASE_URL, LOG_LEVEL, VERSION, GIT_SHA)

app/db.py (SQLModel engine/session factory)

app/api/health.py (/healthz, /version)

app/__init__.py

pyproject.toml (or requirements.txt)

README.md quickstart

Endpoints:

GET /healthz → {"ok": true}

GET /version → {"version": "...", "git_sha": "..."} from env
Acceptance Criteria:

App serves locally: uvicorn app.main:app --reload

/healthz and /version return 200
Tests:

tests/test_health.py for both endpoints using TestClient

T0.2 — Dockerfile (multi-stage) + .dockerignore

Why: Match ECS runtime locally.
Deliverables:

Dockerfile:

Stage 1: build deps

Stage 2: slim runtime, non-root user, CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]

.dockerignore to keep context small
AC:

docker build . succeeds

Container runs; curl localhost:8000/healthz returns ok

T0.3 — docker-compose (API + Postgres) and .env.example

Why: Local DB parity.
Deliverables:

docker-compose.yml with:

db: postgres:15, healthcheck, mounted volume

api: builds local image, depends_on db, env DATABASE_URL=postgresql+psycopg://...

.env.example with all required vars
AC:

docker compose up starts both; API becomes healthy

Logs show connected to DB
Tests: Manual curl to health/version.

T0.4 — Alembic + SQLModel wiring

Why: Schema management.
Deliverables:

alembic.ini, alembic/ with env.py using SQLModel metadata

app/models/base.py with TimestampMixin (created_on, updated_on auto-set)

First empty migration versions/000_initial_base.py
AC:

alembic revision --autogenerate detects changes

alembic upgrade head works inside compose
Tests:

Scripted up/down within CI succeeds

T0.5 — Logging & request IDs + Problem+JSON errors

Why: Operability & consistent errors.
Deliverables:

app/middleware/logging.py: inject or propagate X-Request-ID; JSON logs

app/errors.py: exception handlers mapping to application/problem+json
AC:

Requests log request_id, method, path, status

404/422 return problem+json with fields type, title, status, detail
Tests:

Simulated error test asserts response shape and header propagation

T0.6 — Lint, format, test, CI

Why: Quality gates.
Deliverables:

Makefile targets: dev, lint, format, test, migrate, downgrade

Pre-commit with black, ruff, isort

.github/workflows/ci.yml: install, lint, test, build docker
AC:

Pre-commit runs locally

CI green on main/PR

T0.7 — JSONata evaluator stub

Why: Many later components depend on it.
Deliverables:

app/lib/jsonata.py exposing:

class JsonataError(Exception): ...
def evaluate(expr: str, data: dict, timeout_ms: int = 100) -> Any: ...


Implementation can be a placeholder raising NotImplementedError with tests scaffolding.
AC:

Function exists and is importable; unit tests cover API
Tests:

tests/lib/test_jsonata.py with basic happy/error paths (mark xfail if not yet implemented)