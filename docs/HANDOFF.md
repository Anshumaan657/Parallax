# Backend Handoff

## Current state

- Branch: `feature/backend-development`
- Phase 1: complete and committed as `b5ff4ec`
- Phase 2: complete and committed as `16016b4`
- Phase 3: implemented and verified in the working tree; not committed or pushed
- Next phase: Phase 4 — four integration adapters

## Phase 3 implementation

Frontend/API endpoints:

- `POST /api/missions`
- `GET /api/missions`
- `GET /api/missions/{mission_id}`
- `POST /api/missions/{mission_id}/cancel`
- `GET /api/dashboard/stats`
- `GET /api/dashboard/activity`
- `GET /api/dashboard/projects`
- `GET /api/integrations`

Persistence added for missions, ordered steps, state transitions, activity, immutable-style audit events, idempotency records, and transactional outbox jobs. Manual submission commits the initial mission and job intent atomically. The worker dispatches the outbox to ARQ with a stable job ID and advances the mission from `queued` to `planning`.

The mission state machine rejects illegal transitions. Mission reads, dashboard projections, projects, integrations, idempotency keys, and correlation IDs are all workspace-scoped.

## Existing Phase 2 foundation

Models:

- users
- workspaces
- workspace memberships
- teams
- projects
- repositories
- integrations
- external identities
- refresh sessions

All identifiers are UUIDs. Every workspace-owned model contains `workspace_id`. Workspace roles are owner, admin, manager, reviewer, and viewer.
Registration and demo seeding create disconnected GitHub, Jira, Notion, and Slack integration records for the workspace.

Authentication endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Workspace endpoints:

- `GET /api/workspaces/current`
- `GET /api/workspaces/current/members`
- `PATCH /api/workspaces/current/members/{user_id}`

## Security decisions

- Argon2id password hashes
- HS256 access JWTs with a 15-minute default lifetime
- Opaque random refresh tokens; only SHA-256 token hashes are stored
- Server-side refresh sessions support rotation, logout, and access-token revocation
- Access tokens are scoped to exactly one workspace and membership is checked on every protected request
- Admins cannot manage the owner role; the last owner cannot be demoted
- Raw credentials, password hashes, and token hashes are not exposed by APIs

## Migration

`20260913_0003_manual_missions` follows the Phase-2 identity migration.

## Environment variables

- `JWT_SECRET`
- `JWT_ACCESS_TOKEN_MINUTES`
- `JWT_REFRESH_TOKEN_DAYS`
- optional `DEMO_OWNER_*` and `DEMO_WORKSPACE_*` variables for local seeding

## Commands

```bash
alembic upgrade head
ruff check .
mypy app scripts/seed_demo.py
pytest
python scripts/export_openapi.py
docker compose up --build -d
```

## Current boundary

- The worker deliberately stops at `planning`; context collection and the Agent gateway are Phase 5.
- Integration records are status placeholders; real/mock adapters and credential handling are Phase 4.
- No external system is mutated and no approval or execution behavior is claimed in Phase 3.
- Local registration remains intentionally open for the local MVP.

## Verification result

- Ruff: passed
- strict MyPy: passed for the app and seed command
- Pytest: 12 passed (including Phase 3 API, isolation, outbox, and worker tests)
- Generated OpenAPI contract: refreshed
- Existing PostgreSQL database: `20260913_0003 (head)`
- Fresh PostgreSQL migration: passed from empty schema through `20260913_0003`
- Alembic schema drift check: no new upgrade operations
- Docker: API healthy; PostgreSQL and Redis healthy; worker running
- Readiness: `ready`; Prometheus API target: `up`
- Manual smoke: registration `201`, mission submission `202`, durable worker reached `planning`, and exactly four integrations returned
- Worker jobs observed: zero failed and zero retried
