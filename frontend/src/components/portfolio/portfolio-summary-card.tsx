"use client";

import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@/lib/format";
import type { PortfolioSummary } from "@/types";

interface Props {
  portfolio: PortfolioSummary;
}

export function PortfolioSummaryCard({ portfolio }: Props) {
  const totalReturn = parseFloat(portfolio.total_return);
  const dailyChange = parseFloat(portfolio.daily_change);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card label="Total Value" value={formatCurrency(portfolio.total_value)} />
      <Card
        label="Cash Balance"
        value={formatCurrency(portfolio.cash_balance)}
      />
      <Card
        label="Total Return"
        value={formatCurrency(Math.abs(totalReturn))}
        sub={formatPercent(portfolio.total_return_pct)}
        positive={totalReturn >= 0}
      />
      <Card
        label="Today's Change"
        value={formatCurrency(Math.abs(dailyChange))}
        sub={formatPercent(portfolio.daily_change_pct)}
        positive={dailyChange >= 0}
      />
    </div>
  );
}

function Card({
  label,
  value,
  sub,
  positive,
}: {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums">{value}</p>
      {sub && (
        <p
          className={cn(
            "mt-1 text-sm font-medium tabular-nums",
            positive === true && "text-green-600",
            positive === false && "text-red-600",
          )}
        >
          {positive ? "+" : "-"}
          {value} ({sub})
        </p>
      )}
    </div>
  );
}
