"use client";

import Link from "next/link";
import { useUserSync } from "@/hooks/use-user-sync";
import { usePortfolio, usePerformance } from "@/hooks/use-portfolio";
import { useWatchlist } from "@/hooks/use-watchlist";
import { useRisk } from "@/hooks/use-risk";
import { PageHeader } from "@/components/layout/page-header";
import { PortfolioSummaryCard } from "@/components/portfolio/portfolio-summary-card";
import { PortfolioSparkline } from "@/components/portfolio/portfolio-sparkline";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { SectorDonut } from "@/components/portfolio/sector-donut";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { RiskScoreCard } from "@/components/risk/risk-score-card";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { PageSkeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";

export default function DashboardPage() {
  const { data: user, isLoading: userLoading } = useUserSync();
  const { data: portfolio, isLoading: portfolioLoading, error } = usePortfolio();
  const { data: watchlistItems, isLoading: watchlistLoading } = useWatchlist();
  const { data: risk } = useRisk();
  const { data: performance } = usePerformance("1M");

  if (userLoading || portfolioLoading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState
          icon="⚠"
          title="Failed to load portfolio"
          message="Check your connection and try again."
          action={
            <button
              onClick={() => window.location.reload()}
              className="glass-card px-4 py-2 text-xs font-semibold uppercase tracking-wider text-primary hover:border-primary/30"
            >
              Retry
            </button>
          }
        />
      </div>
    );
  }

  const cashPct = portfolio
    ? (parseFloat(portfolio.cash_balance) / parseFloat(portfolio.total_value)) * 100
    : 0;

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 sm:gap-5 sm:p-6">
      <PageHeader
        title={
          user?.display_name
            ? `Welcome back, ${user.display_name}`
            : "Dashboard"
        }
      />

      {/* KPI cards — 6 across */}
      {portfolio && <PortfolioSummaryCard portfolio={portfolio} />}

      {/* Sparkline strip */}
      <PortfolioSparkline points={performance?.points ?? []} />

      {/* Main content grid */}
      <div className="grid gap-4 sm:gap-5 lg:grid-cols-3">
        {/* Left — Holdings */}
        <div className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
              Holdings
            </p>
            <Link
              href="/portfolio"
              className="text-[10px] font-medium uppercase tracking-wider text-primary hover:brightness-110"
            >
              View All →
            </Link>
          </div>
          <HoldingsTable holdings={portfolio?.holdings ?? []} />

          {/* Recent activity */}
          <RecentActivity />
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          {/* Risk score */}
          {risk && <RiskScoreCard score={risk.overall_score} compact />}

          {/* Sector allocation */}
          {portfolio && portfolio.holdings.length > 0 && (
            <SectorDonut holdings={portfolio.holdings} cashPercent={cashPct} />
          )}

          {/* Watchlist */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                Watchlist
              </p>
              <Link
                href="/explore"
                className="text-[10px] font-medium uppercase tracking-wider text-primary hover:brightness-110"
              >
                + Add
              </Link>
            </div>
            {watchlistLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="skeleton-shimmer h-12 rounded-lg" />
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
