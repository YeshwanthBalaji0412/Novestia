"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { usePortfolio, usePerformance } from "@/hooks/use-portfolio";
import { PageHeader } from "@/components/layout/page-header";
import { PortfolioSummaryCard } from "@/components/portfolio/portfolio-summary-card";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { PerformanceChart } from "@/components/portfolio/performance-chart";
import { SectorDonut } from "@/components/portfolio/sector-donut";
import { CostBasisSummary } from "@/components/portfolio/cost-basis-summary";
import { EmptyState } from "@/components/common/empty-state";
import { PageSkeleton } from "@/components/common/skeleton";

const RANGES = ["1W", "1M", "3M", "6M", "1Y", "ALL"] as const;

export default function PortfolioPage() {
  const [range, setRange] = useState<string>("1M");
  const { data: portfolio, isLoading, error } = usePortfolio();
  const { data: performance } = usePerformance(range);

  if (isLoading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState icon="⚠" title="Failed to load portfolio" action={
          <button onClick={() => window.location.reload()} className="glass-card px-4 py-2 text-xs font-semibold uppercase tracking-wider text-primary">Retry</button>
        } />
      </div>
    );
  }

  const cashPct = portfolio
    ? (parseFloat(portfolio.cash_balance) / parseFloat(portfolio.total_value)) * 100
    : 0;

  return (
    <div className="flex flex-1 flex-col gap-5 p-4 sm:p-6">
      <PageHeader title="Portfolio" />
      {portfolio && <PortfolioSummaryCard portfolio={portfolio} />}

      {/* Performance chart with range selector */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
            Performance
          </p>
          <div className="flex gap-1">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider transition-all",
                  range === r
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <PerformanceChart points={performance?.points ?? []} />
      </div>

      {/* Allocation + Cost Basis */}
      {portfolio && portfolio.holdings.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          <SectorDonut holdings={portfolio.holdings} cashPercent={cashPct} />
          <CostBasisSummary portfolio={portfolio} />
        </div>
      )}

      {/* Holdings */}
      <div>
        <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          All Holdings
        </p>
        <HoldingsTable holdings={portfolio?.holdings ?? []} />
      </div>
    </div>
  );
}
