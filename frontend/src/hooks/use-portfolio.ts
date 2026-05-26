"use client";

import { useQuery } from "@tanstack/react-query";
import { useApi } from "@/hooks/use-api";
import type {
  ApiResponse,
  PaginatedTransactions,
  PerformanceData,
  PortfolioSummary,
} from "@/types";

export function usePortfolio() {
  const api = useApi();

  return useQuery({
    queryKey: ["portfolio"],
    queryFn: () =>
      api.get<ApiResponse<PortfolioSummary>>("/api/v1/portfolio"),
    select: (res) => res.data,
    refetchInterval: 30_000,
  });
}

export function useTransactions(
  limit = 20,
  cursor?: string | null,
  ticker?: string | null,
) {
  const api = useApi();

  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  if (ticker) params.set("ticker", ticker);

  return useQuery({
    queryKey: ["transactions", limit, cursor, ticker],
    queryFn: () =>
      api.get<PaginatedTransactions>(
        `/api/v1/portfolio/transactions?${params.toString()}`,
      ),
  });
}

export function usePerformance(range = "1M") {
  const api = useApi();

  return useQuery({
    queryKey: ["performance", range],
    queryFn: () =>
      api.get<ApiResponse<PerformanceData>>(
        `/api/v1/portfolio/performance?range=${range}`,
      ),
    select: (res) => res.data,
  });
}
