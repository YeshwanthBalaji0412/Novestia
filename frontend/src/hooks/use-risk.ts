"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/hooks/use-api";
import type { ApiResponse } from "@/types";

export interface RiskSubscore {
  score: number;
  explanation: string;
}

export interface RiskReport {
  id: string;
  overall_score: number;
  subscores: {
    concentration: RiskSubscore;
    sector_concentration: RiskSubscore;
    volatility: RiskSubscore;
    diversification: RiskSubscore;
    cash_ratio: RiskSubscore;
  };
  engine_explanation: string;
  ai_interpretation: string | null;
  computed_at: string;
}

export interface RiskHistoryPoint {
  overall_score: number;
  computed_at: string;
}

export function useRisk() {
  const api = useApi();

  return useQuery({
    queryKey: ["risk"],
    queryFn: () =>
      api.get<ApiResponse<RiskReport>>("/api/v1/portfolio/risk"),
    select: (res) => res.data,
  });
}

export function useRiskHistory(limit = 30) {
  const api = useApi();

  return useQuery({
    queryKey: ["risk-history", limit],
    queryFn: () =>
      api.get<ApiResponse<RiskHistoryPoint[]>>(
        `/api/v1/portfolio/risk/history?limit=${limit}`,
      ),
    select: (res) => res.data,
  });
}

export function useRecomputeRisk() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      api.post<ApiResponse<RiskReport>>("/api/v1/portfolio/risk/recompute"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["risk"] });
      void queryClient.invalidateQueries({ queryKey: ["risk-history"] });
    },
  });
}
