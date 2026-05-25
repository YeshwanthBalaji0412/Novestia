# Novestia API Surface & Project Structure

Last updated: 2026-05-25

---

## API Design Conventions

### Base URL
All endpoints live under `/api/v1/`. Adding versioning now costs nothing; adding it later means renaming everything.

### Authentication
Every endpoint except `GET /health` requires a valid Clerk JWT in the `Authorization: Bearer <token>` header. A FastAPI dependency (`get_current_user`) validates the token, resolves to `users.id`, and injects the user object. No route handler ever touches the raw token.

### Response Shape

**Success:**
```json
{
  "data": { ... }
}
```
For paginated endpoints:
```json
{
  "data": [ ... ],
  "next_cursor": "opaque_string_or_null"
}
```

**Error:**
```json
{
  "error": {
    "code": "INSUFFICIENT_CASH",
    "message": "You need $4,500.00 but only have $1,200.00",
    "details": {}
  }
}
```

Standard HTTP status codes: 200 (success), 201 (created), 400 (bad request), 401 (unauthorized), 404 (not found), 422 (validation error), 429 (rate limit), 500 (server error).

### Pagination
Cursor-based for all list endpoints. Default `limit=20`, max `limit=100`. The cursor is an opaque base64-encoded string (typically the `id` or `executed_at` of the last item). Never offset-based — offset pagination degrades on large tables and produces inconsistent results when rows are inserted between pages.

### Money Format
All monetary values in responses are strings with 4 decimal places: `"1234.5600"`. This avoids JSON float precision issues. The frontend parses and formats for display. Requests accept either string or number.

### Timestamps
All timestamps are ISO 8601 with timezone: `"2026-05-25T14:30:00Z"`. Stored as `TIMESTAMPTZ` in Postgres, serialized as UTC in responses.

---

## Endpoints

### Health

#### `GET /health`
No auth. Used by Railway health checks and uptime monitoring.

**Response 200:**
```json
{
  "status": "ok",
  "timestamp": "2026-05-25T14:30:00Z"
}
```

---

### Users

#### `POST /api/v1/users/sync`
Called on every login from the frontend. Upserts the user record from the Clerk JWT claims. Idempotent — safe to call repeatedly. This is how a new Clerk user gets a row in our `users` table and a default portfolio.

**Request body:** None (user info extracted from JWT).

**Response 200:**
```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "User",
    "onboarded": false,
    "created_at": "2026-05-25T14:30:00Z"
  }
}
```

**Side effects on first call:**
- Creates `users` row
- Creates default `portfolios` row (cash_balance = 10000.0000, name = "Main Portfolio")
- Creates default empty `watchlists` row

#### `GET /api/v1/users/me`
Returns the current user's profile.

**Response 200:**
```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "User",
    "onboarded": true,
    "created_at": "2026-05-25T14:30:00Z",
    "portfolio_id": "uuid"
  }
}
```

#### `PATCH /api/v1/users/me`
Update display name or mark onboarding complete.

**Request body:**
```json
{
  "display_name": "Yeshwanth",
  "onboarded": true
}
```

**Response 200:** Same shape as `GET /api/v1/users/me`.

---

### Stocks & Market Data

#### `GET /api/v1/stocks/search?q=apple&limit=10`
Search stocks by ticker or company name. Hits Finnhub's symbol search endpoint, caches results in Redis for 1 hour. Returns matches sorted by relevance.

**Query params:**
- `q` (required): search query, min 1 character
- `limit` (optional): max results, default 10, max 25

**Response 200:**
```json
{
  "data": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "exchange": "NASDAQ",
      "instrument_type": "STOCK"
    }
  ]
}
```

#### `GET /api/v1/stocks/{ticker}`
Full stock profile: company info + current snapshot metrics. If the stock isn't in our `stocks` table yet, fetches from Finnhub and creates the record (lazy population).

**Response 200:**
```json
{
  "data": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "exchange": "NASDAQ",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "instrument_type": "STOCK",
    "currency": "USD",
    "snapshot": {
      "last_price": "187.4500",
      "previous_close": "185.2300",
      "daily_change": "2.2200",
      "daily_change_pct": "1.20",
      "market_cap": 2890000000000,
      "pe_ratio": "31.2400",
      "eps": "6.0100",
      "dividend_yield": "0.005200",
      "week_52_high": "199.6200",
      "week_52_low": "164.0800",
      "beta": "1.2400",
      "snapshot_taken_at": "2026-05-25T14:30:00Z"
    }
  }
}
```

#### `GET /api/v1/stocks/{ticker}/quote`
Lightweight price-only endpoint for widgets and quick lookups. Reads from Redis cache first, falls back to Finnhub REST if cache miss.

