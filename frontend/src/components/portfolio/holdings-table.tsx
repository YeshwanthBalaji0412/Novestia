"use client";

import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent, formatQuantity } from "@/lib/format";
import { EmptyState } from "@/components/common/empty-state";
import type { HoldingSummary } from "@/types";

interface Props {
  holdings: HoldingSummary[];
  compact?: boolean;
}

type SortKey = "ticker" | "value" | "pnl" | "day" | "weight";

export function HoldingsTable({ holdings, compact }: Props) {
  const [sortBy, setSortBy] = useState<SortKey>("value");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  if (holdings.length === 0) {
    return (
      <EmptyState
        icon="📊"
        title="No holdings yet"
        message="Search for a stock to make your first trade."
        action={
          <Link href="/explore" className="glass-card inline-flex h-9 items-center px-4 text-xs font-semibold uppercase tracking-wider text-primary hover:border-primary/30">
            Explore Stocks
          </Link>
        }
      />
    );
  }

  function handleSort(key: SortKey) {
    if (sortBy === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
  }

  const sorted = [...holdings].sort((a, b) => {
    let av = 0;
    let bv = 0;
    switch (sortBy) {
      case "ticker": return sortDir === "asc" ? a.ticker.localeCompare(b.ticker) : b.ticker.localeCompare(a.ticker);
      case "value": av = parseFloat(a.market_value); bv = parseFloat(b.market_value); break;
      case "pnl": av = parseFloat(a.unrealized_pnl); bv = parseFloat(b.unrealized_pnl); break;
      case "day": av = parseFloat(a.daily_change_pct); bv = parseFloat(b.daily_change_pct); break;
      case "weight": av = parseFloat(a.weight); bv = parseFloat(b.weight); break;
    }
    return sortDir === "asc" ? av - bv : bv - av;
  });

  function th(label: string, sortKey?: SortKey, right?: boolean) {
    return (
      <th
        key={label}
        className={cn(
          "p-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground",
          right && "text-right",
          sortKey && "cursor-pointer select-none hover:text-foreground",
        )}
        onClick={sortKey ? () => handleSort(sortKey) : undefined}
      >
        {label}
        {sortKey && sortBy === sortKey && (
          <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>
        )}
      </th>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-left">
              {th("Asset", "ticker")}
              {!compact && th("Qty")}
              {!compact && th("Avg Cost", undefined, true)}
              {th("Price", undefined, true)}
              {th("Value", "value", true)}
              {th("P/L", "pnl", true)}
              {th("Day", "day", true)}
              {!compact && th("Weight", "weight", true)}
            </tr>
          </thead>
          <tbody>
            {sorted.map((h, i) => {
              const pnl = parseFloat(h.unrealized_pnl);
              const dayChg = parseFloat(h.daily_change_pct);
              return (
                <motion.tr
                  key={h.ticker}
                  className="border-b border-border/30 transition-colors last:border-0 hover:bg-accent/30"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                >
                  <td className="p-3">
                    <Link href={`/stocks/${h.ticker}`} className="group">
                      <div className="font-semibold transition-colors group-hover:text-primary">
                        {h.ticker}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {h.company_name}
                      </div>
                    </Link>
                  </td>
                  {!compact && (
                    <td className="p-3 font-numbers text-muted-foreground">
                      {formatQuantity(h.quantity)}
                    </td>
                  )}
                  {!compact && (
                    <td className="p-3 text-right font-numbers text-muted-foreground">
                      {formatCurrency(h.average_cost)}
                    </td>
                  )}
                  <td className="p-3 text-right font-numbers">
                    {formatCurrency(h.current_price)}
                  </td>
                  <td className="p-3 text-right font-numbers font-medium">
                    {formatCurrency(h.market_value)}
                  </td>
                  <td className="p-3 text-right">
                    <span className={cn("font-numbers font-medium", pnl > 0 && "text-gain", pnl < 0 && "text-loss")}>
                      {formatCurrency(h.unrealized_pnl)}
                    </span>
                    <div className={cn("font-numbers text-[11px]", pnl > 0 && "text-gain", pnl < 0 && "text-loss")}>
                      {formatPercent(h.unrealized_pnl_pct)}
                    </div>
                  </td>
                  <td className={cn("p-3 text-right font-numbers", dayChg > 0 && "text-gain", dayChg < 0 && "text-loss")}>
                    {formatPercent(h.daily_change_pct)}
                  </td>
                  {!compact && (
                    <td className="p-3 text-right font-numbers text-muted-foreground">
                      {parseFloat(h.weight).toFixed(1)}%
                    </td>
                  )}
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
