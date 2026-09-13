# Parallax API Contract

FastAPI is the source of truth for the API contract.

## Documentation

| Resource | Local URL | Use |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | Interactive reference for frontend and QA |
| ReDoc | `http://localhost:8000/redoc` | Readable API reference |
| OpenAPI JSON | `http://localhost:8000/openapi.json` | Generated client and contract tests |
| Prometheus metrics | `http://localhost:8000/metrics` | Monitoring |

Run `python scripts/export_openapi.py` after changing a route. Commit the resulting `docs/openapi.json`.

## Implemented in Phase 1

### `GET /health`

Process liveness. It does not check dependencies.

```json
{
  "status": "ok",
  "service": "parallax-api",
  "uptime_seconds": 42.5
}
```

### `GET /api/health`

Compatibility path for the Drive MVP. It returns the same response as `GET /health`.

### `GET /ready`

Checks PostgreSQL, Redis, and the worker heartbeat. Returns `200` when all are up and `503` otherwise.

```json
{
  "status": "ready",
  "dependencies": {
    "postgres": "up",
    "redis": "up",
    "worker": "up"
  }
}
```

## Frontend contract to implement in the mission phase

These paths match `parallax-mvp/frontend/src/api.js` from the shared Drive:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/dashboard/stats` | Dashboard counts and project health |
| `GET` | `/api/dashboard/activity` | Recent verified/audited activity |
| `GET` | `/api/dashboard/projects` | Projects available to the mission form |
| `GET` | `/api/integrations` | GitHub, Jira, Notion, and Slack status |
| `GET` | `/api/missions` | Recent missions |
| `POST` | `/api/missions` | Submit a manual PM/agent-user mission |
| `GET` | `/api/missions/{mission_id}` | Poll mission timeline and result |

The frontend should generate types from `docs/openapi.json`; it must not maintain a second handwritten response schema.

### Required frontend response fields

```text
MissionCreate
  prompt: string
  project: string = "General"

MissionRead
  id: integer
  prompt: string
  project: string
  status: queued | planning | waiting_for_approval | running |
          completed | blocked | rejected | cancelled | partially_complete | failed
  progress_current: integer
  progress_total: integer
  result_summary: string | null
  steps: MissionStep[]
  created_at: ISO-8601 datetime
  updated_at: ISO-8601 datetime

IntegrationStatus
  name: GitHub | Jira | Notion | Slack
  connected: boolean
  detail: string

DashboardStats
  active_tasks: integer
  completed_this_week: integer
  blocked: integer
  awaiting_approval: integer
  project_health_pct: integer
```

The Drive frontend currently styles `queued`, `running`, `completed`, `blocked`, and `failed`. The frontend team must add styles for approval, rejection, cancellation, and partial completion before those states are enabled.

## Implemented in Phase 2

Protected routes use:

```http
Authorization: Bearer <access-token>
X-Workspace-ID: <workspace-uuid>
```

`X-Workspace-ID` is optional because the access token is already workspace-scoped. If supplied, it must match the token. To change workspaces, log in with the desired `workspace_id` and receive a newly scoped token.

### `POST /api/auth/register`

Creates a user, workspace, owner membership, and token session atomically. Returns `201`. Duplicate email or workspace slug returns `409`.

```json
{
  "email": "owner@example.com",
  "password": "a-password-with-12-or-more-characters",
  "display_name": "Example Owner",
  "workspace_name": "Example Engineering",
  "workspace_slug": "example-engineering"
}
```

### `POST /api/auth/login`

Authenticates a local user. `workspace_id` is optional; when omitted, the oldest membership is selected. Returns an access token and opaque refresh token.

### `POST /api/auth/refresh`

Rotates the supplied refresh token. The old refresh session and its access token become invalid immediately.

### `POST /api/auth/logout`

Revokes the refresh session. Returns `204` with no response body.

### `GET /api/auth/me`

Returns the current user, active workspace, role, and available workspaces. Password and token hashes are never returned.

### `GET /api/workspaces/current`

Returns the workspace and role derived from the access token.

### `GET /api/workspaces/current/members`

Lists members of the token-scoped workspace. Requires authentication.

### `PATCH /api/workspaces/current/members/{user_id}`

Changes a member role. Requires owner or admin. Only owners may manage the owner role, and a workspace must retain at least one owner.

Available roles are `owner`, `admin`, `manager`, `reviewer`, and `viewer`.

## Endpoint documentation rule

Every endpoint must declare a tag, summary, request model, response model, error responses, and stable status codes. Mutation endpoints must also document idempotency and approval behavior.
