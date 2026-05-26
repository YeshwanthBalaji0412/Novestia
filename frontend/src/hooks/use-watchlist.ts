"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/hooks/use-api";
import type { ApiResponse, WatchlistItem } from "@/types";

export function useWatchlist() {
  const api = useApi();

  return useQuery({
    queryKey: ["watchlist"],
    queryFn: () =>
      api.get<ApiResponse<WatchlistItem[]>>("/api/v1/watchlist"),
    select: (res) => res.data,
    refetchInterval: 30_000,
  });
}

export function useAddToWatchlist() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticker: string) =>
      api.post(`/api/v1/watchlist/${ticker.toUpperCase()}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticker: string) =>
      api.delete(`/api/v1/watchlist/${ticker.toUpperCase()}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}
