"use client";

import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { useUserSync } from "@/hooks/use-user-sync";
import { WebSocketProvider } from "@/providers/websocket-provider";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/portfolio/transactions", label: "Transactions" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/risk", label: "Risk" },
  { href: "/learn", label: "Learn" },
];

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
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
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="text-lg font-semibold">
              Novestia
            </Link>
            <nav className="hidden items-center gap-1 md:flex">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent",
                    pathname === item.href
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <UserButton />
        </header>
        <main className="flex flex-1 flex-col">{children}</main>
      </div>
    </WebSocketProvider>
  );
}
