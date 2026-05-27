"use client";

import { Skeleton } from "@/components/common/skeleton";
import { useExplainRisk } from "@/hooks/use-ai";

export function RiskAIInterpretation() {
  const { mutate, data, isPending } = useExplainRisk();
  const interpretation = data?.data?.interpretation;

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-ai">✦</span>
          <h3 className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
            AI Interpretation
          </h3>
        </div>
        {!interpretation && (
          <button
            onClick={() => mutate()}
            disabled={isPending}
            className="glass-card px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-ai transition-all hover:glow-purple disabled:opacity-40"
          >
            {isPending ? "Generating..." : "Generate"}
          </button>
        )}
      </div>
      {isPending && (
        <div className="mt-3 space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      )}
      {interpretation && (
        <div className="mt-3 space-y-2 text-sm leading-relaxed text-muted-foreground">
          {interpretation.split("\n\n").map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      )}
      {data?.data?.error && (
        <p className="mt-3 text-xs text-muted-foreground">
          AI interpretation is currently unavailable.
        </p>
      )}
    </div>
  );
}
