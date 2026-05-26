"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatCurrency, formatQuantity } from "@/lib/format";
import { useTransactions } from "@/hooks/use-portfolio";

export default function TransactionsPage() {
  const [cursor, setCursor] = useState<string | null>(null);
  const { data, isLoading } = useTransactions(20, cursor);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const transactions = data?.data ?? [];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-bold">Transaction History</h1>

      {transactions.length === 0 ? (
        <div className="rounded-lg border bg-card p-6 text-center text-muted-foreground">
          No transactions yet. Start trading to see your history.
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="p-3 font-medium">Date</th>
                  <th className="p-3 font-medium">Type</th>
                  <th className="p-3 font-medium">Ticker</th>
                  <th className="p-3 font-medium text-right">Qty</th>
                  <th className="p-3 font-medium text-right">Price</th>
                  <th className="p-3 font-medium text-right">Total</th>
                  <th className="p-3 font-medium">Note</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <tr key={txn.id} className="border-b last:border-0">
                    <td className="p-3 text-muted-foreground">
                      {new Date(txn.executed_at).toLocaleDateString()}
                      {txn.executed_after_hours && (
                        <span className="ml-1 text-xs text-yellow-600">
                          AH
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      <span
                        className={cn(
                          "inline-flex rounded px-2 py-0.5 text-xs font-medium",
                          txn.type === "BUY"
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800",
                        )}
                      >
                        {txn.type}
                      </span>
                    </td>
                    <td className="p-3 font-medium">{txn.ticker}</td>
                    <td className="p-3 text-right tabular-nums">
                      {formatQuantity(txn.quantity)}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {formatCurrency(txn.execution_price)}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {formatCurrency(txn.total_amount)}
                    </td>
                    <td className="max-w-[200px] truncate p-3 text-xs text-muted-foreground">
                      {txn.journal_note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data?.next_cursor && (
            <div className="border-t p-3 text-center">
              <button
                onClick={() => setCursor(data.next_cursor)}
                className="text-sm font-medium text-primary hover:underline"
              >
                Load more
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
