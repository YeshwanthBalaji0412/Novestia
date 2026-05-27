/**
 * Novestia chart theme — shared across all Recharts instances.
 * Ensures visual consistency between performance, risk, and price charts.
 */

export const chartColors = {
  positive: "oklch(0.78 0.2 155)",
  negative: "oklch(0.7 0.23 18)",
  neutral: "oklch(0.7 0.27 290)",
  info: "oklch(0.75 0.2 240)",
  warning: "oklch(0.8 0.17 80)",
} as const;

export const chartAxis = {
  fontSize: 10,
  fill: "oklch(0.55 0.01 260)",
} as const;

export const chartTooltip = {
  contentStyle: {
    background: "oklch(0.14 0.006 260 / 0.9)",
    border: "1px solid oklch(1 0 0 / 0.1)",
    borderRadius: "8px",
    backdropFilter: "blur(12px)",
    fontSize: 12,
    color: "oklch(0.93 0 0)",
  },
} as const;

export const chartActiveDot = (color: string) => ({
  r: 4,
  stroke: color,
  strokeWidth: 2,
  fill: "oklch(0.14 0.006 260)",
});

/** Returns a gradient definition ID and the color based on trend direction */
export function getChartGradient(isPositive: boolean) {
  return {
    id: isPositive ? "gradPositive" : "gradNegative",
    color: isPositive ? chartColors.positive : chartColors.negative,
  };
}
