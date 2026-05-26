"use client";

import { useState } from "react";
import { useWatchlist, useAddToWatchlist } from "@/hooks/use-watchlist";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";

export default function WatchlistPage() {
  const { data: items, isLoading } = useWatchlist();
  const { mutate: addTicker, isPending } = useAddToWatchlist();
  const [tickerInput, setTickerInput] = useState("");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    addTicker(ticker);
    setTickerInput("");
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <form onSubmit={handleAdd} className="flex gap-2">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            placeholder="Add ticker (e.g. AAPL)"
            className="flex h-9 rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button
            type="submit"
            disabled={isPending || !tickerInput.trim()}
            className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isPending ? "Adding..." : "Add"}
          </button>
        </form>
      </div>

      <WatchlistTable items={items ?? []} />
    </div>
  );
}
