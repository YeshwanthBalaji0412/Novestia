"use client";

import { useUserSync } from "@/hooks/use-user-sync";

export default function DashboardPage() {
  const { data: user, isLoading } = useUserSync();

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-muted-foreground">
        Welcome{user?.display_name ? `, ${user.display_name}` : ""}. Your
        portfolio is ready.
      </p>
    </div>
  );
}
