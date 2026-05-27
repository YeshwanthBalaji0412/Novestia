"use client";

import { formatCurrency, formatPercent, getDeltaColor } from "@/lib/format";
import { KpiCard } from "@/components/common/kpi-card";
import type { HoldingSummary, PortfolioSummary } from "@/types";

interface Props {
  portfolio: PortfolioSummary;
  loading?: boolean;
}

function findBestWorst(holdings: HoldingSummary[]) {
  if (holdings.length === 0) return { best: null, worst: null };

  let best = holdings[0]!;
  let worst = holdings[0]!;

  for (const h of holdings) {
    const pct = parseFloat(h.daily_change_pct);
    if (pct > parseFloat(best.daily_change_pct)) best = h;
    if (pct < parseFloat(worst.daily_change_pct)) worst = h;
  }

  return { best, worst };
}

export function PortfolioSummaryCard({ portfolio, loading }: Props) {
  const totalReturn = parseFloat(portfolio.total_return);
  const dailyChange = parseFloat(portfolio.daily_change);
  const { best, worst } = findBestWorst(portfolio.holdings);

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <KpiCard
        label="Total Value"
        value={formatCurrency(portfolio.total_value)}
        loading={loading}
        index={0}
      />
      <KpiCard
        label="Cash Available"
        value={formatCurrency(portfolio.cash_balance)}
        loading={loading}
        index={1}
      />
      <KpiCard
        label="Total Return"
        value={formatCurrency(Math.abs(totalReturn))}
        delta={formatPercent(portfolio.total_return_pct)}
        accent={getDeltaColor(totalReturn)}
        loading={loading}
        index={2}
      />
      <KpiCard
        label="Today"
        value={formatCurrency(Math.abs(dailyChange))}
        delta={formatPercent(portfolio.daily_change_pct)}
        accent={getDeltaColor(dailyChange)}
        loading={loading}
        index={3}
      />
      <KpiCard
        label="Best Today"
        value={best ? best.ticker : "—"}
        delta={best ? formatPercent(best.daily_change_pct) : undefined}
        accent={best ? "positive" : undefined}
        loading={loading}
        index={4}
      />
      <KpiCard
        label="Worst Today"
        value={worst ? worst.ticker : "—"}
        delta={worst ? formatPercent(worst.daily_change_pct) : undefined}
        accent={worst ? "negative" : undefined}
        loading={loading}
        index={5}
      />
    </div>
  );
}
