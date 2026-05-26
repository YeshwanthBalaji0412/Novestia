"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useApi } from "@/hooks/use-api";
import { useAddToWatchlist } from "@/hooks/use-watchlist";
import type { ApiResponse } from "@/types";

interface SearchResult {
  ticker: string;
  company_name: string;
  exchange: string | null;
  instrument_type: string;
}

interface Props {
  /** If true, show "Add to Watchlist" button on each result */
  showWatchlistButton?: boolean;
  /** Placeholder text */
  placeholder?: string;
}

export function StockSearch({
  showWatchlistButton = false,
  placeholder = "Search stocks (e.g. Apple, Tesla, Microsoft...)",
}: Props) {
  const api = useApi();
  const [query, setQuery] = useState("");
  const { mutate: addToWatchlist } = useAddToWatchlist();

  const { data: results, isLoading } = useQuery({
    queryKey: ["stock-search", query],
    queryFn: () =>
      api.get<ApiResponse<SearchResult[]>>(
        `/api/v1/stocks/search?q=${encodeURIComponent(query)}&limit=10`,
      ),
    select: (res) => res.data,
    enabled: query.length >= 1,
  });

  return (
    <div className="w-full">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />

      {query.length >= 1 && (
        <div className="mt-2 rounded-lg border bg-card">
          {isLoading && (
            <div className="p-3 text-sm text-muted-foreground">
              Searching...
            </div>
          )}
          {results && results.length === 0 && (
            <div className="p-3 text-sm text-muted-foreground">
              No results found for &quot;{query}&quot;
            </div>
          )}
          {results && results.length > 0 && (
            <ul>
              {results.map((stock) => (
                <li
                  key={stock.ticker}
                  className="flex items-center justify-between border-b px-3 py-2.5 last:border-0"
                >
                  <Link
                    href={`/stocks/${stock.ticker}`}
                    className="flex-1 hover:underline"
                  >
                    <span className="font-medium">{stock.ticker}</span>
                    <span className="ml-2 text-sm text-muted-foreground">
                      {stock.company_name}
                    </span>
                    {stock.exchange && (
                      <span className="ml-1 text-xs text-muted-foreground">
                        · {stock.exchange}
                      </span>
                    )}
                  </Link>
                  {showWatchlistButton && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        addToWatchlist(stock.ticker);
                      }}
                      className="ml-2 rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent"
                    >
                      + Watch
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
