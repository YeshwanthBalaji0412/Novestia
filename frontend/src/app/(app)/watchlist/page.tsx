"use client";

import { useWatchlist } from "@/hooks/use-watchlist";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { StockSearch } from "@/components/common/stock-search";
import { TableSkeleton } from "@/components/common/skeleton";

export default function WatchlistPage() {
  const { data: items, isLoading } = useWatchlist();

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <h1 className="text-xl font-bold sm:text-2xl">Watchlist</h1>

      <StockSearch
        showWatchlistButton
        placeholder="Search by company name or ticker (e.g. Apple, MSFT, Tesla...)"
      />

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : (
        <WatchlistTable items={items ?? []} />
      )}
    </div>
  );
}
