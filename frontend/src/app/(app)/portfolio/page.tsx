"use client";

import { usePortfolio, usePerformance } from "@/hooks/use-portfolio";
import { PortfolioSummaryCard } from "@/components/portfolio/portfolio-summary-card";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { PerformanceChart } from "@/components/portfolio/performance-chart";

export default function PortfolioPage() {
  const { data: portfolio, isLoading } = usePortfolio();
  const { data: performance } = usePerformance("1M");

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-bold">Portfolio</h1>

      {portfolio && <PortfolioSummaryCard portfolio={portfolio} />}

      <div>
        <h2 className="mb-3 text-lg font-semibold">Performance</h2>
        <PerformanceChart points={performance?.points ?? []} />
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold">All Holdings</h2>
        <HoldingsTable holdings={portfolio?.holdings ?? []} />
      </div>
    </div>
  );
}
