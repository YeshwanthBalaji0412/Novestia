"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@/lib/format";
import { EmptyState } from "@/components/common/empty-state";
import { useRemoveFromWatchlist } from "@/hooks/use-watchlist";
import type { WatchlistItem } from "@/types";

interface Props {
  items: WatchlistItem[];
}

export function WatchlistTable({ items }: Props) {
  const { mutate: remove, isPending } = useRemoveFromWatchlist();

  if (items.length === 0) {
    return (
      <EmptyState
        icon="👀"
        title="Watchlist is empty"
        message="Search for stocks to start watching."
        action={
          <Link href="/explore" className="glass-card inline-flex h-9 items-center px-4 text-xs font-semibold uppercase tracking-wider text-primary hover:border-primary/30">
            Explore Stocks
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-1.5">
      {items.map((item) => {
        const chg = parseFloat(item.daily_change);
        return (
          <Link
            key={item.ticker}
            href={`/stocks/${item.ticker}`}
            className="glass-card flex items-center justify-between p-3 transition-all hover:border-primary/30"
          >
            <div>
              <span className="font-semibold text-sm">{item.ticker}</span>
              <span className="ml-2 text-[11px] text-muted-foreground">
                {item.company_name}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-numbers text-sm">
                {formatCurrency(item.current_price)}
              </span>
              <span
                className={cn(
                  "font-numbers text-xs font-medium",
                  chg > 0 && "text-gain",
                  chg < 0 && "text-loss",
                )}
              >
                {formatPercent(item.daily_change_pct)}
              </span>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  remove(item.ticker);
                }}
                disabled={isPending}
                className="text-[10px] uppercase tracking-wide text-muted-foreground transition-colors hover:text-destructive"
              >
                ✕
              </button>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