**Response 200:**
```json
{
  "data": {
    "ticker": "AAPL",
    "price": "187.4500",
    "previous_close": "185.2300",
    "change": "2.2200",
    "change_pct": "1.20",
    "stale": false,
    "market_open": true,
    "updated_at": "2026-05-25T14:30:00Z"
  }
}
```

The `stale` flag is `true` when the cached price is older than 30 seconds and a fresh fetch failed. The `market_open` flag tells the frontend whether to expect live streaming updates.

#### `GET /api/v1/stocks/{ticker}/history`
Price history for chart rendering. Leverages TimescaleDB `time_bucket` for efficient aggregation.

**Query params:**
- `range` (optional): `1D`, `1W`, `1M`, `3M`, `6M`, `1Y`, `ALL`. Default `1M`.
- `interval` (optional): `5min`, `1h`, `1d`. Default chosen automatically based on range.

Range-to-interval defaults:
| Range | Default Interval | Approx Points |
|-------|-----------------|---------------|
| 1D    | 5min            | ~78           |
| 1W    | 1h              | ~35           |
| 1M    | 1d              | ~22           |
| 3M    | 1d              | ~63           |
| 6M    | 1d              | ~126          |
| 1Y    | 1d              | ~252          |
| ALL   | 1d              | varies        |

**Response 200:**
```json
{
  "data": {
    "ticker": "AAPL",
    "range": "1M",
    "interval": "1d",
    "points": [
      {
        "timestamp": "2026-04-25T00:00:00Z",
        "open": "180.0000",
        "close": "181.5000",
        "high": "182.3000",
        "low": "179.1000",
        "volume": 54000000
      }
    ]
  }
}
```

For `5min` and `1h` intervals where we only store a single price per sample (not OHLC), all four price fields are the same value. This keeps the response shape consistent so the frontend chart component doesn't need conditional logic.

---

### Portfolio

#### `GET /api/v1/portfolio`
The main dashboard endpoint. Returns the full portfolio summary: cash, total value, all holdings with current market prices, overall daily change, and total return.

**Response 200:**
```json
{
  "data": {
    "id": "uuid",
    "name": "Main Portfolio",
    "cash_balance": "1200.0000",
    "total_value": "10450.0000",
    "starting_balance": "10000.0000",
    "total_return": "450.0000",
    "total_return_pct": "4.50",
    "daily_change": "125.0000",
    "daily_change_pct": "1.21",
    "holdings": [
      {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "quantity": "10.00000000",
        "average_cost": "180.0000",
        "current_price": "187.4500",
        "market_value": "1874.5000",
        "total_cost": "1800.0000",
        "unrealized_pnl": "74.5000",
        "unrealized_pnl_pct": "4.14",
        "daily_change": "22.2000",
        "daily_change_pct": "1.20",
        "weight": "17.94",
        "instrument_type": "STOCK",
        "sector": "Technology"
      }
    ],
    "holdings_count": 5
  }
}
```

Current prices for each holding are fetched from the Redis cache (populated by the WebSocket worker). `daily_change` per holding is computed from `current_price - previous_close`. Portfolio-level `daily_change` is the sum of all holding-level daily changes.

#### `GET /api/v1/portfolio/holdings/{ticker}`
Single holding detail with full P/L breakdown and transaction history for that ticker.

**Response 200:**
```json
{
  "data": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "quantity": "10.00000000",
    "average_cost": "180.0000",
    "current_price": "187.4500",
    "market_value": "1874.5000",
    "total_cost": "1800.0000",
    "unrealized_pnl": "74.5000",
    "unrealized_pnl_pct": "4.14",
    "first_purchased_at": "2026-04-15T10:30:00Z",
    "recent_transactions": [
      {
        "id": "uuid",
        "type": "BUY",
        "quantity": "5.00000000",
        "execution_price": "178.0000",
        "total_amount": "890.0000",
        "executed_after_hours": false,
        "journal_note": "Adding to position after earnings dip",
        "executed_at": "2026-05-20T11:15:00Z"
      }
    ]
  }
}
```

#### `POST /api/v1/portfolio/trade`
Execute a buy or sell. This is the endpoint that force-fetches a live price from Finnhub (Decision 1). The entire operation — price fetch, validation, transaction insert, holdings upsert, cash balance update — runs in a single database transaction.

**Request body:**
```json
{
  "ticker": "AAPL",
  "type": "BUY",
  "quantity": "5.00000000",
  "journal_note": "Buying the dip after earnings report"
}
```

`journal_note` is required — enforced by the UI, validated by the API. This is a core pedagogical feature: every trade requires a one-sentence reason.

