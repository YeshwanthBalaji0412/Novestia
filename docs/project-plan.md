# Novestia Project Plan

## Overview

Novestia is an AI-powered fintech learning platform that teaches beginner investors through hands-on paper trading. Users trade with simulated money using real-time market data, build portfolios, analyze risk through an algorithmic risk engine, and get AI-generated explanations of financial concepts.

The project is designed as a portfolio piece that demonstrates real distributed systems thinking — not just CRUD.

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui | SSR for SEO on landing, App Router for layouts, shadcn for consistent design system |
| Backend | FastAPI (Python), SQLAlchemy (async), Pydantic | Async-native for WebSocket support, Pydantic for request validation and settings |
| Database | PostgreSQL 16 + TimescaleDB | TimescaleDB for time-series price data (automatic partitioning, time-bucket queries, continuous aggregates) |
| Cache / PubSub | Redis 7 | Price cache (5s TTL) + pub/sub fan-out for live price streaming |
| Auth | Clerk | Handles JWT, OAuth, session management — we store only a thin local user record |
| Market Data | Finnhub (WebSocket + REST) | Free tier: 60 REST calls/min, real-time WebSocket. REST for trade execution, WebSocket for streaming |
| AI | Google Gemini 2.5 Flash | Beginner-friendly explanations of stocks, metrics, and risk reports |
| Observability | structlog (JSON logging), OpenTelemetry | Structured logs for debugging, OTel for distributed tracing |
| Deployment | Railway | Postgres, Redis, and app hosting in one platform |

## Architecture Summary

### Three Key Decisions

1. **Trade execution: force-fetch live price.** WebSocket-cached prices are for display only. Trade execution makes a synchronous Finnhub REST call for the current price. Correctness over latency.

2. **Market hours: hybrid 24/7.** Users can trade anytime. During market hours, trades execute at live price. After hours, trades execute at last close and are tagged `executed_after_hours = true` with a UI banner.

3. **WebSocket scope: dynamic subscriptions.** Clients subscribe to portfolio + watchlist + current view tickers. Subscribe/unsubscribe on navigation. Refcounted per connection. One worker process holds the single Finnhub WebSocket connection globally.

### Price Flow

```
Finnhub WebSocket → Worker process (single global subscriber)
                  → Redis cache (overwrite, 5s TTL)
                  → Redis pub/sub (per-ticker channels)
                  → API server instances (subscribe to channels their clients need)
                  → WebSocket fan-out to connected clients
```

Trade execution bypasses the cache: `Client → API → Finnhub REST → Postgres transaction → Response`.

### Graceful Degradation

| Failure | Behavior |
|---------|----------|
| Finnhub down | Stale cached prices served, "data delayed" banner after 30s |
| Redis down | API falls back to direct Finnhub REST (rate-limited) |
| Worker crash | Auto-restart, resubscribe from Redis channel list |
| Postgres down | Trades fail, prices still stream (no Postgres in read path) |

### Risk Engine

Algorithmic scoring (0–100, higher = riskier) with 5 subscores:
- Concentration (single-position weight, ETF discount at 0.4×)
- Sector concentration
- Volatility (weighted portfolio beta)
- Diversification (position count + ETF ratio)
- Cash ratio (U-shaped: too little or too much)

Composite: `max(weighted_avg, 0.85 × max_structural_subscore)` — severe single risks can't hide.

Engine produces deterministic templated explanations. Gemini AI narrates over them for beginner-friendly interpretation.

## Data Model

5 domains, ~16 tables. See [Design Decisions](design-decisions.md) for full schema.

- **Identity:** `users` (thin, Clerk owns auth)
- **Portfolio:** `portfolios`, `holdings` (materialized), `transactions` (immutable log), `journal_entries`, `watchlists`, `watchlist_items`, `portfolio_snapshots`
- **Market Data:** `stocks` (ticker as PK), `stock_snapshots`, `price_history` (TimescaleDB hypertable)
- **AI/Risk:** `ai_explanations` (LLM cache with prompt_version), `risk_reports` (historical, never overwritten)
- **System:** `api_call_log`

## API Surface

22 REST endpoints + 1 WebSocket, versioned under `/api/v1/`. See [API Surface](api-surface.md) for full request/response shapes.

Key conventions: cursor-based pagination, money as strings ("1234.5600"), ISO 8601 UTC timestamps, `{error: {code, message, details}}` envelope.
