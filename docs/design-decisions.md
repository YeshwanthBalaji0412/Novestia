# Novestia Design Decisions

Last updated: 2026-05-25

This document captures the three architectural decisions, the complete data model, the price flow architecture, and the risk engine design. Every choice has a stated reason so it can be defended in an interview.

---

## Part 1: Architectural Decisions

### Decision 1: Trade Execution Price — Force-fetch live price at click

When the user clicks Buy or Sell, the backend makes a synchronous call to Finnhub's REST quote endpoint, gets the current price, executes the trade at that price, and returns confirmation. The WebSocket-cached price is used only for display, never for execution.

**Why:** The cached price is fine for display (users understand dashboards lag a few seconds), but the moment money changes hands the price needs to be current. Using cached prices for execution creates a class of bugs where users can game stale prices during volatile moments. Even with fake money, that pattern is a real flaw in the simulation's pedagogical value.

**Tradeoff:** One extra API call per trade. Finnhub free tier allows 60 calls/minute — a single user won't hit that. To scale: add a per-user trade execution rate limiter, not cached execution prices.

**Architectural note:** The cache layer has two read patterns — bulk-cached reads for display and bypass-cache reads for execution. That distinction must be explicit in code.

### Decision 2: Market Hours — Hybrid, trading allowed 24/7 with after-hours labeling

Users can trade anytime. During market hours (9:30am–4:00pm ET, weekdays), trades execute at the live Finnhub price. Outside market hours, trades execute at the last close price and are tagged `executed_after_hours = true`. The UI shows a clear "After-hours simulation — executed at last close" banner.

**Why:** The target user (college student, early-career) will mostly use the app evenings and weekends — exactly when US markets are closed. Blocking trading then kills the product. But pretending markets are always open teaches a false mental model. The hybrid teaches real concepts (market hours, "last close") without locking users out.

**Tradeoff:** Two execution branches (market-open vs after-hours) and one extra column. Both cheap. Weekends: same logic, executed at Friday's close.

### Decision 3: WebSocket Stream Scope — Portfolio + Watchlist + Dynamic Current View

Each connected client subscribes to tickers in their portfolio (holdings), watchlist, and whatever ticker they're currently viewing. Subscriptions are dynamic — subscribe on navigate, unsubscribe on leave (unless the ticker is in portfolio/watchlist).

**Why:** "Portfolio + watchlist only" creates jarring UX (static price on detail pages while dashboard is live). "Everything ever viewed" creates ticker leaks. Dynamic subscription with explicit sub/unsub messages and refcounting per connection is how real trading platforms work.

**Architecture implication:** This is what makes Redis pub/sub earn its place:
```
Finnhub WebSocket → Worker (single subscriber per ticker globally)
                  → Redis pub/sub channel per ticker
                  → API server instances subscribe to channels their clients need
                  → Fan out to connected WebSocket clients
```
One worker holds the single Finnhub connection regardless of user count. New API instances just join Redis channels. Textbook pub/sub fan-out that scales horizontally.

**Frontend mitigation:** `usePriceSubscription(tickers)` React hook handles lifecycle automatically.

---

## Part 2: Data Model

### Domain 1: Identity

**`users`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | Internal ID for all FK relationships |
| `clerk_user_id` | TEXT, UNIQUE, NOT NULL | Maps to Clerk's user ID |
| `email` | TEXT, NOT NULL | Denormalized from Clerk, refreshed on login |
| `display_name` | TEXT | Defaults to email prefix |
| `created_at` | TIMESTAMPTZ, NOT NULL, DEFAULT now() | |
| `onboarded_at` | TIMESTAMPTZ | NULL until onboarding complete |

Index: `clerk_user_id` (unique).

**Why a local table with Clerk:** Every other table needs a stable FK. UUIDs are the abstraction boundary — if you ever migrate off Clerk, you don't rewrite the schema.

### Domain 2: Portfolio

**`portfolios`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id, NOT NULL | |
| `name` | TEXT, NOT NULL | Default: "Main Portfolio" |
| `cash_balance` | NUMERIC(18,4), NOT NULL | Starts at 10000.0000 |
| `starting_balance` | NUMERIC(18,4), NOT NULL | Immutable, for total return % |
| `created_at` | TIMESTAMPTZ, NOT NULL, DEFAULT now() | |

Index: `user_id`.

