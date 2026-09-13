# Parallax frontend

Parallax is an agent-control dashboard for creating engineering missions and following their execution across GitHub, Jira, Notion, and Slack. This repository contains the hackathon frontend described by the supplied product and integration documents.

## Run locally

```bash
npm install
copy .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The root route redirects to `/dashboard`.

Mock mode is enabled by default, so the complete UI can be demonstrated without the backend. Created demo missions advance from queued to running to completed and are clearly labeled as simulated.

## Connect the FastAPI backend

Set these values in `.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MOCK_MODE=false
```

The frontend consumes:

- `GET /api/dashboard/stats`
- `GET /api/dashboard/activity`
- `GET /api/dashboard/projects`
- `GET /api/integrations`
- `GET /api/missions`
- `GET /api/missions/:id`
- `POST /api/missions`

Responses are validated and normalized in `src/lib/domain.ts` and `src/lib/api.ts`. Active missions poll while queued or running; the query cache is invalidated after mission creation.

## Product routes

- `/dashboard` — truthful operational overview, mission composer, recent work, projects, integrations, activity, and quick actions.
- `/missions` — searchable and filterable mission history.
- `/missions/:id` — mission summary, step trace, timestamps, outputs, and recovery actions.
- `/projects` — project health overview.
- `/integrations` — connection status; management controls remain visibly unavailable until supported.

## Quality checks

```bash
npm run lint
npx tsc --noEmit
npm run build
```

## Design contract

`brand-spec.md`, `direction-approved.md`, and `.hallmark/preflight.json` record the approved Light Control Room direction, token rules, responsive behavior, and pre-implementation critique. Future approval, risk review, context-pack, and realtime features are reserved in the domain capability map but are not presented as working functionality.
