"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/format";
import { EmptyState } from "@/components/common/empty-state";
import { chartAxis, chartTooltip, chartColors, chartActiveDot } from "@/lib/charts/theme";
import type { PerformancePoint } from "@/types";

interface Props {
  points: PerformancePoint[];
}

export function PerformanceChart({ points }: Props) {
  if (points.length < 2) {
    return (
      <div className="h-64">
        <EmptyState icon="📈" title="Not enough data yet" message="Check back after a few days of trading." />
      </div>
    );
  }

  const data = points.map((p) => ({
    date: p.date,
    value: parseFloat(p.value) || 0,
  }));

  const isPositive = data[data.length - 1]!.value >= data[0]!.value;
  const stroke = isPositive ? chartColors.positive : chartColors.negative;
  const fillId = isPositive ? "fillGreen" : "fillRed";

  return (
    <div className="glass-card h-64 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="fillGreen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={chartColors.positive} stopOpacity={0.25} />
              <stop offset="100%" stopColor={chartColors.positive} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="fillRed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={chartColors.negative} stopOpacity={0.25} />
              <stop offset="100%" stopColor={chartColors.negative} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={chartAxis}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={chartAxis}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
            domain={["auto", "auto"]}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip
            contentStyle={chartTooltip.contentStyle as React.CSSProperties}
            formatter={(value) => [formatCurrency(Number(value)), "Value"]}
            labelFormatter={(label) => String(label)}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={stroke}
            fill={`url(#${fillId})`}
            strokeWidth={2}
            dot={false}
            activeDot={chartActiveDot(stroke)}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
