"use client";

import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@/lib/format";
import { useRemoveFromWatchlist } from "@/hooks/use-watchlist";
import type { WatchlistItem } from "@/types";

interface Props {
  items: WatchlistItem[];
}

export function WatchlistTable({ items }: Props) {
  const { mutate: remove, isPending } = useRemoveFromWatchlist();

  if (items.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6 text-center text-muted-foreground">
        Your watchlist is empty. Search for stocks to add.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="p-3 font-medium">Ticker</th>
              <th className="p-3 font-medium text-right">Price</th>
              <th className="p-3 font-medium text-right">Change</th>
              <th className="p-3 font-medium text-right"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const chg = parseFloat(item.daily_change);
              return (
                <tr key={item.ticker} className="border-b last:border-0">
                  <td className="p-3">
                    <div className="font-medium">{item.ticker}</div>
                    <div className="text-xs text-muted-foreground">
                      {item.company_name}
                    </div>
                  </td>
                  <td className="p-3 text-right tabular-nums">
                    {formatCurrency(item.current_price)}
                  </td>
                  <td
                    className={cn(
                      "p-3 text-right tabular-nums",
                      chg > 0 && "text-green-600",
                      chg < 0 && "text-red-600",
                    )}
                  >
                    {formatPercent(item.daily_change_pct)}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => remove(item.ticker)}
                      disabled={isPending}
                      className="text-xs text-muted-foreground hover:text-destructive"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
