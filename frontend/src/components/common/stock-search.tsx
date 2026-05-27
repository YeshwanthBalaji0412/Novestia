"use client";

import { useEffect, useState } from "react";
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
  showWatchlistButton?: boolean;
  placeholder?: string;
}

export function StockSearch({
  showWatchlistButton = false,
  placeholder = "Search stocks (e.g. Apple, Tesla, Microsoft...)",
}: Props) {
  const api = useApi();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const { mutate: addToWatchlist } = useAddToWatchlist();

  // Debounce search input by 300ms to prevent race conditions
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: results, isLoading } = useQuery({
    queryKey: ["stock-search", debouncedQuery],
    queryFn: () =>
      api.get<ApiResponse<SearchResult[]>>(
        `/api/v1/stocks/search?q=${encodeURIComponent(debouncedQuery)}&limit=10`,
      ),
    select: (res) => res.data,
    enabled: debouncedQuery.length >= 1,
  });

  return (
    <div className="w-full">
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">⌕</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="flex h-11 w-full rounded-lg border border-input bg-background/50 pl-9 pr-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
        />
      </div>

      {query.length >= 1 && (
        <div className="glass-card-solid mt-2">
          {isLoading && (
            <div className="p-3 text-sm text-muted-foreground scan-line">
              Searching...
            </div>
          )}
          {results && results.length === 0 && (
            <div className="p-3 text-sm text-muted-foreground">
              No results for &quot;{query}&quot;
            </div>
          )}
          {results && results.length > 0 && (
            <ul>
              {results.map((stock) => (
                <li
                  key={stock.ticker}
                  className="flex items-center justify-between border-b border-border/30 px-3 py-2.5 transition-colors last:border-0 hover:bg-accent/30"
                >
                  <Link
                    href={`/stocks/${stock.ticker}`}
                    className="flex flex-1 items-center gap-2"
                  >
                    <span className="font-semibold text-sm">{stock.ticker}</span>
                    <span className="text-xs text-muted-foreground">
                      {stock.company_name}
                    </span>
                    {stock.exchange && (
                      <span className="text-[10px] text-muted-foreground/60">
                        {stock.exchange}
                      </span>
                    )}
                  </Link>
                  {showWatchlistButton && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        addToWatchlist(stock.ticker);
                      }}
                      className="glass-card ml-2 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider transition-all hover:border-primary/30 hover:text-primary"
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
