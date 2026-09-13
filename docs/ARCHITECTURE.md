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
│       └── workspaces.py       # Workspace context and membership roles
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
