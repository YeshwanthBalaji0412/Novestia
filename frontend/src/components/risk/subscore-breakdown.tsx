"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { RiskReport } from "@/hooks/use-risk";

interface Props {
  report: RiskReport;
  engineExplanation?: string;
}

const SUBSCORE_META: Record<string, { label: string; extractContext: (text: string) => string }> = {
  concentration: {
    label: "Concentration",
    extractContext: (text) => {
      const match = text.match(/Concentration risk:.*?\. (.*?)$/m);
      return match?.[1] ?? "";
    },
  },
  sector_concentration: {
    label: "Sector Exposure",
    extractContext: (text) => {
      const match = text.match(/Sector concentration:.*?\. (.*?)$/m);
      return match?.[1] ?? "";
    },
  },
  volatility: {
    label: "Volatility",
    extractContext: (text) => {
      const match = text.match(/Volatility:.*?\. (.*?)$/m);
      return match?.[1] ?? "";
    },
  },
  diversification: {
    label: "Diversification",
    extractContext: (text) => {
      const match = text.match(/Diversification:.*?\. (.*?)$/m);
      return match?.[1] ?? "";
    },
  },
  cash_ratio: {
    label: "Cash Ratio",
    extractContext: (text) => {
      const match = text.match(/Cash ratio:.*?\. (.*?)$/m);
      return match?.[1] ?? "";
    },
  },
};

function barStyle(score: number) {
  if (score <= 25) return { bg: "bg-neon-green/20", fill: "bg-neon-green", text: "text-gain" };
  if (score <= 50) return { bg: "bg-neon-amber/20", fill: "bg-neon-amber", text: "text-warning" };
  if (score <= 75) return { bg: "bg-neon-red/15", fill: "bg-neon-red/80", text: "text-loss" };
  return { bg: "bg-neon-red/20", fill: "bg-neon-red", text: "text-loss" };
}

export function SubscoreBreakdown({ report, engineExplanation }: Props) {
  const entries = Object.entries(report.subscores) as [
    string,
    { score: number; explanation: string },
  ][];

  return (
    <div className="glass-card space-y-4 p-4">
      <h3 className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        Risk Breakdown
      </h3>
      {entries.map(([key, subscore], i) => {
        const meta = SUBSCORE_META[key];
        const style = barStyle(subscore.score);

        // Extract context from engine explanation
        const context = engineExplanation && meta
          ? meta.extractContext(engineExplanation)
          : subscore.explanation;

        return (
          <div key={key} className="space-y-1.5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-medium">
                  {meta?.label ?? key}
                </span>
                {context && (
                  <span className="ml-2 text-[10px] text-muted-foreground">
                    {context}
                  </span>
                )}
              </div>
              <span className={cn("font-numbers text-xs font-semibold", style.text)}>
                {subscore.score}
              </span>
            </div>
            <div className={cn("h-1.5 overflow-hidden rounded-full", style.bg)}>
              <motion.div
                className={cn("h-full rounded-full", style.fill)}
                initial={{ width: 0 }}
                animate={{ width: `${subscore.score}%` }}
                transition={{ duration: 0.8, delay: i * 0.1, ease: "easeOut" }}
                style={{
                  boxShadow:
                    subscore.score > 50
                      ? "0 0 8px var(--neon-red)"
                      : undefined,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
