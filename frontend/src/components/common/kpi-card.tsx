"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/common/skeleton";
import { type Accent, accentTextClass, glowClass } from "@/styles/design-tokens";

interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  accent?: Accent;
  loading?: boolean;
  index?: number;
  className?: string;
}

export function KpiCard({
  label,
  value,
  delta,
  accent,
  loading,
  index = 0,
  className,
}: KpiCardProps) {
  if (loading) return <KpiCardSkeleton />;

  return (
    <motion.div
      className={cn(
        "glass-card hud-corners p-4",
        accent && glowClass[accent],
        className
      )}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
    >
      <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p className="mt-1.5 font-numbers text-2xl font-bold leading-none truncate" title={value}>
        {value}
      </p>
      {delta && accent && (
        <p
          className={cn(
            "mt-1.5 font-numbers text-sm font-semibold",
            accentTextClass[accent],
          )}
        >
          {delta}
        </p>
      )}
    </motion.div>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="glass-card p-4 space-y-3">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-28" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}
