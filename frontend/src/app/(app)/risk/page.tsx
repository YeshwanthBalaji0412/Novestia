"use client";

import { useRisk, useRiskHistory, useRecomputeRisk } from "@/hooks/use-risk";
import { RiskScoreCard } from "@/components/risk/risk-score-card";
import { SubscoreBreakdown } from "@/components/risk/subscore-breakdown";
import { RiskHistoryChart } from "@/components/risk/risk-history-chart";
import { RiskAIInterpretation } from "@/components/risk/risk-ai-interpretation";

export default function RiskPage() {
  const { data: report, isLoading } = useRisk();
  const { data: history } = useRiskHistory();
  const { mutate: recompute, isPending } = useRecomputeRisk();

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Risk Analysis</h1>
        <button
          onClick={() => recompute()}
          disabled={isPending}
          className="inline-flex h-9 items-center rounded-md border bg-background px-4 text-sm font-medium hover:bg-accent disabled:opacity-50"
        >
          {isPending ? "Computing..." : "Recompute"}
        </button>
      </div>

      {report && (
        <div className="grid gap-6 lg:grid-cols-3">
          <RiskScoreCard score={report.overall_score} />
          <div className="lg:col-span-2">
            <SubscoreBreakdown report={report} />
          </div>
        </div>
      )}

      <div>
        <h2 className="mb-3 text-lg font-semibold">Risk Over Time</h2>
        <RiskHistoryChart points={history ?? []} />
      </div>

      <RiskAIInterpretation />

      {report?.engine_explanation && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-2 font-semibold">Engine Report</h3>
          <pre className="whitespace-pre-wrap text-sm text-muted-foreground">
            {report.engine_explanation}
          </pre>
        </div>
      )}
    </div>
  );
}
