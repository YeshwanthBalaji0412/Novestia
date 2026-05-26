"use client";

import { useState } from "react";
import { useExplainStock } from "@/hooks/use-ai";

interface Props {
  ticker: string;
}

export function AIExplanation({ ticker }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { mutate, data, isPending } = useExplainStock();

  function handleToggle() {
    if (!expanded && !data) {
      mutate(ticker);
    }
    setExpanded(!expanded);
  }

  const explanation = data?.data?.explanation;

  return (
    <div className="rounded-lg border bg-card">
      <button
        onClick={handleToggle}
        className="flex w-full items-center justify-between p-4 text-left text-sm font-medium hover:bg-accent/50"
      >
        <span>AI Explanation</span>
        <span className="text-muted-foreground">{expanded ? "−" : "+"}</span>
      </button>
      {expanded && (
        <div className="border-t px-4 pb-4 pt-3">
          {isPending && (
            <div className="space-y-2">
              <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
              <div className="h-4 w-full animate-pulse rounded bg-muted" />
              <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
            </div>
          )}
          {explanation && (
            <div className="space-y-3 text-sm text-muted-foreground">
              {explanation.split("\n\n").map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          )}
          {data?.data?.error && (
            <p className="text-sm text-muted-foreground">
              AI explanation is currently unavailable.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
