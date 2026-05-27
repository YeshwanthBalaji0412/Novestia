"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { formatCurrency, formatQuantity } from "@/lib/format";
import { useTransactions } from "@/hooks/use-portfolio";
import { TableSkeleton } from "@/components/common/skeleton";

export default function TransactionsPage() {
  const [cursor, setCursor] = useState<string | null>(null);
  const { data, isLoading } = useTransactions(20, cursor);

  if (isLoading) return <div className="p-4 sm:p-6"><TableSkeleton rows={8} /></div>;

  const transactions = data?.data ?? [];

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <h1 className="font-heading text-xl font-bold sm:text-2xl">Transaction History</h1>

      {transactions.length === 0 ? (
        <div className="glass-card p-8 text-center text-sm text-muted-foreground">
          No transactions yet. Start trading to see your history.
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 text-left">
                  {["Date", "Type", "Ticker", "Qty", "Price", "Total", "Note"].map((h, i) => (
                    <th
                      key={h}
                      className={cn(
                        "p-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground",
                        i >= 3 && i <= 5 && "text-right",
                      )}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-border/30 transition-colors last:border-0 hover:bg-accent/30">
                    <td className="p-3 text-xs text-muted-foreground">
                      {new Date(txn.executed_at).toLocaleDateString()}
                      {txn.executed_after_hours && (
                        <span className="ml-1 text-warning">AH</span>
                      )}
                    </td>
                    <td className="p-3">
                      <span
                        className={cn(
                          "inline-flex rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                          txn.type === "BUY"
                            ? "bg-neon-green/10 text-gain"
                            : "bg-neon-red/10 text-loss",
                        )}
                      >
                        {txn.type}
                      </span>
                    </td>
                    <td className="p-3">
                      <Link href={`/stocks/${txn.ticker}`} className="font-semibold hover:text-primary">
                        {txn.ticker}
                      </Link>
                    </td>
                    <td className="p-3 text-right font-numbers">{formatQuantity(txn.quantity)}</td>
                    <td className="p-3 text-right font-numbers">{formatCurrency(txn.execution_price)}</td>
                    <td className="p-3 text-right font-numbers font-medium">{formatCurrency(txn.total_amount)}</td>
                    <td className="max-w-[200px] truncate p-3 text-xs text-muted-foreground italic">
                      {txn.journal_note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data?.next_cursor && (
            <div className="border-t border-border/30 p-3 text-center">
              <button
                onClick={() => setCursor(data.next_cursor)}
                className="text-xs font-medium uppercase tracking-wider text-primary hover:brightness-110"
              >
                Load More
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
