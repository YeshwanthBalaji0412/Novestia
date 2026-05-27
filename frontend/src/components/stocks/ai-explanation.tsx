"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Skeleton } from "@/components/common/skeleton";
import { useExplainStock } from "@/hooks/use-ai";

interface Props {
  ticker: string;
}

export function AIExplanation({ ticker }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { mutate, data, isPending } = useExplainStock();

  function handleToggle() {
    if (!expanded && !data) {
      mutate(ticker);
    }
    setExpanded(!expanded);
  }

  const explanation = data?.data?.explanation;

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={handleToggle}
        className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-accent/30"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-ai">✦</span>
          <span className="text-sm font-semibold">AI Explanation</span>
        </div>
        <span className="text-xs text-muted-foreground">{expanded ? "−" : "+"}</span>
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
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              )}
              {explanation && (
                <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">
                  {explanation.split("\n\n").map((p, i) => (
                    <p key={i}>{p}</p>
                  ))}
                </div>
              )}
              {data?.data?.error && (
                <p className="text-xs text-muted-foreground">
                  AI explanation is currently unavailable.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
