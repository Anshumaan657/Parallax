# Backend Handoff

## Current state

- Branch: `feature/backend-development`
- Phase 1: complete and committed as `b5ff4ec`
- Phase 2: implemented and verified in the working tree; not committed or pushed
- Next phase: Phase 3 — manual missions and frontend APIs

## Phase 2 implementation

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

`20260913_0002_identity_and_core_data` follows the Phase-1 migration.

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

## Known limitations

- Local registration is intentionally open for the local MVP; invitations and email verification are not implemented.
- Access JWT signing uses a shared secret. Key rotation and asymmetric signing are deferred.
- Integration rows store credential references only; encrypted credential persistence belongs with the integration phase.
- Team/project/repository management endpoints are deferred until their first frontend use.
- Refresh-session cleanup is deferred to the reliability phase.

## Verification result

- Ruff: passed
- strict MyPy: passed for the app and seed command
- Pytest: 9 passed
- Existing PostgreSQL migration: `20260913_0002 (head)`
- Fresh PostgreSQL migration: passed through `20260913_0002`
- Alembic schema drift check: no new upgrade operations
- Docker readiness: PostgreSQL, Redis, and worker all `up`
- Manual registration/login smoke test: `201` / `200`

## Phase 3 boundary

Phase 3 should add manual mission persistence, state transitions, idempotency, audit events, ARQ enqueueing, and the exact dashboard/mission endpoints documented in `docs/API.md`. It must derive workspace and actor IDs from `RequestIdentity`; it must not accept them as trusted request-body authorization fields.
