"use client";

import { MetricCard } from "@/components/learn/metric-card";

const METRICS = [
  {
    name: "pe_ratio",
    label: "P/E Ratio",
    description:
      "How much investors pay for each dollar of earnings. Higher means more expensive relative to profits.",
  },
  {
    name: "eps",
    label: "Earnings Per Share (EPS)",
    description:
      "How much profit a company makes per share of stock. Higher generally means more profitable.",
  },
  {
    name: "market_cap",
    label: "Market Capitalization",
    description:
      "The total value of all a company's shares. Tells you how big the company is.",
  },
  {
    name: "beta",
    label: "Beta",
    description:
      "How much a stock moves compared to the overall market. Beta > 1 means more volatile.",
  },
  {
    name: "dividend_yield",
    label: "Dividend Yield",
    description:
      "The percentage of a stock's price paid out as dividends each year.",
  },
  {
    name: "expense_ratio",
    label: "Expense Ratio",
    description:
      "The annual fee an ETF charges, expressed as a percentage. Lower is better for investors.",
  },
  {
    name: "week_52_high",
    label: "52-Week High",
    description:
      "The highest price a stock has traded at over the past year.",
  },
  {
    name: "week_52_low",
    label: "52-Week Low",
    description: "The lowest price a stock has traded at over the past year.",
  },
];

export default function LearnPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Learn</h1>
        <p className="mt-1 text-muted-foreground">
          Tap any metric to get an AI-powered explanation in plain English.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {METRICS.map((m) => (
          <MetricCard
            key={m.name}
            metricName={m.name}
            label={m.label}
            description={m.description}
          />
        ))}
      </div>
    </div>
  );
}
