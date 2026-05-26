"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@/lib/format";
import { useApi } from "@/hooks/use-api";
import { usePortfolio } from "@/hooks/use-portfolio";
import { TradeDialog } from "@/components/trading/trade-dialog";
import { AIExplanation } from "@/components/stocks/ai-explanation";
import type { ApiResponse } from "@/types";

interface StockQuote {
  ticker: string;
  price: string;
  previous_close: string;
  change: string;
  change_pct: string;
  market_open: boolean;
  stale: boolean;
}

interface StockSnapshot {
  ticker: string;
  company_name: string;
  exchange: string | null;
  sector: string | null;
  instrument_type: string;
  snapshot: {
    last_price: string;
    previous_close: string;
    market_cap: number | null;
    pe_ratio: string | null;
    eps: string | null;
    beta: string | null;
    dividend_yield: string | null;
    week_52_high: string | null;
    week_52_low: string | null;
  } | null;
}

export default function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const api = useApi();
  const { data: portfolio } = usePortfolio();
  const [showTrade, setShowTrade] = useState(false);

  const { data: quote } = useQuery({
    queryKey: ["quote", ticker],
    queryFn: () =>
      api.get<ApiResponse<StockQuote>>(
        `/api/v1/stocks/${ticker.toUpperCase()}/quote`,
      ),
    select: (res) => res.data,
    refetchInterval: 5_000,
  });

  const { data: snapshot } = useQuery({
    queryKey: ["snapshot", ticker],
    queryFn: () =>
      api.get<ApiResponse<StockSnapshot>>(
        `/api/v1/stocks/${ticker.toUpperCase()}/snapshot`,
      ),
    select: (res) => res.data,
  });

  const change = quote ? parseFloat(quote.change) : 0;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{ticker.toUpperCase()}</h1>
          <p className="text-muted-foreground">
            {snapshot?.company_name ?? "Loading..."}
            {snapshot?.exchange && ` · ${snapshot.exchange}`}
          </p>
        </div>
        <button
          onClick={() => setShowTrade(true)}
          className="inline-flex h-10 items-center rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Trade
        </button>
      </div>

      {/* Price */}
      {quote && (
        <div>
          <p className="text-3xl font-bold tabular-nums">
            {formatCurrency(quote.price)}
          </p>
          <p
            className={cn(
              "text-sm font-medium tabular-nums",
              change > 0 && "text-green-600",
              change < 0 && "text-red-600",
            )}
          >
            {change >= 0 ? "+" : ""}
            {formatCurrency(quote.change)} ({formatPercent(quote.change_pct)})
          </p>
          {!quote.market_open && (
            <p className="text-xs text-yellow-600">Market closed</p>
          )}
          {quote.stale && (
            <p className="text-xs text-yellow-600">Live data delayed</p>
          )}
        </div>
      )}

      {/* Metrics grid */}
      {snapshot?.snapshot && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Market Cap" value={snapshot.snapshot.market_cap ? `$${(snapshot.snapshot.market_cap / 1e9).toFixed(1)}B` : "—"} />
          <Metric label="P/E Ratio" value={snapshot.snapshot.pe_ratio ?? "—"} />
          <Metric label="EPS" value={snapshot.snapshot.eps ? `$${snapshot.snapshot.eps}` : "—"} />
          <Metric label="Beta" value={snapshot.snapshot.beta ?? "—"} />
          <Metric label="Dividend Yield" value={snapshot.snapshot.dividend_yield ? `${(parseFloat(snapshot.snapshot.dividend_yield) * 100).toFixed(2)}%` : "—"} />
          <Metric label="52w High" value={snapshot.snapshot.week_52_high ? formatCurrency(snapshot.snapshot.week_52_high) : "—"} />
          <Metric label="52w Low" value={snapshot.snapshot.week_52_low ? formatCurrency(snapshot.snapshot.week_52_low) : "—"} />
          <Metric label="Sector" value={snapshot.sector ?? "—"} />
        </div>
      )}

      {/* AI Explanation */}
      <AIExplanation ticker={ticker.toUpperCase()} />

      {/* Trade dialog */}
      {showTrade && quote && (
        <TradeDialog
          ticker={ticker.toUpperCase()}
          currentPrice={quote.price}
          cashBalance={portfolio?.cash_balance ?? "0"}
          onClose={() => setShowTrade(false)}
        />
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium tabular-nums">{value}</p>
    </div>
  );
}