**Validation rules:**
- `type` must be `BUY` or `SELL`
- `quantity` must be > 0, max 8 decimal places
- For `BUY`: `quantity × execution_price` must not exceed `cash_balance`
- For `SELL`: `quantity` must not exceed current holding quantity
- `ticker` must be a valid symbol (checked against Finnhub)
- `journal_note` must be 1–500 characters

**Response 201:**
```json
{
  "data": {
    "transaction": {
      "id": "uuid",
      "ticker": "AAPL",
      "type": "BUY",
      "quantity": "5.00000000",
      "execution_price": "187.4500",
      "total_amount": "937.2500",
      "realized_pnl": null,
      "executed_after_hours": false,
      "journal_note": "Buying the dip after earnings report",
      "executed_at": "2026-05-25T14:30:05Z"
    },
    "portfolio_after": {
      "cash_balance": "262.7500",
      "total_value": "10450.0000"
    },
    "holding_after": {
      "ticker": "AAPL",
      "quantity": "15.00000000",
      "average_cost": "179.3300"
    },
    "risk_score_after": 72
  }
}
```

The response includes the state *after* the trade so the frontend can update optimistically without re-fetching. `risk_score_after` is from the synchronous risk engine run (Trigger 1).

For sells, `realized_pnl` is populated:
```json
{
  "realized_pnl": "37.2500"
}
```

**Error examples:**
```json
{
  "error": {
    "code": "INSUFFICIENT_CASH",
    "message": "This trade costs $937.25 but you only have $200.00",
    "details": {
      "required": "937.2500",
      "available": "200.0000"
    }
  }
}
```
```json
{
  "error": {
    "code": "INSUFFICIENT_SHARES",
    "message": "You only hold 10 shares of AAPL but tried to sell 15",
    "details": {
      "held": "10.00000000",
      "requested": "15.00000000"
    }
  }
}
```
```json
{
  "error": {
    "code": "PRICE_UNAVAILABLE",
    "message": "Could not fetch current price for AAPL. Try again in a moment.",
    "details": {}
  }
}
```

#### `GET /api/v1/portfolio/transactions?limit=20&cursor=xxx`
Paginated transaction history, newest first.

