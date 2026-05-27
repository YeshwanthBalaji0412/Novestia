"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatCurrency, formatQuantity } from "@/lib/format";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { TableSkeleton } from "@/components/common/skeleton";
import { useJournal, useCreateJournalEntry } from "@/hooks/use-journal";

export default function JournalPage() {
  const [filter, setFilter] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const { data, isLoading } = useJournal(20, cursor, filter);
  const { mutate: create, isPending: isCreating } = useCreateJournalEntry();
  const [newEntry, setNewEntry] = useState("");
  const [showForm, setShowForm] = useState(false);

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newEntry.trim()) return;
    create(newEntry.trim());
    setNewEntry("");
    setShowForm(false);
  }

  const entries = data?.data ?? [];
  const filters = [
    { label: "All", value: null },
    { label: "Trade Notes", value: "trade" },
    { label: "Reflections", value: "reflection" },
  ];

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        title="Journal"
        action={
          <button
            onClick={() => setShowForm(!showForm)}
            className={cn(
              "inline-flex h-9 items-center rounded-lg px-4 text-sm font-semibold transition-all",
              showForm
                ? "glass-card text-muted-foreground"
                : "bg-primary text-primary-foreground hover:brightness-110",
            )}
          >
            {showForm ? "Cancel" : "New Entry"}
          </button>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="glass-card p-4">
          <textarea
            value={newEntry}
            onChange={(e) => setNewEntry(e.target.value)}
            placeholder="Write a reflection on your investing journey..."
            maxLength={2000}
            rows={3}
            className="w-full rounded-lg border border-input bg-background/50 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            autoFocus
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="font-numbers text-[10px] text-muted-foreground">
              {newEntry.length}/2000
            </span>
            <button
              type="submit"
              disabled={isCreating || !newEntry.trim()}
              className="inline-flex h-8 items-center rounded-lg bg-primary px-4 text-xs font-semibold text-primary-foreground transition-all hover:brightness-110 disabled:opacity-40"
            >
              {isCreating ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      )}

      <div className="flex gap-1">
        {filters.map((f) => (
          <button
            key={f.label}
            onClick={() => { setFilter(f.value); setCursor(null); }}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium uppercase tracking-wider transition-all",
              filter === f.value
                ? "bg-primary/15 text-primary glow-blue"
                : "glass-card text-muted-foreground hover:text-foreground",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : entries.length === 0 ? (
        <EmptyState
          icon="📓"
          title="No journal entries yet"
          message="Your trade notes appear here automatically, or write a reflection."
        />
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => (
            <div key={entry.id} className="glass-card p-4">
              {entry.transaction_summary && (
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className={cn(
                      "inline-flex rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                      entry.transaction_summary.type === "BUY"
                        ? "bg-neon-green/10 text-gain"
                        : "bg-neon-red/10 text-loss",
                    )}
                  >
                    {entry.transaction_summary.type}
                  </span>
                  <span className="font-numbers text-sm">
                    {formatQuantity(entry.transaction_summary.quantity)}{" "}
                    {entry.transaction_summary.ticker} @{" "}
                    {formatCurrency(entry.transaction_summary.execution_price)}
                  </span>
                </div>
              )}
              <p className="break-words text-sm leading-relaxed">{entry.content}</p>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                {new Date(entry.created_at).toLocaleString()}
              </p>
            </div>
          ))}

          {data?.next_cursor && (
            <div className="pt-2 text-center">
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
