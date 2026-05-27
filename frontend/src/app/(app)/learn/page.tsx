"use client";

import { PageHeader } from "@/components/layout/page-header";
import { MetricCard } from "@/components/learn/metric-card";

const METRICS = [
  { name: "pe_ratio", label: "P/E Ratio", description: "How much investors pay for each dollar of earnings." },
  { name: "eps", label: "Earnings Per Share", description: "How much profit a company makes per share of stock." },
  { name: "market_cap", label: "Market Capitalization", description: "The total value of all a company's shares." },
  { name: "beta", label: "Beta", description: "How much a stock moves compared to the overall market." },
  { name: "dividend_yield", label: "Dividend Yield", description: "The percentage of price paid out as dividends yearly." },
  { name: "expense_ratio", label: "Expense Ratio", description: "The annual fee an ETF charges. Lower is better." },
  { name: "week_52_high", label: "52-Week High", description: "The highest price over the past year." },
  { name: "week_52_low", label: "52-Week Low", description: "The lowest price over the past year." },
];

export default function LearnPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        title="Learn"
        subtitle="Tap any metric for an AI-powered explanation in plain English."
      />
      <div className="grid gap-3 sm:grid-cols-2">
        {METRICS.map((m) => (
          <MetricCard key={m.name} metricName={m.name} label={m.label} description={m.description} />
        ))}
      </div>
    </div>
  );
}
