"use client";

import { useExplainRisk } from "@/hooks/use-ai";

export function RiskAIInterpretation() {
  const { mutate, data, isPending } = useExplainRisk();
  const interpretation = data?.data?.interpretation;

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">AI Interpretation</h3>
        {!interpretation && (
          <button
            onClick={() => mutate()}
            disabled={isPending}
            className="text-sm text-primary hover:underline disabled:opacity-50"
          >
            {isPending ? "Generating..." : "Generate"}
          </button>
        )}
      </div>
      {isPending && (
        <div className="mt-3 space-y-2">
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
        </div>
      )}
      {interpretation && (
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          {interpretation.split("\n\n").map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      )}
      {data?.data?.error && (
        <p className="mt-3 text-sm text-muted-foreground">
          AI interpretation is currently unavailable.
        </p>
      )}
    </div>
  );
}
