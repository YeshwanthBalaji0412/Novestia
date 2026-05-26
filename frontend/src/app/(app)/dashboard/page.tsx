"use client";

import { useUserSync } from "@/hooks/use-user-sync";
import { usePortfolio } from "@/hooks/use-portfolio";
import { useWatchlist } from "@/hooks/use-watchlist";
import { useRisk } from "@/hooks/use-risk";
import { PortfolioSummaryCard } from "@/components/portfolio/portfolio-summary-card";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { RiskScoreCard } from "@/components/risk/risk-score-card";

export default function DashboardPage() {
  const { data: user, isLoading: userLoading } = useUserSync();
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: watchlistItems, isLoading: watchlistLoading } = useWatchlist();
  const { data: risk } = useRisk();

  if (userLoading || portfolioLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-bold">
        {user?.display_name
          ? `Welcome back, ${user.display_name}`
          : "Dashboard"}
      </h1>

      {portfolio && <PortfolioSummaryCard portfolio={portfolio} />}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Holdings</h2>
          <HoldingsTable holdings={portfolio?.holdings ?? []} />
        </div>
        <div className="space-y-6">
          {risk && <RiskScoreCard score={risk.overall_score} />}
          <div>
            <h2 className="mb-3 text-lg font-semibold">Watchlist</h2>
            {watchlistLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : (
              <WatchlistTable items={watchlistItems ?? []} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
