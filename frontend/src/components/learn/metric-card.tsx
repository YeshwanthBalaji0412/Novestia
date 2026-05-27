"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Skeleton } from "@/components/common/skeleton";
import { useExplainMetric } from "@/hooks/use-ai";

interface Props {
  metricName: string;
  label: string;
  description: string;
}

export function MetricCard({ metricName, label, description }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { mutate, data, isPending } = useExplainMetric();

  function handleExpand() {
    if (!expanded && !data) {
      mutate({ metric_name: metricName });
    }
    setExpanded(!expanded);
  }

  const explanation = data?.data?.explanation;

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={handleExpand}
        className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-accent/30"
      >
        <div>
          <h3 className="text-sm font-semibold">{label}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        </div>
        <span className="ml-3 text-xs text-muted-foreground">
          {expanded ? "−" : "+"}
        </span>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border/30 px-4 pb-4 pt-3">
              {isPending && (
                <div className="space-y-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              )}
              {explanation && (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {explanation}
                </p>
              )}
              {data?.data?.error && (
                <p className="text-xs text-muted-foreground">
                  AI explanation unavailable.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
