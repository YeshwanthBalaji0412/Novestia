"use client";

import { useState } from "react";
import { useRisk, useRiskHistory, useRecomputeRisk } from "@/hooks/use-risk";
import { PageHeader } from "@/components/layout/page-header";
import { RiskScoreCard } from "@/components/risk/risk-score-card";
import { SubscoreBreakdown } from "@/components/risk/subscore-breakdown";
import { RiskHistoryChart } from "@/components/risk/risk-history-chart";
import { RiskAIInterpretation } from "@/components/risk/risk-ai-interpretation";
import { EmptyState } from "@/components/common/empty-state";
import { PageSkeleton } from "@/components/common/skeleton";

export default function RiskPage() {
  const { data: report, isLoading, error } = useRisk();
  const { data: history } = useRiskHistory();
  const { mutate: recompute, isPending } = useRecomputeRisk();
  const [recomputeError, setRecomputeError] = useState<string | null>(null);

  function handleRecompute() {
    setRecomputeError(null);
    recompute(undefined, {
      onError: (err) => {
        const msg = err instanceof Error ? err.message : "Rate limited — try again in a minute";
        setRecomputeError(msg);
        setTimeout(() => setRecomputeError(null), 5000);
      },
    });
  }

  if (isLoading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState icon="⚠" title="Failed to load risk data" action={
          <button onClick={() => window.location.reload()} className="glass-card px-4 py-2 text-xs font-semibold uppercase tracking-wider text-primary">Retry</button>
        } />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        title="Risk Analysis"
        action={
          <div className="flex items-center gap-3">
            {recomputeError && (
              <span className="text-xs text-loss">{recomputeError}</span>
            )}
            <button
              onClick={handleRecompute}
              disabled={isPending}
              className="glass-card inline-flex h-9 items-center px-4 text-xs font-semibold uppercase tracking-wider transition-all hover:border-primary/30 hover:glow-blue disabled:opacity-40"
            >
              {isPending ? "Computing..." : "Recompute"}
            </button>
          </div>
        }
      />

      {report && (
        <div className="grid gap-4 lg:grid-cols-3">
          <RiskScoreCard score={report.overall_score} />
          <div className="lg:col-span-2">
            <SubscoreBreakdown report={report} engineExplanation={report.engine_explanation} />
          </div>
        </div>
      )}

      <div>
        <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Risk Over Time</p>
        <RiskHistoryChart points={history ?? []} />
      </div>

      <RiskAIInterpretation />

      {report?.engine_explanation && (
        <div className="glass-card p-4">
          <p className="mb-2 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Engine Report</p>
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted-foreground">
            {report.engine_explanation}
          </pre>
        </div>
      )}
    </div>
  );
}
