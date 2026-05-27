"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";
import { useApi } from "@/hooks/use-api";
import type { ApiResponse, TradePreview, TradeResult } from "@/types";

interface Props {
  ticker: string;
  currentPrice: string;
  cashBalance: string;
  heldQuantity?: string;
  onClose: () => void;
}

export function TradeDialog({
  ticker,
  currentPrice,
  cashBalance,
  heldQuantity,
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

  function validateQuantity(): string | null {
    if (!quantity) return "Enter a quantity";
    const num = parseFloat(quantity);
    if (isNaN(num) || num <= 0) return "Quantity must be greater than zero";
    if (!/^\d+(\.\d{1,8})?$/.test(quantity)) return "Max 8 decimal places";
    return null;
  }

  async function handlePreview() {
    const err = validateQuantity();
    if (err) { setError(err); return; }
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
    if (!quantity || !journalNote.trim() || !preview) return;
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
      void queryClient.invalidateQueries({ queryKey: ["risk"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="glass-card-solid w-full max-w-md p-6"
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
        >
          {success ? (
            /* ── Success state ── */
            <div>
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neon-green/10">
                  <span className="text-gain text-lg">✓</span>
                </div>
                <h2 className="font-heading text-lg font-semibold">
                  Trade Executed
                </h2>
              </div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="glass-card p-3">
                  <span className={cn("font-semibold", success.transaction.type === "BUY" ? "text-gain" : "text-loss")}>
                    {success.transaction.type}
                  </span>{" "}
                  <span className="font-numbers">{parseFloat(success.transaction.quantity)}</span>{" "}
                  {success.transaction.ticker} @{" "}
                  <span className="font-numbers">{formatCurrency(success.transaction.execution_price)}</span>
                  <div className="mt-1 text-muted-foreground">
                    Total: <span className="font-numbers">{formatCurrency(success.transaction.total_amount)}</span>
                  </div>
                </div>
                {success.transaction.realized_pnl && (
                  <p className="font-numbers text-sm">
                    Realized P/L:{" "}
                    <span className={parseFloat(success.transaction.realized_pnl) >= 0 ? "text-gain" : "text-loss"}>
                      {formatCurrency(success.transaction.realized_pnl)}
                    </span>
                  </p>
                )}
                {success.risk_score_after != null && (
                  <p className="text-xs text-muted-foreground">
                    Risk score: <span className="font-numbers text-foreground">{success.risk_score_after}/100</span>
                  </p>
                )}
              </div>
              <button
                onClick={onClose}
                className="mt-5 inline-flex h-10 w-full items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition-all hover:brightness-110"
              >
                Done
              </button>
            </div>
          ) : (
            /* ── Trade form ── */
            <div>
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-lg font-semibold">
                  Trade {ticker}
                </h2>
                <button
                  onClick={onClose}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  ✕
                </button>
              </div>

              <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                <span>Price: <span className="font-numbers text-foreground">{formatCurrency(currentPrice)}</span></span>
                <span>Cash: <span className="font-numbers text-foreground">{formatCurrency(cashBalance)}</span></span>
              </div>

              {/* BUY/SELL toggle */}
              <div className="mt-4 flex gap-1.5">
                {(["BUY", "SELL"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTradeType(t); setPreview(null); }}
                    className={cn(
                      "flex-1 rounded-lg py-2.5 text-xs font-semibold uppercase tracking-wider transition-all",
                      tradeType === t
                        ? t === "BUY"
                          ? "bg-neon-green/15 text-gain glow-green"
                          : "bg-neon-red/15 text-loss glow-red"
                        : "glass-card text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {/* Quantity */}
              <div className="mt-4 space-y-1.5">
                <label className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  Shares
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={quantity}
                    onChange={(e) => { setQuantity(e.target.value); setPreview(null); setError(null); }}
                    placeholder="0.00"
                    className="flex h-10 w-full rounded-lg border border-input bg-background/50 px-3 py-2 pr-14 font-numbers text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                  />
                  {tradeType === "SELL" && heldQuantity && (
                    <button
                      type="button"
                      onClick={() => { setQuantity(heldQuantity); setPreview(null); }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md bg-accent/50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary hover:bg-accent"
                    >
                      Max
                    </button>
                  )}
                </div>
                <p className="font-numbers text-xs text-muted-foreground">
                  ≈ {formatCurrency(estimatedTotal)}
                </p>
              </div>

              {/* Journal note */}
              <div className="mt-4 space-y-1.5">
                <label className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  Trade Thesis · <span className="font-numbers">{journalNote.length}/500</span>
                </label>
                <textarea
                  value={journalNote}
                  onChange={(e) => setJournalNote(e.target.value)}
                  maxLength={500}
                  rows={2}
                  placeholder="Every trade needs a reason..."
                  className="flex w-full rounded-lg border border-input bg-background/50 px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />
              </div>

              {/* Warnings */}
              {preview?.warnings && preview.warnings.length > 0 && (
                <div className="mt-3 space-y-1">
                  {preview.warnings.map((w, i) => (
                    <p
                      key={i}
                      className={cn(
                        "rounded-lg px-3 py-2 text-xs",
                        w.code === "AFTER_HOURS"
                          ? "bg-neon-amber/10 text-warning"
                          : "bg-neon-red/10 text-loss",
                      )}
                    >
                      {w.message}
                    </p>
                  ))}
                </div>
              )}

              {error && (
                <p className="mt-3 text-sm text-loss">{error}</p>
              )}

              {/* Actions */}
              <div className="mt-5">
                {!preview ? (
                  <button
                    onClick={handlePreview}
                    disabled={isLoading || !quantity || parseFloat(quantity) <= 0}
                    className="glass-card inline-flex h-10 w-full items-center justify-center text-sm font-semibold transition-all hover:border-primary/30 disabled:opacity-40"
                  >
                    {isLoading ? "Loading..." : "Preview Trade"}
                  </button>
                ) : (
                  <button
                    onClick={handleExecute}
                    disabled={isLoading || !journalNote.trim()}
                    className={cn(
                      "inline-flex h-10 w-full items-center justify-center rounded-lg text-sm font-semibold transition-all disabled:opacity-40",
                      tradeType === "BUY"
                        ? "bg-neon-green/15 text-gain glow-green hover:bg-neon-green/25"
                        : "bg-neon-red/15 text-loss glow-red hover:bg-neon-red/25",
                    )}
                  >
                    {isLoading
                      ? "Executing..."
                      : `Confirm ${tradeType} · ${formatCurrency(preview.estimated_total)}`}
                  </button>
                )}
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
