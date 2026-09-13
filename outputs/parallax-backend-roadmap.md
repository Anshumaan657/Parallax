# Parallax Backend Roadmap

## Phase 1 — Local FastAPI foundation

- FastAPI API and separate ARQ worker
- PostgreSQL, Redis, and Prometheus in Docker Compose
- Pydantic environment validation, JSON logs, health/readiness, and OpenAPI
- SQLAlchemy, Alembic migration, Ruff, MyPy, Pytest, and `.env.example`

Done when the stack runs locally and `GET /health` succeeds.

## Phase 2 — Workspace and core data

- Local JWT authentication and roles
- Workspaces, users, teams, projects, repositories, integrations, and identity mappings
- Workspace scoping in every query

## Phase 3 — Manual missions and frontend APIs

- `POST /api/missions`, list/detail/polling, dashboard, activity, projects, and integration status
- Explicit mission state machine, idempotency, correlation IDs, audit events
- Seed and mock endpoints matching the Drive frontend

## Phase 4 — Four integration adapters

- GitHub read/context operations
- Jira read and approved updates
- Notion read and approved documentation
- Slack approved notifications
- Real and mock modes with health checks

## Phase 5 — Context and agent-team gateway

- Worker context collection and evidence storage
- Typed read-only request to the Agent service
- Validation of context packs, risk, effort, reviewers, confidence, citations, and proposals
- Deterministic fallback for demos

## Phase 6 — Policy and approval

- Typed action proposals and approval bundles
- Approve, edit, reject, and cancel APIs
- Deterministic policy rules and mandatory revalidation after edits

## Phase 7 — Execution, verification, and recovery

- Idempotent approved execution with Redis locks, retries, and rate limits
- Read-after-write verification for every integration mutation
- Partial-failure recovery and immutable audit history

## Phase 8 — Analytics and demo reliability

- Mission timeline, activity, audit, integration health, SLA, and dashboard APIs
- Metrics, traces, contract/integration/E2E tests, demo reset, backup, and failure simulation

