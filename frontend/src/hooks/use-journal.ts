"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/hooks/use-api";

interface JournalEntry {
  id: string;
  content: string;
  transaction_id: string | null;
  transaction_summary: {
    ticker: string;
    type: string;
    quantity: string;
    execution_price: string;
  } | null;
  created_at: string;
}

interface PaginatedJournal {
  data: JournalEntry[];
  next_cursor: string | null;
}

export function useJournal(
  limit = 20,
  cursor?: string | null,
  type?: string | null,
) {
  const api = useApi();
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  if (type) params.set("type", type);

  return useQuery({
    queryKey: ["journal", limit, cursor, type],
    queryFn: () =>
      api.get<PaginatedJournal>(`/api/v1/journal?${params.toString()}`),
  });
}

export function useCreateJournalEntry() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) =>
      api.post("/api/v1/journal", { content }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["journal"] });
    },
  });
}
