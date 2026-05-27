"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatPercent } from "@/lib/format";
import { chartTooltip } from "@/lib/charts/theme";
import type { HoldingSummary } from "@/types";

interface Props {
  holdings: HoldingSummary[];
  cashPercent: number;
}

const SECTOR_COLORS = [
  "oklch(0.75 0.2 240)",   // blue
  "oklch(0.78 0.2 155)",   // green
  "oklch(0.7 0.27 290)",   // purple
  "oklch(0.8 0.17 80)",    // amber
  "oklch(0.7 0.23 18)",    // red
  "oklch(0.7 0.15 200)",   // teal
  "oklch(0.75 0.12 320)",  // pink
  "oklch(0.65 0.1 60)",    // brown
];

const CASH_COLOR = "oklch(0.4 0 0)";

export function SectorDonut({ holdings, cashPercent }: Props) {
  const sectorMap = new Map<string, number>();

  for (const h of holdings) {
    const sector = h.sector ?? "Other";
    const weight = parseFloat(h.weight);
    sectorMap.set(sector, (sectorMap.get(sector) ?? 0) + weight);
  }

  const data = [...sectorMap.entries()]
    .map(([name, value]) => ({ name, value: Math.round(value * 10) / 10 }))
    .sort((a, b) => b.value - a.value);

  if (cashPercent > 0.5) {
    data.push({ name: "Cash", value: Math.round(cashPercent * 10) / 10 });
  }

  if (data.length === 0) return null;

  return (
    <div className="glass-card p-4">
      <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        Sector Allocation
      </p>
      <div className="flex items-center gap-4">
        <div className="h-[120px] w-[120px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={55}
                paddingAngle={2}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell
                    key={entry.name}
                    fill={
                      entry.name === "Cash"
                        ? CASH_COLOR
                        : SECTOR_COLORS[index % SECTOR_COLORS.length]
                    }
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={chartTooltip.contentStyle as React.CSSProperties}
                formatter={(value) => [formatPercent(Number(value), { withSign: false }), ""]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-col gap-1.5 overflow-hidden">
          {data.map((entry, i) => (
            <div key={entry.name} className="flex items-center gap-2 text-xs">
              <div
                className="h-2 w-2 shrink-0 rounded-full"
                style={{
                  backgroundColor:
                    entry.name === "Cash"
                      ? CASH_COLOR
                      : SECTOR_COLORS[i % SECTOR_COLORS.length],
                }}
              />
              <span className="truncate text-muted-foreground">{entry.name}</span>
              <span className="ml-auto font-numbers">{entry.value}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
