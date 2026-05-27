"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatCurrency } from "@/lib/format";
import { chartColors, chartTooltip } from "@/lib/charts/theme";
import type { PerformancePoint } from "@/types";

interface Props {
  points: PerformancePoint[];
}

export function PortfolioSparkline({ points }: Props) {
  if (points.length < 2) return null;

  const data = points.map((p) => ({
    date: p.date,
    value: parseFloat(p.value) || 0,
  }));

  const isPositive = data[data.length - 1]!.value >= data[0]!.value;
  const color = isPositive ? chartColors.positive : chartColors.negative;

  return (
    <div className="glass-card h-[60px] overflow-hidden px-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.15} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Tooltip
            contentStyle={chartTooltip.contentStyle as React.CSSProperties}
            formatter={(value) => [formatCurrency(Number(value)), ""]}
            labelFormatter={(label) => String(label)}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill="url(#sparkFill)"
            strokeWidth={1.5}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