**Why NUMERIC(18,4):** Floats are forbidden for money. Period. Postgres NUMERIC with explicit precision. 18 total digits, 4 decimal places handles fractional share cost basis without precision loss. Fintech interviewers explicitly test this.

**Why separate table even with 1:1 MVP:** 1-to-many from start costs nothing, prevents migration later.

**`holdings`** — Materialized current state of what the user owns.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `portfolio_id` | UUID, FK → portfolios.id, NOT NULL | |
| `ticker` | TEXT, NOT NULL | Uppercase, normalized on insert |
| `quantity` | NUMERIC(18,8) | 8 decimals for fractional shares |
| `average_cost` | NUMERIC(18,4) | Weighted avg cost basis per share |
| `total_cost` | NUMERIC(18,4) | quantity × average_cost, denormalized |
| `first_purchased_at` | TIMESTAMPTZ | |
| `last_updated_at` | TIMESTAMPTZ | |

Unique: `(portfolio_id, ticker)`.

**Why materialized, not event-sourced:** Pure event-sourcing means every dashboard load recomputes holdings from the full transaction log. Materializing + updating transactionally with each trade is the right tradeoff: read performance over write simplicity, consistency risk mitigated by single DB transaction.

**`transactions`** — Immutable event log. Every buy and sell, forever.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `portfolio_id` | UUID, FK → portfolios.id, NOT NULL | |
| `ticker` | TEXT, NOT NULL | |
| `transaction_type` | TEXT, NOT NULL | CHECK in ('BUY', 'SELL') |
| `quantity` | NUMERIC(18,8), NOT NULL | |
| `execution_price` | NUMERIC(18,4), NOT NULL | Price at moment of execution |
| `total_amount` | NUMERIC(18,4), NOT NULL | quantity × execution_price |
| `realized_pnl` | NUMERIC(18,4) | NULL for buys, computed for sells |
| `executed_after_hours` | BOOLEAN, NOT NULL, DEFAULT false | |
| `journal_note` | TEXT | One-sentence reflection, required by UI |
| `executed_at` | TIMESTAMPTZ, NOT NULL, DEFAULT now() | |

Indexes: `(portfolio_id, executed_at DESC)`, `(portfolio_id, ticker)`.

**Why `realized_pnl` on the row:** Computed at sell time using current `average_cost`, frozen forever. Historical P/L is stable even if cost basis calculation changes later. Audit-friendly.

**`journal_entries`** — Separate from transactions because journals can be standalone.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `portfolio_id` | UUID, FK → portfolios.id, NOT NULL | |
| `transaction_id` | UUID, FK → transactions.id, NULLABLE | NULL = standalone reflection |
| `content` | TEXT, NOT NULL | |
| `created_at` | TIMESTAMPTZ, NOT NULL, DEFAULT now() | |

Index: `(portfolio_id, created_at DESC)`.

**`watchlists`** and **`watchlist_items`** — Standard two-table pattern.

`watchlists`: `id`, `user_id`, `name`, `created_at`.
`watchlist_items`: `id`, `watchlist_id`, `ticker`, `added_at`. Unique: `(watchlist_id, ticker)`.

**`portfolio_snapshots`** — Daily portfolio value snapshots for performance charts.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `portfolio_id` | UUID, FK → portfolios.id, NOT NULL | |
| `total_value` | NUMERIC(18,4), NOT NULL | Cash + market value |
| `cash_balance` | NUMERIC(18,4), NOT NULL | |
| `recorded_at` | TIMESTAMPTZ, NOT NULL | |

Index: `(portfolio_id, recorded_at DESC)`. One row per portfolio per day.

### Domain 3: Market Data

**`stocks`** — Canonical reference for every ticker the platform knows about.

| Column | Type | Notes |
|---|---|---|
| `ticker` | TEXT, PK | Uppercase |
| `company_name` | TEXT, NOT NULL | |
| `exchange` | TEXT | NYSE, NASDAQ, etc. |
| `sector` | TEXT | Critical for sector concentration risk |
| `industry` | TEXT | More granular than sector |
| `instrument_type` | TEXT, NOT NULL | 'STOCK' or 'ETF' |
| `currency` | TEXT, NOT NULL, DEFAULT 'USD' | |
| `metadata_updated_at` | TIMESTAMPTZ | |

**Why ticker as PK:** Natural key, globally unique within a market, used everywhere as user-facing identifier. UUID would mean every join needs a translation.

**`stock_snapshots`** — Current-state metrics, separate from stocks for different update cadences.

