"use client";

import { useUserSync } from "@/hooks/use-user-sync";
import { usePortfolio } from "@/hooks/use-portfolio";
import { useWatchlist } from "@/hooks/use-watchlist";
import { useRisk } from "@/hooks/use-risk";
import { PortfolioSummaryCard } from "@/components/portfolio/portfolio-summary-card";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { RiskScoreCard } from "@/components/risk/risk-score-card";
import { PageSkeleton } from "@/components/common/skeleton";

export default function DashboardPage() {
  const { data: user, isLoading: userLoading } = useUserSync();
  const { data: portfolio, isLoading: portfolioLoading, error } = usePortfolio();
  const { data: watchlistItems, isLoading: watchlistLoading } = useWatchlist();
  const { data: risk } = useRisk();

  if (userLoading || portfolioLoading) {
    return <PageSkeleton />;
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="text-center">
          <p className="text-destructive">Failed to load portfolio.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-sm text-primary hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 sm:gap-6 sm:p-6">
      <h1 className="text-xl font-bold sm:text-2xl">
        {user?.display_name
          ? `Welcome back, ${user.display_name}`
          : "Dashboard"}
      </h1>

      {portfolio && <PortfolioSummaryCard portfolio={portfolio} />}

      <div className="grid gap-4 sm:gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Holdings</h2>
          <HoldingsTable holdings={portfolio?.holdings ?? []} />
        </div>
        <div className="space-y-4 sm:space-y-6">
          {risk && <RiskScoreCard score={risk.overall_score} />}
          <div>
            <h2 className="mb-3 text-lg font-semibold">Watchlist</h2>
            {watchlistLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-12 animate-pulse rounded-md bg-muted"
                  />
                ))}
              </div>
            ) : (
              <WatchlistTable items={watchlistItems ?? []} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
