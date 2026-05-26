"use client";

import { cn } from "@/lib/utils";

interface Props {
  score: number;
  label?: string;
}

function getScoreColor(score: number): string {
  if (score <= 25) return "text-green-600";
  if (score <= 50) return "text-yellow-600";
  if (score <= 75) return "text-orange-600";
  return "text-red-600";
}

function getScoreLabel(score: number): string {
  if (score <= 25) return "Low Risk";
  if (score <= 50) return "Moderate";
  if (score <= 75) return "Elevated";
  return "High Risk";
}

export function RiskScoreCard({ score, label }: Props) {
  return (
    <div className="rounded-lg border bg-card p-6 text-center">
      <p className="text-sm text-muted-foreground">{label ?? "Risk Score"}</p>
      <p className={cn("mt-2 text-5xl font-bold tabular-nums", getScoreColor(score))}>
        {score}
      </p>
      <p className={cn("mt-1 text-sm font-medium", getScoreColor(score))}>
        {getScoreLabel(score)} / 100
      </p>
    </div>
  );
}
