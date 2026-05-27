"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
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
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-heading text-2xl font-bold sm:text-3xl">
              {ticker.toUpperCase()}
            </h1>
            {snapshot?.instrument_type && (
              <span className="rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-[9px] uppercase tracking-wider text-muted-foreground">
                {snapshot.instrument_type}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {snapshot?.company_name ?? "Loading..."}
            {snapshot?.exchange && ` · ${snapshot.exchange}`}
          </p>
        </div>
        <button
          onClick={() => setShowTrade(true)}
          className="inline-flex h-10 items-center rounded-lg bg-primary px-6 text-sm font-semibold text-primary-foreground transition-all hover:brightness-110 hover:shadow-[0_0_20px_oklch(0.7_0.18_240_/_0.3)]"
        >
          Trade
        </button>
      </div>

      {/* Price */}
      {quote && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <p className="font-numbers text-4xl font-bold leading-none sm:text-5xl">
            {formatCurrency(quote.price)}
          </p>
          <p
            className={cn(
              "mt-2 font-numbers text-sm font-semibold",
              change > 0 && "text-gain",
              change < 0 && "text-loss",
            )}
          >
            {change >= 0 ? "+" : ""}
            {formatCurrency(quote.change)} ({formatPercent(quote.change_pct)})
          </p>
          <div className="mt-1 flex gap-2">
            {!quote.market_open && (
              <span className="text-[10px] uppercase tracking-wider text-warning">
                Market Closed
              </span>
            )}
            {quote.stale && (
              <span className="text-[10px] uppercase tracking-wider text-warning">
                Delayed
              </span>
            )}
          </div>
        </motion.div>
      )}

      {/* Metrics grid */}
      {snapshot?.snapshot && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Market Cap"
            value={
              snapshot.snapshot.market_cap
                ? `$${(snapshot.snapshot.market_cap / 1e9).toFixed(1)}B`
                : "—"
            }
            i={0}
          />
          <MetricCard label="P/E Ratio" value={snapshot.snapshot.pe_ratio ?? "—"} i={1} />
          <MetricCard
            label="EPS"
            value={snapshot.snapshot.eps ? `$${snapshot.snapshot.eps}` : "—"}
            i={2}
          />
          <MetricCard label="Beta" value={snapshot.snapshot.beta ?? "—"} i={3} />
          <MetricCard
            label="Div. Yield"
            value={
              snapshot.snapshot.dividend_yield
                ? `${(parseFloat(snapshot.snapshot.dividend_yield) * 100).toFixed(2)}%`
                : "—"
            }
            i={4}
          />
          <MetricCard
            label="52w High"
            value={
              snapshot.snapshot.week_52_high
                ? formatCurrency(snapshot.snapshot.week_52_high)
                : "—"
            }
            i={5}
          />
          <MetricCard
            label="52w Low"
            value={
              snapshot.snapshot.week_52_low
                ? formatCurrency(snapshot.snapshot.week_52_low)
                : "—"
            }
            i={6}
          />
          <MetricCard label="Sector" value={snapshot.sector ?? "—"} i={7} />
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

function MetricCard({ label, value, i }: { label: string; value: string; i: number }) {
  return (
    <motion.div
      className="glass-card hud-corners p-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: i * 0.05 }}
    >
      <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 font-numbers text-sm font-medium">{value}</p>
    </motion.div>
  );
}
