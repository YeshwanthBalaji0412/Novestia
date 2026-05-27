"use client";

import { useClerk } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/layout/page-header";
import { useUserSync } from "@/hooks/use-user-sync";
import { useApi } from "@/hooks/use-api";

export default function SettingsPage() {
  const router = useRouter();
  const { signOut } = useClerk();
  const queryClient = useQueryClient();
  const api = useApi();
  const { data: user, refetch } = useUserSync();

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  async function handleSaveName() {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.patch("/api/v1/users/me", { display_name: displayName });
      await refetch();
      setMessage({ text: "Display name updated.", type: "success" });
    } catch {
      setMessage({ text: "Failed to update name.", type: "error" });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleReset() {
    setIsResetting(true);
    setMessage(null);
    try {
      await api.post("/api/v1/users/reset-portfolio");
      void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
      void queryClient.invalidateQueries({ queryKey: ["risk"] });
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
      setMessage({ text: "Portfolio reset to $10,000.", type: "success" });
      setShowResetConfirm(false);
    } catch {
      setMessage({ text: "Failed to reset portfolio.", type: "error" });
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 sm:gap-6 sm:p-6">
      <PageHeader title="Settings" />

      {message && (
        <div className={cn(
          "glass-card px-4 py-3 text-sm",
          message.type === "success" ? "glow-green text-gain" : "glow-red text-loss",
        )}>
          {message.text}
        </div>
      )}

      <div className="glass-card p-4">
        <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Display Name</p>
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="flex h-10 flex-1 rounded-lg border border-input bg-background/50 px-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
          />
          <button
            onClick={handleSaveName}
            disabled={isSaving}
            className="inline-flex h-10 items-center rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-all hover:brightness-110 disabled:opacity-40"
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <div className="glass-card border-neon-red/20 p-4">
        <p className="text-[10px] font-medium uppercase tracking-widest text-loss">Danger Zone</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Reset your portfolio to $10,000. This deletes all trades, holdings, journal entries, and risk history.
        </p>
        {!showResetConfirm ? (
          <button
            onClick={() => setShowResetConfirm(true)}
            className="mt-3 inline-flex h-9 items-center rounded-lg border border-neon-red/30 px-4 text-sm font-medium text-loss transition-all hover:bg-neon-red/10"
          >
            Reset Portfolio
          </button>
        ) : (
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={handleReset}
              disabled={isResetting}
              className="inline-flex h-9 items-center rounded-lg bg-neon-red/15 px-4 text-sm font-semibold text-loss glow-red transition-all hover:bg-neon-red/25 disabled:opacity-40"
            >
              {isResetting ? "Resetting..." : "Yes, reset everything"}
            </button>
            <button
              onClick={() => setShowResetConfirm(false)}
              className="glass-card inline-flex h-9 items-center px-4 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      <div className="glass-card p-4">
        <button
          onClick={() => signOut(() => router.push("/"))}
          className="glass-card inline-flex h-9 items-center px-4 text-sm font-medium transition-all hover:border-primary/30"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
