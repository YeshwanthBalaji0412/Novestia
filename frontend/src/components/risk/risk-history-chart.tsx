"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "@/components/common/empty-state";
import { chartAxis, chartColors, chartTooltip } from "@/lib/charts/theme";
import type { RiskHistoryPoint } from "@/hooks/use-risk";

interface Props {
  points: RiskHistoryPoint[];
}

export function RiskHistoryChart({ points }: Props) {
  if (points.length < 2) {
    return (
      <div className="h-48">
        <EmptyState icon="📉" title="Risk history will appear after a few trades" />
      </div>
    );
  }

  const data = [...points].reverse().map((p) => ({
    date: new Date(p.computed_at).toLocaleDateString(),
    score: p.overall_score,
  }));

  return (
    <div className="glass-card h-48 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={chartColors.neutral} stopOpacity={0.2} />
              <stop offset="100%" stopColor={chartColors.neutral} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={chartAxis} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={chartAxis} axisLine={false} tickLine={false} width={30} />
          <Tooltip contentStyle={chartTooltip.contentStyle as React.CSSProperties} />
          <Area
            type="monotone"
            dataKey="score"
            stroke={chartColors.neutral}
            fill="url(#riskFill)"
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
