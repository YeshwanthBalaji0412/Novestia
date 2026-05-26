"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createApiClient } from "@/lib/api/client";
import { useUserSync } from "@/hooks/use-user-sync";
import type { ApiResponse, OnboardResponse } from "@/types";

const STARTER_TICKERS = [
  "VOO", "QQQ", "VTI", "BND", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
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

      for (const ticker of selectedTickers) {
        try {
          await client.post(`/api/v1/watchlist/${ticker}`);
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
    <div className="flex flex-1 items-center justify-center px-4">
      <div className="w-full max-w-lg space-y-6">
        {step === 0 && (
          <>
            <div className="space-y-3 text-center">
              <h1 className="text-3xl font-bold">Welcome to Novestia</h1>
              <p className="text-muted-foreground">
                Learn investing by doing — with zero risk. You&apos;ll get
                $10,000 in virtual cash to practice trading real stocks at real
                prices.
              </p>
            </div>
            <div className="space-y-2 rounded-lg border bg-card p-4 text-sm">
              <p>
                <span className="font-medium">Real prices</span> — stocks move
                with the actual market
              </p>
              <p>
                <span className="font-medium">Fake money</span> — no risk, pure
                learning
              </p>
              <p>
                <span className="font-medium">Risk analysis</span> —
                AI-powered feedback on your portfolio
              </p>
              <p>
                <span className="font-medium">Trade journal</span> — every
                trade needs a reason
              </p>
            </div>
            <button
              onClick={() => setStep(1)}
              className="inline-flex h-11 w-full items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Get Started
            </button>
          </>
        )}

        {step === 1 && (
          <>
            <div className="space-y-2 text-center">
              <h2 className="text-2xl font-bold">What should we call you?</h2>
              <p className="text-sm text-muted-foreground">
                Optional — you can change this later in settings.
              </p>
            </div>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
              className="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              autoFocus
            />
            <button
              onClick={() => setStep(2)}
              className="inline-flex h-11 w-full items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {displayName ? "Continue" : "Skip"}
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <div className="space-y-2 text-center">
              <h2 className="text-2xl font-bold">Pick stocks to watch</h2>
              <p className="text-sm text-muted-foreground">
                We&apos;ll add these to your watchlist. You can change them
                anytime.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {STARTER_TICKERS.map((ticker) => (
                <button
                  key={ticker}
                  onClick={() => toggleTicker(ticker)}
                  className={`rounded-md border px-3 py-2.5 text-sm font-medium transition-colors ${
                    selectedTickers.includes(ticker)
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background hover:bg-accent"
                  }`}
                >
                  {ticker}
                </button>
              ))}
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="inline-flex h-11 w-full items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isSubmitting
                ? "Setting up your portfolio..."
                : "Start with $10,000"}
            </button>
          </>
        )}

        <div className="flex justify-center gap-1.5">
          {[0, 1, 2].map((s) => (
            <div
              key={s}
              className={`h-1.5 w-8 rounded-full ${
                s <= step ? "bg-primary" : "bg-muted"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