**Query params:**
- `limit` (optional): default 20, max 100
- `cursor` (optional): opaque cursor from previous response
- `ticker` (optional): filter to a specific ticker

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "type": "BUY",
      "quantity": "5.00000000",
      "execution_price": "187.4500",
      "total_amount": "937.2500",
      "realized_pnl": null,
      "executed_after_hours": false,
      "journal_note": "Buying the dip after earnings report",
      "executed_at": "2026-05-25T14:30:05Z"
    }
  ],
  "next_cursor": "eyJpZCI6Ijc4OTAifQ=="
}
```

`next_cursor` is `null` when there are no more results.

#### `GET /api/v1/portfolio/performance`
Portfolio value over time for the performance chart. Computed from daily snapshots (a cron job stores one `portfolio_value` data point per day at market close).

**Query params:**
- `range` (optional): `1W`, `1M`, `3M`, `6M`, `1Y`, `ALL`. Default `1M`.

**Response 200:**
```json
{
  "data": {
    "starting_balance": "10000.0000",
    "current_value": "10450.0000",
    "total_return": "450.0000",
    "total_return_pct": "4.50",
    "points": [
      {
        "date": "2026-04-25",
        "value": "10120.0000"
      }
    ]
  }
}
```

This endpoint implies an additional table not in the core schema: **`portfolio_snapshots`** (`id`, `portfolio_id`, `total_value`, `cash_balance`, `recorded_at`). One row per portfolio per day, written by the daily cron. Lightweight and necessary for the performance chart.

---

### Watchlist

#### `GET /api/v1/watchlist`
All watchlist items with current prices (from Redis cache).

**Response 200:**
```json
{
  "data": [
    {
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "current_price": "687.4500",
      "previous_close": "680.0000",
      "daily_change": "7.4500",
      "daily_change_pct": "1.10",
      "added_at": "2026-05-20T09:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/watchlist/{ticker}`
Add a ticker to the watchlist. Idempotent — adding an already-watched ticker returns 200, not an error. Also triggers a WebSocket subscription for that ticker if not already subscribed.

**Response 201 (or 200 if already exists):**
```json
{
  "data": {
    "ticker": "NVDA",
    "added_at": "2026-05-25T14:30:00Z"
  }
}
```

#### `DELETE /api/v1/watchlist/{ticker}`
Remove a ticker. Returns 204 No Content on success. Returns 404 if the ticker wasn't in the watchlist.

---

### Journal

#### `GET /api/v1/journal?limit=20&cursor=xxx`
Paginated journal entries, newest first. Includes both trade-linked and standalone entries.

**Query params:**
- `limit` (optional): default 20, max 100
- `cursor` (optional): opaque cursor
- `type` (optional): `trade` (linked to transaction) or `reflection` (standalone)

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "content": "This week I learned that diversification isn't just about counting stocks...",
      "transaction_id": null,
      "transaction_summary": null,
      "created_at": "2026-05-24T20:00:00Z"
    },
    {
      "id": "uuid",
      "content": "Buying the dip after earnings report",
      "transaction_id": "uuid",
      "transaction_summary": {
        "ticker": "AAPL",
        "type": "BUY",
        "quantity": "5.00000000",
        "execution_price": "187.4500"
      },
      "created_at": "2026-05-25T14:30:05Z"
    }
  ],
  "next_cursor": "eyJpZCI6IjEyMzQifQ=="
}
```

#### `POST /api/v1/journal`
Create a standalone journal entry (not linked to a trade). Trade-linked journal entries are created automatically via the trade endpoint.

**Request body:**
```json
{
  "content": "This week I learned that diversification isn't just about counting stocks..."
}
```

`content` must be 1–2000 characters.

**Response 201:**
```json
{
  "data": {
    "id": "uuid",
    "content": "This week I learned that diversification isn't just about counting stocks...",
    "transaction_id": null,
    "created_at": "2026-05-24T20:00:00Z"
  }
}
```

#### `GET /api/v1/journal/{id}`
Single journal entry by ID. Returns 404 if not found or not owned by the current user.

**Response 200:** Same shape as a single item in the list response.

---

### Risk

#### `GET /api/v1/risk/latest`
Most recent risk report for the user's portfolio. If none exists yet, computes one on the fly and stores it.

**Response 200:**
```json
{
  "data": {
    "id": "uuid",
    "overall_score": 85,
    "subscores": {
      "concentration": {
        "score": 100,
        "explanation": "90% of portfolio is in NVDA."
      },
      "sector_concentration": {
        "score": 100,
        "explanation": "90% of portfolio is in Technology."
      },
      "volatility": {
        "score": 53,
        "explanation": "Portfolio beta is 1.53, well above the market."
      },
      "diversification": {
        "score": 84,
        "explanation": "You hold 1 position. No ETF exposure."
      },
      "cash_ratio": {
        "score": 0,
        "explanation": "10% cash is within healthy range."
      }
    },
    "engine_explanation": "Concentration risk: 100/100. 90% of portfolio is in NVDA.\nSector concentration: 100/100. 90% of portfolio is in Technology.\nVolatility: 53/100. Portfolio beta is 1.53, well above the market.\nDiversification: 84/100. You hold 1 position. No ETF exposure.\nCash ratio: 0/100. 10% cash is within healthy range.\n\nOverall risk score: 85/100.\nPrimary concern: extreme concentration in a single high-volatility stock.",
    "ai_interpretation": "Your portfolio is heavily concentrated in a single tech stock. Think of it like putting most of your eggs in one basket — if NVDA drops 20%, your entire portfolio drops 18%. Consider spreading your investments across different sectors and adding a broad-market ETF like VOO to reduce risk.",
    "computed_at": "2026-05-25T14:30:00Z"
  }
}
```

#### `GET /api/v1/risk/history?limit=30`
Risk score over time for the risk trend chart. Returns the composite score per report, not the full subscore breakdown (that would be too heavy for a chart endpoint).

**Query params:**
- `limit` (optional): default 30, max 90

**Response 200:**
```json
{
  "data": [
    {
      "overall_score": 85,
      "computed_at": "2026-05-25T14:30:00Z"
    },
    {
      "overall_score": 72,
      "computed_at": "2026-05-24T16:30:00Z"
    }
  ]
}
```

#### `POST /api/v1/risk/compute`
Trigger a fresh risk computation. Returns the new report. Rate limited to 1 call per minute per user.

**Request body:** None.

**Response 201:** Same shape as `GET /api/v1/risk/latest`.

---

### AI Explanations

#### `GET /api/v1/ai/explain/stock/{ticker}`
AI-generated beginner-friendly explanation of a stock. Cached by `(ticker, prompt_version)` in `ai_explanations` table. Cache TTL: 24 hours.

**Response 200:**
```json
{
  "data": {
    "ticker": "AAPL",
    "explanation": "Apple is one of the world's largest companies, known for the iPhone, Mac, and a growing services business. It's considered a 'blue chip' stock — a large, stable, well-established company. Its P/E ratio of 31 means investors are paying $31 for every $1 of earnings, which is above the market average of ~22, reflecting high growth expectations.",
    "cached": true,
    "generated_at": "2026-05-25T10:00:00Z"
  }
}
```

#### `GET /api/v1/ai/explain/metric?name=pe_ratio&ticker=AAPL`
Explain a specific financial metric in the context of a particular stock. This is the "?" button next to each metric on the stock detail page.

**Query params:**
- `name` (required): one of `pe_ratio`, `eps`, `market_cap`, `beta`, `dividend_yield`, `week_52_high`, `week_52_low`, `expense_ratio`
- `ticker` (optional): if provided, explanation is contextualized to this stock

**Response 200:**
```json
{
  "data": {
    "metric": "pe_ratio",
    "ticker": "AAPL",
    "explanation": "The P/E (Price-to-Earnings) ratio tells you how much investors are paying for each dollar of a company's earnings. Apple's P/E of 31 means investors pay $31 for every $1 Apple earns. The S&P 500 average is about 22, so Apple is priced at a premium — investors expect its earnings to grow faster than average.",
    "cached": true,
    "generated_at": "2026-05-25T10:00:00Z"
  }
}
```

#### `GET /api/v1/ai/interpret/risk`
AI-generated beginner narrative of the current risk report. Takes the engine's templated `engine_explanation` as input and produces a conversational interpretation. Cached per `(portfolio_id, risk_report_id, prompt_version)`.

**Response 200:**
```json
{
  "data": {
    "risk_report_id": "uuid",
    "interpretation": "Your portfolio is heavily concentrated in a single tech stock...",
    "suggestions": [
      "Consider adding a broad-market ETF like VOO or VTI to instantly diversify across 500+ stocks.",
      "Your Technology sector exposure is very high. Look into other sectors like Healthcare (XLV) or Consumer Staples (XLP).",
      "Keep 5-15% of your portfolio in cash so you can take advantage of buying opportunities."
    ],
    "cached": true,
    "generated_at": "2026-05-25T14:35:00Z"
  }
}
```

---

### WebSocket Protocol

#### Connection: `wss://{host}/api/v1/ws?token={clerk_jwt}`