| Column | Type | Notes |
|---|---|---|
| `ticker` | TEXT, PK, FK → stocks.ticker | |
| `last_price` | NUMERIC(18,4) | |
| `previous_close` | NUMERIC(18,4) | For daily change |
| `market_cap` | BIGINT | In USD |
| `pe_ratio` | NUMERIC(10,4) | |
| `eps` | NUMERIC(10,4) | |
| `dividend_yield` | NUMERIC(8,6) | Decimal: 0.025 = 2.5% |
| `week_52_high` | NUMERIC(18,4) | |
| `week_52_low` | NUMERIC(18,4) | |
| `beta` | NUMERIC(8,4) | For risk engine |
| `expense_ratio` | NUMERIC(8,6) | NULL for stocks, populated for ETFs |
| `snapshot_taken_at` | TIMESTAMPTZ | |

**`price_history`** — TimescaleDB hypertable.

| Column | Type | Notes |
|---|---|---|
| `ticker` | TEXT, NOT NULL, FK → stocks.ticker | |
| `recorded_at` | TIMESTAMPTZ, NOT NULL | |
| `price` | NUMERIC(18,4), NOT NULL | |
| `volume` | BIGINT | NULL if unavailable |
| `source` | TEXT, NOT NULL | 'live_stream', 'rest_quote', 'eod_close' |

Hypertable on `recorded_at`. Index: `(ticker, recorded_at DESC)`.

**Sampling rule:** Worker stores at most one tick per ticker per minute, plus EOD close. Timescale continuous aggregates roll into 5min, hourly, daily buckets for charts.

### Domain 4: AI and Risk

**`ai_explanations`** — LLM output cache.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `content_type` | TEXT, NOT NULL | 'stock_overview', 'metric_explanation', 'risk_interpretation' |
| `cache_key` | TEXT, NOT NULL | Hash of inputs |
| `content` | TEXT, NOT NULL | The explanation |
| `model` | TEXT, NOT NULL | 'gemini-2.5-flash' etc. |
| `prompt_version` | TEXT, NOT NULL | Invalidation on prompt change |
| `generated_at` | TIMESTAMPTZ, NOT NULL | |
| `expires_at` | TIMESTAMPTZ | NULL = never expires |

Unique: `(content_type, cache_key, prompt_version)`.

**`risk_reports`** — Historical, never overwritten.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `portfolio_id` | UUID, FK → portfolios.id, NOT NULL | |
| `overall_score` | INTEGER, NOT NULL | 0–100 |
| `concentration_score` | INTEGER | |
| `sector_concentration_score` | INTEGER | |
| `volatility_score` | INTEGER | |
| `diversification_score` | INTEGER | |
| `cash_ratio_score` | INTEGER | |
| `engine_explanation` | TEXT, NOT NULL | Templated, deterministic |
| `ai_interpretation` | TEXT | Optional Gemini narrative |
| `computed_at` | TIMESTAMPTZ, NOT NULL | |

Index: `(portfolio_id, computed_at DESC)`.

### Domain 5: System

**`api_call_log`** — External API usage tracking.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `provider` | TEXT, NOT NULL | 'finnhub', 'gemini' |
| `endpoint` | TEXT, NOT NULL | |
| `status_code` | INTEGER | |
| `latency_ms` | INTEGER | |
| `called_at` | TIMESTAMPTZ, NOT NULL | |

Index: `(provider, called_at DESC)`. 30-day retention.

### Not in MVP schema
- `alerts` — post-MVP
- `news_articles` / `sentiment_results` — post-MVP
- `notifications` — post-MVP

---

## Part 3: Price Flow Architecture

### Five flows

**Flow 1: New ticker enters the system.** User searches "NVDA" → API checks Redis cache → miss → Finnhub REST quote → return to user + write Redis cache (5s TTL) + write `stock_snapshots` → message worker to subscribe on Finnhub WebSocket.

**Flow 2: Continuous streaming.** Worker receives Finnhub ticks → writes Redis cache (overwrite, 5s TTL) → publishes to Redis pub/sub `prices:NVDA` → decides whether to persist to `price_history` (max 1/min sampling).

**Flow 3: Client subscribes.** Client opens WebSocket → JWT validated → server fetches portfolio+watchlist tickers → subscribes to Redis channels → forwards price messages as JSON frames. Client navigates → sends subscribe/unsubscribe messages → server adds/drops channels.

