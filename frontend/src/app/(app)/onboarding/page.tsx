"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createApiClient } from "@/lib/api/client";
import { useUserSync } from "@/hooks/use-user-sync";
import type { ApiResponse, OnboardResponse } from "@/types";

export default function OnboardingPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { data: user, isLoading: isSyncing, refetch } = useUserSync();
  const [displayName, setDisplayName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already onboarded — redirect to dashboard
  if (!isSyncing && user?.onboarded) {
    router.replace("/dashboard");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const token = await getToken();
      const client = createApiClient(token);
      await client.post<ApiResponse<OnboardResponse>>("/api/v1/users/onboard", {
        display_name: displayName || null,
      });
      await refetch();
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="w-full max-w-md space-y-6 px-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold">Welcome to Novestia</h1>
          <p className="text-muted-foreground">
            You&apos;ll start with $10,000 in virtual cash to practice
            investing.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="displayName"
              className="text-sm font-medium leading-none"
            >
              Display name (optional)
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How should we call you?"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground ring-offset-background transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            {isSubmitting ? "Setting up..." : "Start Investing"}
          </button>
        </form>
      </div>
    </div>
  );
}
