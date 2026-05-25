"use client";

import { UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useUserSync } from "@/hooks/use-user-sync";
import { WebSocketProvider } from "@/providers/websocket-provider";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading } = useUserSync();

  useEffect(() => {
    if (!isLoading && user && !user.onboarded) {
      router.replace("/onboarding");
    }
  }, [user, isLoading, router]);

  return (
    <WebSocketProvider>
      <div className="flex min-h-full flex-col">
        <header className="flex items-center justify-between border-b px-6 py-3">
          <span className="text-lg font-semibold">Novestia</span>
          <UserButton />
        </header>
        <main className="flex flex-1 flex-col">{children}</main>
      </div>
    </WebSocketProvider>
  );
}
