"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";
import { useApi } from "@/hooks/use-api";
import type { ApiResponse, TradePreview, TradeResult } from "@/types";

interface Props {
  ticker: string;
  currentPrice: string;
  cashBalance: string;
  onClose: () => void;
}

export function TradeDialog({
  ticker,
  currentPrice,
  cashBalance,
  onClose,
}: Props) {
  const api = useApi();
  const queryClient = useQueryClient();

  const [tradeType, setTradeType] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [journalNote, setJournalNote] = useState("");
  const [preview, setPreview] = useState<TradePreview | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<TradeResult | null>(null);

  const estimatedTotal = quantity
    ? (parseFloat(quantity) * parseFloat(currentPrice)).toFixed(2)
    : "0.00";

  async function handlePreview() {
    if (!quantity || parseFloat(quantity) <= 0) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get<ApiResponse<TradePreview>>(
        `/api/v1/trades/preview?ticker=${ticker}&type=${tradeType}&quantity=${quantity}`,
      );
      setPreview(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExecute() {
    if (!quantity || !journalNote.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.post<ApiResponse<TradeResult>>("/api/v1/trades", {
        ticker,
        type: tradeType,
        quantity,
        journal_note: journalNote,
      });
      setSuccess(res.data);
      void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed");
    } finally {
      setIsLoading(false);
    }
  }

  if (success) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="w-full max-w-md rounded-lg border bg-background p-6">
          <h2 className="text-lg font-semibold text-green-600">
            Trade Executed
          </h2>
          <div className="mt-4 space-y-2 text-sm">
            <p>
              {success.transaction.type} {parseFloat(success.transaction.quantity)}{" "}
              {success.transaction.ticker} @{" "}
              {formatCurrency(success.transaction.execution_price)}
            </p>
            <p>Total: {formatCurrency(success.transaction.total_amount)}</p>
            {success.transaction.realized_pnl && (
              <p>Realized P/L: {formatCurrency(success.transaction.realized_pnl)}</p>
            )}
            {success.transaction.executed_after_hours && (
              <p className="text-yellow-600 text-xs">After-hours execution</p>
            )}
            <p className="text-muted-foreground">
              Cash remaining: {formatCurrency(success.portfolio_after.cash_balance)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="mt-4 inline-flex h-9 w-full items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg border bg-background p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Trade {ticker}</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <p className="mt-1 text-sm text-muted-foreground">
          Current price: {formatCurrency(currentPrice)} · Cash:{" "}
          {formatCurrency(cashBalance)}
        </p>

        {/* BUY/SELL toggle */}
        <div className="mt-4 flex gap-2">
          {(["BUY", "SELL"] as const).map((t) => (
            <button
              key={t}
              onClick={() => {
                setTradeType(t);
                setPreview(null);
              }}
              className={cn(
                "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
                tradeType === t
                  ? t === "BUY"
                    ? "bg-green-600 text-white"
                    : "bg-red-600 text-white"
                  : "border bg-background hover:bg-accent",
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Quantity input */}
        <div className="mt-4 space-y-2">
          <label className="text-sm font-medium">Shares</label>
          <input
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => {
              setQuantity(e.target.value);
              setPreview(null);
            }}
            placeholder="0.00"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm tabular-nums ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <p className="text-xs text-muted-foreground">
            Estimated total: {formatCurrency(estimatedTotal)}
          </p>
        </div>

        {/* Journal note */}
        <div className="mt-4 space-y-2">
          <label className="text-sm font-medium">
            Why are you making this trade?{" "}
            <span className="text-muted-foreground">
              ({journalNote.length}/500)
            </span>
          </label>
          <textarea
            value={journalNote}
            onChange={(e) => setJournalNote(e.target.value)}
            maxLength={500}
            rows={2}
            placeholder="Every trade needs a reason..."
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>

        {/* Warnings from preview */}
        {preview?.warnings && preview.warnings.length > 0 && (
          <div className="mt-4 space-y-1">
            {preview.warnings.map((w, i) => (
              <p
                key={i}
                className={cn(
                  "rounded-md px-3 py-2 text-xs",
                  w.code === "AFTER_HOURS"
                    ? "bg-yellow-50 text-yellow-800"
                    : "bg-red-50 text-red-800",
                )}
              >
                {w.message}
              </p>
            ))}
          </div>
        )}

        {error && (
          <p className="mt-4 text-sm text-destructive">{error}</p>
        )}

        {/* Action buttons */}
        <div className="mt-4 flex gap-2">
          {!preview ? (
            <button
              onClick={handlePreview}
              disabled={isLoading || !quantity || parseFloat(quantity) <= 0}
              className="flex-1 rounded-md bg-accent py-2 text-sm font-medium hover:bg-accent/80 disabled:opacity-50"
            >
              {isLoading ? "Loading..." : "Preview"}
            </button>
          ) : (
            <button
              onClick={handleExecute}
              disabled={isLoading || !journalNote.trim()}
              className={cn(
                "flex-1 rounded-md py-2 text-sm font-medium text-white disabled:opacity-50",
                tradeType === "BUY"
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-red-600 hover:bg-red-700",
              )}
            >
              {isLoading
                ? "Executing..."
                : `Confirm ${tradeType} ${formatCurrency(preview.estimated_total)}`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
