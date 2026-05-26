"use client";

import { useState } from "react";
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
    <div className="rounded-lg border bg-card">
      <button
        onClick={handleExpand}
        className="w-full p-4 text-left hover:bg-accent/50"
      >
        <h3 className="font-semibold">{label}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </button>
      {expanded && (
        <div className="border-t px-4 pb-4 pt-3">
          {isPending && (
            <div className="space-y-2">
              <div className="h-4 w-full animate-pulse rounded bg-muted" />
              <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
            </div>
          )}
          {explanation && (
            <p className="text-sm text-muted-foreground">{explanation}</p>
          )}
          {data?.data?.error && (
            <p className="text-sm text-muted-foreground">
              AI explanation unavailable.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
