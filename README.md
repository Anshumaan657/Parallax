
# Parallax

Parallax is an engineering-operations mission platform. It accepts a manual
mission, collects integration context, produces an evidence-backed assessment,
gates external writes behind policy and human approval, executes approved
actions, verifies the result, and records the complete timeline.

## Repository layout

- `app/` — FastAPI API, PostgreSQL models, integrations, policy, and worker.
- `src/` — Next.js operations console.
- `packages/agent-core/` — separately packaged TypeScript/LangGraph Agent Core.
- `migrations/` — Alembic database migrations.

## Local development

Install the backend and frontend dependencies separately:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm ci
npm --prefix packages/agent-core ci
```

Start PostgreSQL, Redis, the API, and the worker with:

```bash
docker compose up --build
```

The frontend is available at `http://localhost:3000`; the API is available at
`http://localhost:8000`.

For local Agent Core development without a configured service key, explicitly
set `AGENT_ALLOW_UNAUTHENTICATED=true`. Set `AGENT_SERVICE_API_KEY` and
`AGENT_ALLOWED_ORIGIN` for deployed environments. The unauthenticated override
must not be used in production.

## Verification commands

```bash
./.venv/bin/pytest
./.venv/bin/ruff check .
./.venv/bin/mypy app scripts/seed_demo.py
npm run typecheck
npm run lint
npm test
npm run agent:typecheck
npm run agent:test
npm run api:check
npm run build
```

The current release includes the mission, approval, execution, verification,
analytics, and integration-health platform. GitHub webhooks, Google Calendar,
Linear, and live-vendor acceptance testing remain separate product milestones;
they are not represented as completed by mock endpoints.
