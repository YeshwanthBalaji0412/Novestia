"use client";

import { useClerk } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useUserSync } from "@/hooks/use-user-sync";
import { useApi } from "@/hooks/use-api";

export default function SettingsPage() {
  const router = useRouter();
  const { signOut } = useClerk();
  const queryClient = useQueryClient();
  const api = useApi();
  const { data: user, refetch } = useUserSync();

  const [displayName, setDisplayName] = useState(
    user?.display_name ?? "",
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark" | "system">(() => {
    if (typeof window === "undefined") return "system";
    return (localStorage.getItem("theme") as "light" | "dark" | "system") ?? "system";
  });

  function applyTheme(newTheme: "light" | "dark" | "system") {
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    const root = document.documentElement;
    if (newTheme === "dark") {
      root.classList.add("dark");
    } else if (newTheme === "light") {
      root.classList.remove("dark");
    } else {
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        root.classList.add("dark");
      } else {
        root.classList.remove("dark");
      }
    }
  }

  async function handleSaveName() {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.patch("/api/v1/users/me", { display_name: displayName });
      await refetch();
      setMessage("Display name updated.");
    } catch {
      setMessage("Failed to update name.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleReset() {
    setIsResetting(true);
    setMessage(null);
    try {
      await api.post("/api/v1/users/reset-portfolio");
      void queryClient.invalidateQueries();
      setMessage("Portfolio reset to $10,000.");
      setShowResetConfirm(false);
    } catch {
      setMessage("Failed to reset portfolio.");
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {message && (
        <div className="rounded-md border bg-card px-4 py-3 text-sm">
          {message}
        </div>
      )}

      {/* Display name */}
      <div className="rounded-lg border bg-card p-4">
        <h2 className="font-semibold">Display Name</h2>
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button
            onClick={handleSaveName}
            disabled={isSaving}
            className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      {/* Theme */}
      <div className="rounded-lg border bg-card p-4">
        <h2 className="font-semibold">Theme</h2>
        <div className="mt-3 flex gap-2">
          {(["light", "dark", "system"] as const).map((t) => (
            <button
              key={t}
              onClick={() => applyTheme(t)}
              className={`rounded-md border px-4 py-2 text-sm font-medium capitalize transition-colors ${
                theme === t
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input bg-background hover:bg-accent"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Reset portfolio */}
      <div className="rounded-lg border border-destructive/30 bg-card p-4">
        <h2 className="font-semibold text-destructive">Danger Zone</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Reset your portfolio to $10,000. This will delete all trades,
          holdings, journal entries, and risk history.
        </p>
        {!showResetConfirm ? (
          <button
            onClick={() => setShowResetConfirm(true)}
            className="mt-3 inline-flex h-9 items-center rounded-md border border-destructive px-4 text-sm font-medium text-destructive hover:bg-destructive/10"
          >
            Reset Portfolio
          </button>
        ) : (
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={handleReset}
              disabled={isResetting}
              className="inline-flex h-9 items-center rounded-md bg-destructive px-4 text-sm font-medium text-white hover:bg-destructive/90 disabled:opacity-50"
            >
              {isResetting ? "Resetting..." : "Yes, reset everything"}
            </button>
            <button
              onClick={() => setShowResetConfirm(false)}
              className="inline-flex h-9 items-center rounded-md border px-4 text-sm font-medium hover:bg-accent"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Sign out */}
      <div className="rounded-lg border bg-card p-4">
        <button
          onClick={() => signOut(() => router.push("/"))}
          className="inline-flex h-9 items-center rounded-md border px-4 text-sm font-medium hover:bg-accent"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
