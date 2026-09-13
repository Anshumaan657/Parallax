# Parallax Backend Structure

```text
Parallax/
├── app/
│   ├── main.py                 # FastAPI application and middleware
│   ├── config.py               # Validated environment configuration
│   ├── database.py             # Async PostgreSQL sessions
│   ├── models.py               # Workspace-scoped SQLAlchemy models
│   ├── schemas.py              # API request and response contracts
│   ├── security.py             # Argon2, JWT, and refresh-token primitives
│   ├── dependencies.py         # Authentication/workspace/role guards
│   ├── queue.py                # Redis connection
│   ├── worker.py               # Separate ARQ worker process
│   ├── metrics.py              # Prometheus instruments
│   └── routers/
│       ├── health.py           # Liveness and dependency readiness
│       ├── auth.py             # Local authentication and token rotation
│       ├── workspaces.py       # Workspace context and membership roles
│       ├── missions.py         # Manual mission commands and reads
│       ├── dashboard.py        # Workspace dashboard projections
│       └── integrations.py     # Four-integration connection status
│   └── services/
│       └── missions.py         # State transitions, DTOs, and audit activity
├── migrations/                 # Alembic PostgreSQL migrations
├── infra/prometheus/           # Local metrics collection
├── docs/
│   ├── API.md                  # Frontend-facing API guide
│   ├── ALIGNMENT.md            # Drive audit and team boundaries
│   └── openapi.json            # Generated API contract
├── scripts/export_openapi.py
├── tests/
├── Dockerfile
└── docker-compose.yml
```

Future business modules are added under `app/modules/`: missions, integrations, context packs, proposals, policy, approvals, execution, verification, audit, and dashboard.

The API handles short request/response work. The worker handles context collection, agent-service calls, retries, external execution, and verification. PostgreSQL is the system of record; Redis is only for jobs, locks, rate limits, and temporary state.

## Identity boundary

Access tokens contain user, workspace, and refresh-session IDs. Every protected request verifies the active user, workspace membership, workspace scope, and non-revoked server-side session. Refresh tokens are random opaque values; only SHA-256 hashes are stored. Passwords are hashed with Argon2id.

Workspace-owned models carry `workspace_id`. Query services must derive this value from the verified request identity rather than accept it as an authorization decision from request bodies.

## Mission processing boundary

```text
Frontend/PM -> FastAPI -> PostgreSQL transaction (mission + outbox + audit)
                              |
                              v
                       outbox dispatcher -> Redis/ARQ -> mission worker
                                                              |
                                                              v
                                                    planning (Phase 3 boundary)
```

PostgreSQL is authoritative. Creating a mission atomically writes the mission, initial transition, activity/audit records, and an outbox job. A periodic worker dispatcher transfers committed outbox jobs to ARQ with a stable job ID. The mission worker then performs a guarded `queued -> planning` transition. This avoids losing work between a database commit and Redis enqueue.

Phase 3 does not collect external context, invoke the Agent service, or mutate integrations. Those boundaries are implemented in Phases 4–7.
