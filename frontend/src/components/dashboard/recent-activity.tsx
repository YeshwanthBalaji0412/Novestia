"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { formatCurrency, formatQuantity } from "@/lib/format";
import { useTransactions } from "@/hooks/use-portfolio";

export function RecentActivity() {
  const { data } = useTransactions(5);
  const txns = data?.data ?? [];

  if (txns.length === 0) return null;

  return (
    <div className="glass-card p-4">
      <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        Recent Activity
      </p>
      <div className="space-y-2">
        {txns.map((txn) => {
          const ago = getTimeAgo(txn.executed_at);
          return (
            <Link
              key={txn.id}
              href="/portfolio/transactions"
              className="flex items-center justify-between rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-accent/30"
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "inline-flex h-5 w-5 items-center justify-center rounded text-[9px] font-bold",
                    txn.type === "BUY"
                      ? "bg-neon-green/10 text-gain"
                      : "bg-neon-red/10 text-loss",
                  )}
                >
                  {txn.type === "BUY" ? "B" : "S"}
                </span>
                <span>
                  <span className="font-medium">
                    {txn.type === "BUY" ? "Bought" : "Sold"}
                  </span>{" "}
                  <span className="font-numbers">
                    {formatQuantity(txn.quantity)} {txn.ticker}
                  </span>{" "}
                  <span className="text-muted-foreground">
                    @ {formatCurrency(txn.execution_price)}
                  </span>
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground">{ago}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function getTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
