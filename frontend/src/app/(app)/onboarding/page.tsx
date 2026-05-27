"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { createApiClient } from "@/lib/api/client";
import { useUserSync } from "@/hooks/use-user-sync";
import type { ApiResponse, OnboardResponse } from "@/types";

const STARTER_TICKERS = [
  { ticker: "VOO", name: "S&P 500 ETF" },
  { ticker: "QQQ", name: "Nasdaq 100 ETF" },
  { ticker: "VTI", name: "Total Market ETF" },
  { ticker: "BND", name: "Bond ETF" },
  { ticker: "AAPL", name: "Apple" },
  { ticker: "MSFT", name: "Microsoft" },
  { ticker: "GOOGL", name: "Google" },
  { ticker: "AMZN", name: "Amazon" },
  { ticker: "NVDA", name: "NVIDIA" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { data: user, isLoading: isSyncing, refetch } = useUserSync();
  const [step, setStep] = useState(0);
  const [displayName, setDisplayName] = useState("");
  const [selectedTickers, setSelectedTickers] = useState<string[]>([
    "VOO", "AAPL", "NVDA",
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isSyncing && user?.onboarded) {
      router.replace("/dashboard");
    }
  }, [isSyncing, user?.onboarded, router]);

  if (!isSyncing && user?.onboarded) return null;

  function toggleTicker(ticker: string) {
    setSelectedTickers((prev) =>
      prev.includes(ticker)
        ? prev.filter((t) => t !== ticker)
        : [...prev, ticker],
    );
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    setError(null);
    try {
      const token = await getToken();
      const client = createApiClient(token);
      await client.post<ApiResponse<OnboardResponse>>(
        "/api/v1/users/onboard",
        { display_name: displayName || null },
      );

      for (const t of selectedTickers) {
        try {
          await client.post(`/api/v1/watchlist/${t}`);
        } catch {
          // Non-critical
        }
      }

      await refetch();
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="relative flex flex-1 items-center justify-center px-4">
      {/* Ambient glow */}
      <div
        className="pointer-events-none absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[400px] w-[400px] rounded-full opacity-15 blur-[100px]"
        style={{ background: "oklch(0.7 0.18 240)" }}
      />

      <div className="relative w-full max-w-lg space-y-6">
        <AnimatePresence mode="wait">
          {step === 0 && (
            <motion.div
              key="step0"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              <div className="space-y-3 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
                  <span className="font-heading text-2xl font-bold text-primary">N</span>
                </div>
                <h1 className="font-heading text-3xl font-bold">Welcome to Novestia</h1>
                <p className="text-sm text-muted-foreground">
                  Learn investing by doing — with zero risk. You&apos;ll get
                  $10,000 in virtual cash to practice trading real stocks at real prices.
                </p>
              </div>
              <div className="glass-card space-y-3 p-4 text-sm">
                {[
                  ["Real prices", "Stocks move with the actual market"],
                  ["Fake money", "No risk, pure learning"],
                  ["Risk analysis", "AI-powered feedback on your portfolio"],
                  ["Trade journal", "Every trade needs a reason"],
                ].map(([title, desc]) => (
                  <div key={title} className="flex gap-3">
                    <span className="mt-0.5 text-primary">→</span>
                    <div>
                      <span className="font-medium">{title}</span>
                      <span className="text-muted-foreground"> — {desc}</span>
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setStep(1)}
                className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition-all hover:brightness-110 hover:shadow-[0_0_20px_oklch(0.7_0.18_240_/_0.3)]"
              >
                Get Started
              </button>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              <div className="space-y-2 text-center">
                <h2 className="font-heading text-2xl font-bold">What should we call you?</h2>
                <p className="text-sm text-muted-foreground">
                  Optional — you can change this later in settings.
                </p>
              </div>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                className="flex h-11 w-full rounded-lg border border-input bg-background/50 px-4 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                autoFocus
              />
              <button
                onClick={() => setStep(2)}
                className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition-all hover:brightness-110"
              >
                {displayName ? "Continue" : "Skip"}
              </button>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              <div className="space-y-2 text-center">
                <h2 className="font-heading text-2xl font-bold">Pick stocks to watch</h2>
                <p className="text-sm text-muted-foreground">
                  We&apos;ll add these to your watchlist. You can change them anytime.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {STARTER_TICKERS.map(({ ticker, name }) => (
                  <button
                    key={ticker}
                    onClick={() => toggleTicker(ticker)}
                    className={`glass-card rounded-lg px-3 py-3 text-center transition-all ${
                      selectedTickers.includes(ticker)
                        ? "glow-blue border-primary/40 bg-primary/10"
                        : "hover:border-primary/20"
                    }`}
                  >
                    <div className="text-sm font-semibold">{ticker}</div>
                    <div className="text-[10px] text-muted-foreground">{name}</div>
                  </button>
                ))}
              </div>

              {error && <p className="text-sm text-loss">{error}</p>}

              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition-all hover:brightness-110 hover:shadow-[0_0_20px_oklch(0.7_0.18_240_/_0.3)] disabled:opacity-50"
              >
                {isSubmitting
                  ? "Setting up your portfolio..."
                  : "Start with $10,000"}
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Progress dots */}
        <div className="flex justify-center gap-2">
          {[0, 1, 2].map((s) => (
            <div
              key={s}
              className={`h-1 rounded-full transition-all ${
                s <= step ? "w-8 bg-primary" : "w-4 bg-muted"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
