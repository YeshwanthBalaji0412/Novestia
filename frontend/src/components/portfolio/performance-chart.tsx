"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/format";
import type { PerformancePoint } from "@/types";

interface Props {
  points: PerformancePoint[];
}

export function PerformanceChart({ points }: Props) {
  if (points.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border bg-card text-muted-foreground">
        Not enough data for a chart yet. Check back after a few days of trading.
      </div>
    );
  }

  const data = points.map((p) => ({
    date: p.date,
    value: parseFloat(p.value),
  }));

  const isPositive = data[data.length - 1]!.value >= data[0]!.value;
  const color = isPositive ? "#16a34a" : "#dc2626";

  return (
    <div className="h-64 rounded-lg border bg-card p-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            className="text-muted-foreground"
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
            className="text-muted-foreground"
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value) => [formatCurrency(Number(value)), "Value"]}
            labelFormatter={(label) => `Date: ${String(label)}`}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.1}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
