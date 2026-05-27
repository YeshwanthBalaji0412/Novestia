"use client";

import { PageHeader } from "@/components/layout/page-header";
import { useWatchlist } from "@/hooks/use-watchlist";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { StockSearch } from "@/components/common/stock-search";
import { EmptyState } from "@/components/common/empty-state";
import { TableSkeleton } from "@/components/common/skeleton";

export default function WatchlistPage() {
  const { data: items, isLoading, error } = useWatchlist();

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <PageHeader title="Watchlist" />

      <StockSearch
        showWatchlistButton
        placeholder="Search by company name or ticker (e.g. Apple, MSFT, Tesla...)"
      />

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : error ? (
        <EmptyState icon="⚠" title="Failed to load watchlist" action={
          <button onClick={() => window.location.reload()} className="glass-card px-4 py-2 text-xs font-semibold uppercase tracking-wider text-primary">Retry</button>
        } />
      ) : (
        <WatchlistTable items={items ?? []} />
      )}
    </div>
  );
}
