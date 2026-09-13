# Parallax Backend

Local-first Python backend for the Parallax MVP. It accepts missions entered by a PM or agent user; GitHub webhooks are not part of the current input flow.

The backend currently includes the local FastAPI/ARQ/PostgreSQL/Redis foundation, workspace authentication and authorization, manual mission APIs with a durable transactional outbox, and typed GitHub, Jira, Notion, and Slack adapters.

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

## Submit a manual mission

Register or log in, then send the access token to the mission API:

```bash
curl -X POST http://localhost:8000/api/missions \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: demo-mission-1" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Prepare a release-readiness plan","project":"General"}'
```

The request returns `202`. Poll `GET /api/missions/{mission_id}` for timeline updates. In Phase 3 the worker intentionally stops at `planning`; no Agent or external integration is called yet.

## Integration modes

`INTEGRATION_MODE=mock` is the default and makes no third-party network requests. It supplies deterministic GitHub, Jira, Notion, and Slack behavior for local frontend, backend, and Agent-team development.

Set `INTEGRATION_MODE=real` and configure the provider variables in `.env` to use real adapters. Check a connection through `POST /api/integrations/{provider}/check`. Jira, Notion, and Slack business writes are not exposed as public APIs and require backend approval proof even in mock mode.
