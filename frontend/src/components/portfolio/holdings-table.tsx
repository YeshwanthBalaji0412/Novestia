"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent, formatQuantity } from "@/lib/format";
import type { HoldingSummary } from "@/types";

interface Props {
  holdings: HoldingSummary[];
}

export function HoldingsTable({ holdings }: Props) {
  if (holdings.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6 text-center text-muted-foreground">
        No holdings yet. Start trading to build your portfolio.
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
              <th className="p-3 font-medium">Shares</th>
              <th className="p-3 font-medium text-right">Price</th>
              <th className="p-3 font-medium text-right">Value</th>
              <th className="p-3 font-medium text-right">P/L</th>
              <th className="p-3 font-medium text-right">Day</th>
              <th className="p-3 font-medium text-right">Weight</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => {
              const pnl = parseFloat(h.unrealized_pnl);
              const dayChg = parseFloat(h.daily_change);
              return (
                <tr key={h.ticker} className="border-b last:border-0">
                  <td className="p-3">
                    <Link href={`/stocks/${h.ticker}`} className="hover:underline">
                      <div className="font-medium">{h.ticker}</div>
                      <div className="text-xs text-muted-foreground">
                        {h.company_name}
                      </div>
                    </Link>
                  </td>
                  <td className="p-3 tabular-nums">
                    {formatQuantity(h.quantity)}
                  </td>
                  <td className="p-3 text-right tabular-nums">
                    {formatCurrency(h.current_price)}
                  </td>
                  <td className="p-3 text-right tabular-nums">
                    {formatCurrency(h.market_value)}
                  </td>
                  <td
                    className={cn(
                      "p-3 text-right tabular-nums",
                      pnl > 0 && "text-green-600",
                      pnl < 0 && "text-red-600",
                    )}
                  >
                    {formatCurrency(h.unrealized_pnl)}
                    <div className="text-xs">
                      {formatPercent(h.unrealized_pnl_pct)}
                    </div>
                  </td>
                  <td
                    className={cn(
                      "p-3 text-right tabular-nums",
                      dayChg > 0 && "text-green-600",
                      dayChg < 0 && "text-red-600",
                    )}
                  >
                    {formatPercent(h.daily_change_pct)}
                  </td>
                  <td className="p-3 text-right tabular-nums">
                    {parseFloat(h.weight).toFixed(1)}%
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
