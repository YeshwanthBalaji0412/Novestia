"use client";

import { formatCurrency, getDeltaColor } from "@/lib/format";
import { KpiCard } from "@/components/common/kpi-card";
import type { PortfolioSummary } from "@/types";

interface Props {
  portfolio: PortfolioSummary;
}

export function CostBasisSummary({ portfolio }: Props) {
  // Total invested = starting_balance - current_cash (rough approximation)
  const totalInvested =
    parseFloat(portfolio.starting_balance) - parseFloat(portfolio.cash_balance);
  const unrealizedPnl = parseFloat(portfolio.total_return);

  return (
    <div className="glass-card p-4">
      <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        Cost Basis Summary
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard
          label="Deployed Capital"
          value={formatCurrency(Math.max(totalInvested, 0))}
          index={0}
        />
        <KpiCard
          label="Unrealized P/L"
          value={formatCurrency(Math.abs(unrealizedPnl))}
          accent={getDeltaColor(unrealizedPnl)}
          index={1}
        />
        <KpiCard
          label="Starting Balance"
          value={formatCurrency(portfolio.starting_balance)}
          index={2}
        />
      </div>
    </div>
  );
}
