"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatCurrency, formatQuantity } from "@/lib/format";
import { useJournal, useCreateJournalEntry } from "@/hooks/use-journal";
import { TableSkeleton } from "@/components/common/skeleton";

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
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Journal</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            {showForm ? "Cancel" : "New Entry"}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="rounded-lg border bg-card p-4">
          <textarea
            value={newEntry}
            onChange={(e) => setNewEntry(e.target.value)}
            placeholder="Write a reflection on your investing journey..."
            maxLength={2000}
            rows={3}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            autoFocus
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {newEntry.length}/2000
            </span>
            <button
              type="submit"
              disabled={isCreating || !newEntry.trim()}
              className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isCreating ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      )}

      {/* Filters */}
      <div className="flex gap-1">
        {filters.map((f) => (
          <button
            key={f.label}
            onClick={() => {
              setFilter(f.value);
              setCursor(null);
            }}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              filter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : entries.length === 0 ? (
        <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
          <p>No journal entries yet.</p>
          <p className="mt-1 text-sm">
            Your trade notes appear here automatically, or write a reflection.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="rounded-lg border bg-card p-4">
              {entry.transaction_summary && (
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className={cn(
                      "inline-flex rounded px-2 py-0.5 text-xs font-medium",
                      entry.transaction_summary.type === "BUY"
                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                    )}
                  >
                    {entry.transaction_summary.type}
                  </span>
                  <span className="text-sm font-medium">
                    {formatQuantity(entry.transaction_summary.quantity)}{" "}
                    {entry.transaction_summary.ticker} @{" "}
                    {formatCurrency(entry.transaction_summary.execution_price)}
                  </span>
                </div>
              )}
              <p className="text-sm">{entry.content}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                {new Date(entry.created_at).toLocaleString()}
              </p>
            </div>
          ))}

          {data?.next_cursor && (
            <div className="text-center">
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
