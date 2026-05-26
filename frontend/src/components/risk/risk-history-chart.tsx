"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RiskHistoryPoint } from "@/hooks/use-risk";

interface Props {
  points: RiskHistoryPoint[];
}

export function RiskHistoryChart({ points }: Props) {
  if (points.length < 2) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border bg-card text-sm text-muted-foreground">
        Risk history will appear after a few trades.
      </div>
    );
  }

  const data = [...points].reverse().map((p) => ({
    date: new Date(p.computed_at).toLocaleDateString(),
    score: p.overall_score,
  }));

  return (
    <div className="h-48 rounded-lg border bg-card p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fontSize: 10 }} />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10 }}
          />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#6366f1"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
