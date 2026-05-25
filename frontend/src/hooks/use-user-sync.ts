"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { createApiClient } from "@/lib/api/client";
import type { ApiResponse, UserResponse } from "@/types";

export function useUserSync() {
  const { isSignedIn, getToken } = useAuth();

  return useQuery({
    queryKey: ["user", "sync"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) {
        throw new Error("No auth token available");
      }
      const client = createApiClient(token);
      return client.post<ApiResponse<UserResponse>>("/api/v1/users/sync");
    },
    enabled: isSignedIn === true,
    staleTime: 5 * 60 * 1000,
    retry: 2,
    select: (data) => data.data,
  });
}