**Flow 4: Trade execution (bypasses everything).** POST /trade → Finnhub REST quote (synchronous, not cached) → DB transaction: insert transaction + upsert holding + update cash + compute realized_pnl → return confirmation.

**Flow 5: Disconnect cleanup.** Client disconnects → server decrements refcounts → zero-refcount channels unsubscribed → background reaper checks every 5min for Finnhub subscriptions with no Redis subscribers for 10+ min → unsubscribes from Finnhub.

### Failure modes

| Failure | Behavior | Recovery |
|---------|----------|----------|
| Finnhub disconnect | Stale prices served from cache, `stale: true` flag after 30s, "Live data delayed" badge | Worker reconnects with exponential backoff, replays subscriptions |
| Redis disconnect | Worker buffers ≤1000 messages, API falls back to direct Finnhub REST with rate limiting | Worker replays on reconnect, Sentry alerts |
| Worker crash | Prices freeze for all clients | Process supervisor restarts, worker resubscribes from Redis channel list |
| Postgres down | Trade execution fails, prices still stream (no Postgres in read path) | Standard DB recovery |

### Why this is interview-worthy
1. Worker is the **only** thing talking to Finnhub — rate limit is a non-issue regardless of user count
2. Architecture **degrades gracefully** — each layer fails independently
3. **Read and write paths are separated** — streaming optimized for throughput, trading for correctness. Small-scale CQRS.

---

## Part 4: Risk Engine

### Purpose
Answers: "How dangerous is this portfolio for a beginner who doesn't know what diversification means?" Teaching tool, not optimizer. Higher score = higher risk (0–100).

### Inputs (all local, no external API calls)
1. Holdings joined to `stocks` (sector, instrument_type) and `stock_snapshots` (last_price, beta)
2. `portfolios.cash_balance`
3. Total portfolio value = sum(quantity × last_price) + cash
4. `portfolios.starting_balance`
5. Benchmark beta of 1.0

### Subscore 1: Concentration (single-position exposure)
```
max_position_weight = max(holding_value / total_value)
ETF adjustment: effective_weight = actual_weight × 0.4 for ETFs
Score: 0 if ≤ 0.10, 100 if ≥ 0.50, linear between
```
Reports: the ticker and its weight.

### Subscore 2: Sector Concentration
```
max_sector_weight = max(sector_weights)
ETFs bucketed as "Diversified"
Score: 0 if ≤ 0.30, 100 if ≥ 0.70, linear between
```
Reports: the sector and its weight.

### Subscore 3: Volatility
```
weighted_beta = sum(holding_weight × beta)
ETFs assumed beta=1.0, cash beta=0
Score: 0 if ≤ 1.0, 100 if ≥ 2.0, linear between
```
Reports: portfolio's weighted beta.

### Subscore 4: Diversification (inverse)
```
Component A (position count): 0 at ≥15, 100 at ≤1, linear
Component B (ETF ratio): 0 at ≥0.50, 60 at 0.00, linear
Blended: 0.6 × A + 0.4 × B
```
Reports: position count and ETF ratio.

### Subscore 5: Cash Ratio (U-shaped)
```
≤ 0.02:         70 (under-cash)
0.02–0.05:      linear 70→0
0.05–0.30:      0 (sweet spot)
0.30–0.80:      linear 0→80
> 0.80:         80 (over-cash)
```
Reports: cash percentage.

### Composite Formula
```
weighted_avg = 0.30×concentration + 0.25×sector + 0.20×volatility + 0.15×diversification + 0.10×cash
max_subscore = max(concentration, sector, volatility)  # structural risks only
overall = max(weighted_avg, 0.85 × max_subscore)
```
The 0.85× floor ensures a single severe structural risk can't be hidden by okay scores elsewhere.

### Triggers
1. After every trade (synchronous in trade response)
2. Daily cron at 4:30 PM ET
3. On-demand from UI

### Engine explanation
Templated, deterministic string — no LLM. Example:
```
Concentration risk: 100/100. 90% of portfolio is in NVDA.
Sector concentration: 100/100. 90% of portfolio is in Technology.
Overall risk score: 85/100.
Primary concern: extreme concentration in a single high-volatility stock.
```
AI interpretation layer (Gemini) narrates over this, constrained by the structured output.

### Not in MVP
- Correlation/covariance between holdings (best v2 upgrade — teaches "diversification is about correlation, not count")
- VaR (Value at Risk)
- Liquidity risk
- Geographic/currency exposure