Authentication via query parameter (WebSocket doesn't support custom headers in the browser). The JWT is validated on connection open; invalid tokens get an immediate close frame with code 4001.

#### Client → Server Messages

**Subscribe to tickers:**
```json
{
  "action": "subscribe",
  "tickers": ["AAPL", "NVDA"]
}
```

**Unsubscribe from tickers:**
```json
{
  "action": "unsubscribe",
  "tickers": ["NVDA"]
}
```

On initial connection, the server auto-subscribes to the user's portfolio holdings + watchlist tickers. The client only needs to send explicit subscribe/unsubscribe for additional tickers (e.g., when viewing a stock detail page).

#### Server → Client Messages

**Price update:**
```json
{
  "type": "price",
  "ticker": "AAPL",
  "price": "187.4500",
  "change": "2.2200",
  "change_pct": "1.20",
  "timestamp": "2026-05-25T14:30:05Z"
}
```

**Connection status:**
```json
{
  "type": "status",
  "connected": true,
  "subscribed_tickers": ["AAPL", "NVDA", "VOO"],
  "market_open": true
}
```

Sent on initial connection and whenever the subscription set changes.

**Data delay warning:**
```json
{
  "type": "warning",
  "code": "STALE_DATA",
  "message": "Live data delayed — reconnecting to data provider"
}
```

Sent when the worker hasn't published updates for 30+ seconds (Finnhub disconnect).

#### Heartbeat
Server sends a ping frame every 30 seconds. Client must respond with pong. If three consecutive pings go unanswered, the server closes the connection. The frontend's `useWebSocket` hook handles automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, max 30s).

#### Connection Lifecycle
1. Client connects with JWT → server validates
2. Server fetches user's holdings + watchlist tickers from Postgres
3. Server subscribes to corresponding Redis pub/sub channels
4. Server sends initial `status` message with subscription set
5. Price updates flow as Redis publishes them
6. Client navigates to stock detail → sends `subscribe` → server adds channel
7. Client navigates away → sends `unsubscribe` → server drops channel (unless ticker is in portfolio/watchlist)
8. Client disconnects → server decrements refcounts, cleans up Redis subscriptions

---

## Additional Table: portfolio_snapshots

Discovered during API design — needed for the performance chart endpoint.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `portfolio_id` | UUID, FK → portfolios.id, NOT NULL | |
| `total_value` | NUMERIC(18,4), NOT NULL | Cash + market value of all holdings |
| `cash_balance` | NUMERIC(18,4), NOT NULL | Snapshot of cash at that moment |
| `recorded_at` | TIMESTAMPTZ, NOT NULL | |

Index: `(portfolio_id, recorded_at DESC)`.

Written by the daily cron job at 4:30 PM ET (same job that computes risk reports). One row per portfolio per day.

---

## Project Structure

### Monorepo Layout

```
novestia/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, CORS, lifespan events
│   │   ├── config.py                  # pydantic-settings: env vars, Finnhub key, DB URL, etc.
│   │   ├── database.py                # SQLAlchemy async engine + sessionmaker
│   │   ├── redis.py                   # Redis client (aioredis)
│   │   ├── dependencies.py            # get_current_user, get_db, get_redis
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # Aggregates all route modules into one router
│   │   │       ├── users.py           # POST /sync, GET /me, PATCH /me
│   │   │       ├── stocks.py          # GET /search, GET /{ticker}, GET /quote, GET /history
│   │   │       ├── portfolio.py       # GET /, GET /holdings/{ticker}, POST /trade, GET /transactions, GET /performance
│   │   │       ├── watchlist.py       # GET /, POST /{ticker}, DELETE /{ticker}
│   │   │       ├── journal.py         # GET /, POST /, GET /{id}
│   │   │       ├── risk.py            # GET /latest, GET /history, POST /compute
│   │   │       ├── ai.py              # GET /explain/stock, GET /explain/metric, GET /interpret/risk
│   │   │       └── ws.py              # WebSocket /ws endpoint
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── __init__.py            # Re-exports all models for Alembic
│   │   │   ├── user.py                # User
│   │   │   ├── portfolio.py           # Portfolio, Holding, Transaction, PortfolioSnapshot
│   │   │   ├── market.py              # Stock, StockSnapshot, PriceHistory
│   │   │   ├── journal.py             # JournalEntry
│   │   │   ├── risk.py                # RiskReport
│   │   │   ├── ai.py                  # AIExplanation
│   │   │   └── system.py              # APICallLog
│   │   │
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── common.py             # ErrorResponse, PaginatedResponse, etc.
│   │   │   ├── user.py
│   │   │   ├── stock.py
│   │   │   ├── portfolio.py           # TradeRequest, TradeResponse, PortfolioSummary, etc.
│   │   │   ├── watchlist.py
│   │   │   ├── journal.py
│   │   │   ├── risk.py
│   │   │   └── ai.py
│   │   │
│   │   ├── services/                  # Business logic (no HTTP concerns)
│   │   │   ├── __init__.py
│   │   │   ├── finnhub.py             # Finnhub REST client (quote, search, profile)
│   │   │   ├── trade.py               # Trade execution: price fetch → validate → transact
│   │   │   ├── risk_engine.py         # All 5 subscores + composite formula
│   │   │   ├── ai_service.py          # Gemini API calls + cache layer
│   │   │   ├── price_cache.py         # Redis read/write for cached prices
│   │   │   └── market_hours.py        # Is market open? After-hours detection, timezone handling
│   │   │
│   │   └── worker/                    # Separate process(es)
│   │       ├── __init__.py
│   │       ├── price_streamer.py      # Finnhub WebSocket → Redis pub/sub + cache + sampled DB writes
│   │       └── cron.py                # Daily: snapshot refresh, risk recompute, portfolio snapshots
│   │
│   ├── alembic/                       # Database migrations
│   │   ├── env.py
│   │   └── versions/                  # Migration files
│   ├── alembic.ini
│   │
│   ├── tests/
│   │   ├── conftest.py                # Test DB, fixtures, test client
│   │   ├── test_risk_engine.py        # Unit tests for every subscore + composite
│   │   ├── test_trade.py              # Trade execution logic
│   │   ├── test_market_hours.py       # Timezone edge cases
│   │   └── test_api/                  # Integration tests per endpoint group
│   │       ├── test_portfolio.py
│   │       ├── test_stocks.py
│   │       └── ...
│   │
│   ├── pyproject.toml                 # Python project config, dependencies
│   └── requirements.txt               # Pinned dependencies for deployment
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout: fonts, metadata, providers
│   │   ├── page.tsx                   # Landing page (unauthenticated)
│   │   │
│   │   ├── (auth)/                    # Clerk auth pages (public)
│   │   │   ├── sign-in/
│   │   │   │   └── [[...sign-in]]/page.tsx
│   │   │   └── sign-up/
│   │   │       └── [[...sign-up]]/page.tsx
│   │   │
│   │   └── (app)/                     # Protected routes (authenticated)
│   │       ├── layout.tsx             # App shell: sidebar, top nav, WebSocket provider
│   │       ├── dashboard/
│   │       │   └── page.tsx           # Portfolio summary, holdings, watchlist, risk gauge
│   │       ├── portfolio/
│   │       │   ├── page.tsx           # Full holdings list + transaction history
│   │       │   └── [ticker]/
│   │       │       └── page.tsx       # Single holding detail + per-ticker transactions
│   │       ├── explore/
│   │       │   └── page.tsx           # Stock search + discovery
│   │       ├── stocks/
│   │       │   └── [ticker]/
│   │       │       └── page.tsx       # Stock detail: chart, metrics, AI explanation, trade form
│   │       ├── watchlist/
│   │       │   └── page.tsx           # Watchlist management
│   │       ├── journal/
│   │       │   ├── page.tsx           # All journal entries
│   │       │   └── new/
│   │       │       └── page.tsx       # Standalone journal entry form
│   │       ├── risk/
│   │       │   └── page.tsx           # Full risk report + subscores + history chart
│   │       └── settings/
│   │           └── page.tsx           # User settings, reset portfolio
│   │
│   ├── components/
│   │   ├── ui/                        # shadcn/ui primitives (button, card, dialog, etc.)
│   │   │
│   │   ├── layout/
│   │   │   ├── sidebar.tsx            # Desktop sidebar navigation
│   │   │   ├── top-nav.tsx            # Top bar: search, user menu
│   │   │   └── mobile-nav.tsx         # Bottom tab bar for mobile
│   │   │
│   │   ├── dashboard/
│   │   │   ├── portfolio-summary-card.tsx   # Total value, return, daily change
│   │   │   ├── holdings-table.tsx           # Sortable table of current holdings
│   │   │   ├── watchlist-widget.tsx          # Compact watchlist with live prices
│   │   │   └── risk-gauge.tsx               # Visual risk score (radial gauge)
│   │   │
│   │   ├── trading/
│   │   │   ├── trade-form.tsx               # Buy/sell form with quantity, journal note
│   │   │   ├── trade-confirmation-dialog.tsx # Confirmation with execution price
│   │   │   └── after-hours-banner.tsx       # "After-hours simulation" warning
│   │   │
│   │   ├── stocks/
│   │   │   ├── price-chart.tsx              # Interactive price chart (Recharts or Lightweight Charts)
│   │   │   ├── stock-header.tsx             # Ticker, name, live price, daily change
│   │   │   ├── metrics-grid.tsx             # P/E, EPS, beta, etc. with "?" AI explain buttons
│   │   │   ├── search-command.tsx           # Command palette style search (cmdk)
│   │   │   └── ticker-pill.tsx              # Small ticker badge with price
│   │   │
│   │   ├── risk/
│   │   │   ├── risk-score-card.tsx          # Overall score with color gradient
│   │   │   ├── subscore-breakdown.tsx       # Five subscores with bar charts
│   │   │   ├── risk-history-chart.tsx       # Score over time line chart
│   │   │   └── ai-interpretation.tsx        # Gemini-generated narrative
│   │   │
│   │   └── journal/
│   │       ├── journal-entry-card.tsx       # Single entry display
│   │       └── journal-form.tsx             # New entry textarea
│   │
│   ├── hooks/
│   │   ├── use-websocket.ts                 # WebSocket connection management + reconnection
│   │   ├── use-price-subscription.ts        # Subscribe/unsub to tickers, returns live prices
│   │   ├── use-portfolio.ts                 # Fetch + cache portfolio data (SWR/React Query)
│   │   ├── use-debounce.ts                  # Debounce for search input
│   │   └── use-market-status.ts             # Is market open? Countdown to open/close
│   │
│   ├── lib/
│   │   ├── api.ts                           # Fetch wrapper: base URL, auth header injection, error handling
│   │   ├── utils.ts                         # cn() helper, misc
│   │   ├── format.ts                        # formatCurrency, formatPercent, formatNumber, formatDate
│   │   └── constants.ts                     # API base URL, market hours, default starting balance
│   │
│   ├── types/
│   │   └── index.ts                         # All shared TypeScript interfaces (mirroring Pydantic schemas)
│   │
│   ├── providers/
│   │   ├── clerk-provider.tsx               # ClerkProvider wrapper
│   │   ├── query-provider.tsx               # React Query / SWR provider
│   │   └── websocket-provider.tsx           # WebSocket context provider
│   │
│   ├── public/
│   │   └── ...                              # Static assets
│   │
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── components.json                      # shadcn/ui config
│   └── package.json
│
├── docs/
│   ├── api-surface.md                       # This document
│   └── design-decisions.md                  # Architecture decisions, data model, risk engine
│
├── docker-compose.yml                       # Local dev: Postgres + TimescaleDB + Redis
├── .env.example                             # Template for required env vars
├── .gitignore
└── README.md
```

### Key structural decisions

**Why `services/` separate from `api/`:** Route handlers in `api/v1/` should be thin — parse request, call service, return response. All business logic (trade execution, risk computation, Finnhub communication) lives in `services/`. This makes services independently testable without HTTP and reusable across routes (e.g., the trade service calls the risk engine service).

**Why `models/` and `schemas/` are separate:** `models/` are SQLAlchemy ORM classes (database shape). `schemas/` are Pydantic classes (API shape). They look similar but serve different purposes and diverge quickly — a `Portfolio` model has SQLAlchemy relationships, while a `PortfolioSummary` schema has computed fields like `total_return_pct` that don't exist in the database.

**Why `worker/` is inside `app/` but runs as a separate process:** The worker shares models, config, and the Redis client with the API server. Keeping it in the same package avoids duplication. It runs via a separate entrypoint: `python -m app.worker.price_streamer` vs `uvicorn app.main:app`.

**Why `(app)/` route group in Next.js:** The parenthesized route group `(app)` shares a layout (sidebar, nav, WebSocket provider) without adding a URL segment. All authenticated pages get the app shell automatically. `(auth)` pages get a clean centered layout.

**Why `hooks/use-price-subscription.ts` is the critical frontend piece:** This hook is what makes the dynamic WebSocket subscription model (Decision 3) ergonomic. A component declares `const prices = usePriceSubscription(["AAPL", "NVDA"])` and the hook handles subscribe on mount, unsubscribe on unmount, and returns a reactive map of ticker → latest price. The component never thinks about WebSocket lifecycle.

---

## Environment Variables

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/novestia
REDIS_URL=redis://localhost:6379/0
FINNHUB_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
CLERK_SECRET_KEY=your_key_here
CLERK_PUBLISHABLE_KEY=your_key_here
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_key_here
CLERK_SECRET_KEY=your_key_here
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
```

---

## Docker Compose (Local Development)

```yaml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: novestia
      POSTGRES_PASSWORD: novestia
      POSTGRES_DB: novestia
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

The backend and frontend run directly on the host during development (not containerized) for fast iteration and hot reload. Only the infrastructure services (Postgres/TimescaleDB + Redis) run in Docker.

---

## Endpoint Summary Table

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/api/v1/users/sync` | Yes | Upsert user from Clerk JWT |
| GET | `/api/v1/users/me` | Yes | Current user profile |
| PATCH | `/api/v1/users/me` | Yes | Update profile |
| GET | `/api/v1/stocks/search` | Yes | Search stocks by name/ticker |
| GET | `/api/v1/stocks/{ticker}` | Yes | Full stock profile + snapshot |
| GET | `/api/v1/stocks/{ticker}/quote` | Yes | Current price only |
| GET | `/api/v1/stocks/{ticker}/history` | Yes | Price history for charts |
| GET | `/api/v1/portfolio` | Yes | Full portfolio summary |
| GET | `/api/v1/portfolio/holdings/{ticker}` | Yes | Single holding detail |
| POST | `/api/v1/portfolio/trade` | Yes | Execute buy/sell |
| GET | `/api/v1/portfolio/transactions` | Yes | Transaction history (paginated) |
| GET | `/api/v1/portfolio/performance` | Yes | Portfolio value over time |
| GET | `/api/v1/watchlist` | Yes | All watchlist items |
| POST | `/api/v1/watchlist/{ticker}` | Yes | Add to watchlist |
| DELETE | `/api/v1/watchlist/{ticker}` | Yes | Remove from watchlist |
| GET | `/api/v1/journal` | Yes | Journal entries (paginated) |
| POST | `/api/v1/journal` | Yes | Create standalone entry |
| GET | `/api/v1/journal/{id}` | Yes | Single journal entry |
| GET | `/api/v1/risk/latest` | Yes | Latest risk report |
| GET | `/api/v1/risk/history` | Yes | Risk score over time |
| POST | `/api/v1/risk/compute` | Yes | Trigger fresh risk computation |
| GET | `/api/v1/ai/explain/stock/{ticker}` | Yes | AI stock explanation |
| GET | `/api/v1/ai/explain/metric` | Yes | AI metric explanation |
| GET | `/api/v1/ai/interpret/risk` | Yes | AI risk interpretation |
| WS | `/api/v1/ws` | Yes | Live price streaming |

**Total: 22 REST endpoints + 1 WebSocket endpoint.**
