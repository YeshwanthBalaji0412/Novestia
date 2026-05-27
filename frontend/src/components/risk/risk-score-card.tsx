"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Props {
  score: number;
  label?: string;
  compact?: boolean;
}

function getScoreColor(score: number) {
  if (score <= 25) return { color: "var(--neon-green)", label: "Low Risk", glow: "glow-green" };
  if (score <= 50) return { color: "var(--neon-amber)", label: "Moderate", glow: "glow-amber" };
  if (score <= 75) return { color: "var(--neon-red)", label: "Elevated", glow: "glow-red" };
  return { color: "var(--neon-red)", label: "High Risk", glow: "glow-red" };
}

export function RiskScoreCard({ score, label, compact }: Props) {
  const { color, label: scoreLabel, glow } = getScoreColor(score);
  const ringSize = compact ? 100 : 160;
  const strokeWidth = compact ? 6 : 8;
  const radius = (ringSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <div className={cn("glass-card text-center", glow, compact ? "p-4" : "p-6")}>
      <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
        {label ?? "Risk Score"}
      </p>

      {/* Ring gauge */}
      <div className="relative mx-auto mt-3" style={{ width: ringSize, height: ringSize }}>
        <svg
          width={ringSize}
          height={ringSize}
          className="-rotate-90"
        >
          {/* Background track */}
          <circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            fill="none"
            stroke="oklch(1 0 0 / 0.06)"
            strokeWidth={strokeWidth}
          />
          {/* Animated progress arc */}
          <motion.circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - progress }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>

        {/* Center score */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="font-numbers font-bold leading-none"
            style={{ color, fontSize: compact ? 28 : 44 }}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            {score}
          </motion.span>
          {!compact && (
            <span className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
              / 100
            </span>
          )}
        </div>
      </div>

      <motion.p
        className="mt-2 text-sm font-semibold"
        style={{ color }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        {scoreLabel}
      </motion.p>
    </div>
  );
}
