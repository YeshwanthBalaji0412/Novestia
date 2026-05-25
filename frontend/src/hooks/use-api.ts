"use client";

import { useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import { createApiClient } from "@/lib/api/client";

export function useApi() {
  const { getToken } = useAuth();

  return useMemo(
    () => ({
      get: async <T>(path: string) => {
        const token = await getToken();
        return createApiClient(token).get<T>(path);
      },
      post: async <T>(path: string, body?: unknown) => {
        const token = await getToken();
        return createApiClient(token).post<T>(path, body);
      },
      patch: async <T>(path: string, body?: unknown) => {
        const token = await getToken();
        return createApiClient(token).patch<T>(path, body);
      },
      delete: async <T>(path: string) => {
        const token = await getToken();
        return createApiClient(token).delete<T>(path);
      },
    }),
    [getToken],
  );
}
