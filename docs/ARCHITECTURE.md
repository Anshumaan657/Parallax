# Parallax Backend Structure

```text
Parallax/
├── app/
│   ├── main.py                 # FastAPI application and middleware
│   ├── config.py               # Validated environment configuration
│   ├── database.py             # Async PostgreSQL sessions
│   ├── queue.py                # Redis connection
│   ├── worker.py               # Separate ARQ worker process
│   ├── metrics.py              # Prometheus instruments
│   └── routers/
│       └── health.py           # Liveness and dependency readiness
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

