"use client";

import { cn } from "@/lib/utils";
import type { RiskReport } from "@/hooks/use-risk";

interface Props {
  report: RiskReport;
}

const SUBSCORE_LABELS: Record<string, string> = {
  concentration: "Concentration",
  sector_concentration: "Sector",
  volatility: "Volatility",
  diversification: "Diversification",
  cash_ratio: "Cash Ratio",
};

function barColor(score: number): string {
  if (score <= 25) return "bg-green-500";
  if (score <= 50) return "bg-yellow-500";
  if (score <= 75) return "bg-orange-500";
  return "bg-red-500";
}

export function SubscoreBreakdown({ report }: Props) {
  const entries = Object.entries(report.subscores) as [
    string,
    { score: number; explanation: string },
  ][];

  return (
    <div className="space-y-4 rounded-lg border bg-card p-4">
      <h3 className="font-semibold">Risk Breakdown</h3>
      {entries.map(([key, subscore]) => (
        <div key={key} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span>{SUBSCORE_LABELS[key] ?? key}</span>
            <span
              className={cn(
                "font-medium tabular-nums",
                subscore.score > 50 ? "text-red-600" : "text-muted-foreground",
              )}
            >
              {subscore.score}/100
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full", barColor(subscore.score))}
              style={{ width: `${subscore.score}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
