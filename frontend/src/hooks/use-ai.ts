"use client";

import { useMutation } from "@tanstack/react-query";
import { useApi } from "@/hooks/use-api";
import type { ApiResponse } from "@/types";

interface StockExplanation {
  ticker: string;
  explanation: string | null;
  cached: boolean;
  error?: string;
}

interface RiskExplanation {
  risk_report_id: string;
  interpretation: string | null;
  cached: boolean;
  error?: string;
}

interface MetricExplanation {
  metric: string;
  explanation: string | null;
  cached: boolean;
  error?: string;
}

export function useExplainStock() {
  const api = useApi();
  return useMutation({
    mutationFn: (ticker: string) =>
      api.post<ApiResponse<StockExplanation>>("/api/v1/ai/explain-stock", {
        ticker,
      }),
  });
}

export function useExplainRisk() {
  const api = useApi();
  return useMutation({
    mutationFn: () =>
      api.post<ApiResponse<RiskExplanation>>("/api/v1/ai/explain-risk"),
  });
}

export function useExplainMetric() {
  const api = useApi();
  return useMutation({
    mutationFn: (params: { metric_name: string; ticker?: string }) =>
      api.post<ApiResponse<MetricExplanation>>(
        "/api/v1/ai/explain-metric",
        params,
      ),
  });
}
