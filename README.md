# Novestia

AI-powered fintech learning platform with real-time market data, paper trading, portfolio risk analytics, and explainable AI insights for beginner investors.

**Status:** Phase 1 — Repo scaffolding and tooling

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python), SQLAlchemy, Pydantic |
| Database | PostgreSQL 16 + TimescaleDB (time-series price data) |
| Cache / PubSub | Redis 7 |
| Auth | Clerk |
| Market Data | Finnhub (WebSocket + REST) |
| AI | Google Gemini 2.5 Flash |
| Observability | structlog, OpenTelemetry |
| Deployment | Railway (planned) |

## Local Development

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for Postgres + Redis)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)
- Node.js 20+
- Python 3.12+

### Quick Start

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Backend
cd backend
cp .env.example .env        # fill in API keys
uv sync
uv run uvicorn novestia.main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd frontend
cp .env.example .env.local   # fill in keys
pnpm install
pnpm dev
```

### Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0","timestamp":"..."}
```

## Project Structure

```
novestia/
├── backend/          # FastAPI API server
├── frontend/         # Next.js web app
├── docs/             # Design documents
├── .github/          # CI workflows
└── docker-compose.yml
```

## Design Documents

- [Design Decisions](docs/design-decisions.md) — Architecture, data model, risk engine
- [API Surface](docs/api-surface.md) — All endpoints, request/response shapes, WebSocket protocol
- [Project Plan](docs/project-plan.md) — Overview, stack, architecture summary
