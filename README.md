# Parallax Backend

Local-first Python backend for the Parallax MVP. It accepts missions entered by a PM or agent user; GitHub webhooks are not part of the current input flow.

The Phase-1 stack contains FastAPI, a separate ARQ worker, PostgreSQL, Redis, Alembic migrations, structured JSON logging, Prometheus metrics, health/readiness checks, and OpenAPI documentation.

## Run the complete local stack

```bash
cp .env.example .env
docker compose up --build
```

Local endpoints:

- API liveness: <http://localhost:8000/health>
- Drive/frontend compatibility health: <http://localhost:8000/api/health>
- Dependency readiness: <http://localhost:8000/ready>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Prometheus metrics: <http://localhost:8000/metrics>
- Prometheus UI: <http://localhost:9090>

## Run without containers

Start PostgreSQL and Redis, copy `.env.example` to `.env`, and change their hostnames to `localhost`. Then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal:

```bash
source .venv/bin/activate
arq app.worker.WorkerSettings
```

## Quality checks

```bash
ruff check .
mypy app
pytest
python scripts/export_openapi.py
```

The maintained API contract and team boundaries are documented in `docs/API.md` and `docs/ALIGNMENT.md`.

## Local authentication

Phase 2 adds local JWT authentication and workspace-scoped authorization. Before sharing a non-local environment, replace `JWT_SECRET` with a random value of at least 32 characters.

Optional demo identity seeding uses values from `.env`:

```bash
python scripts/seed_demo.py
```

The seed command refuses to run unless `DEMO_OWNER_EMAIL` and a password of at least 12 characters are configured.
