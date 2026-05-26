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
  { href: "/explore", label: "Explore" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/risk", label: "Risk" },
  { href: "/journal", label: "Journal" },
  { href: "/learn", label: "Learn" },
];

const mobileNav = [
  { href: "/dashboard", label: "Home" },
  { href: "/explore", label: "Explore" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/watchlist", label: "Watch" },
  { href: "/settings", label: "More" },
];

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: user, isLoading } = useUserSync();

  // Initialize theme from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") {
      document.documentElement.classList.add("dark");
    } else if (saved === "light") {
      document.documentElement.classList.remove("dark");
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      document.documentElement.classList.add("dark");
    }
  }, []);

  useEffect(() => {
    if (!isLoading && user && !user.onboarded) {
      router.replace("/onboarding");
    }
  }, [user, isLoading, router]);

  return (
    <WebSocketProvider>
      <div className="flex min-h-full flex-col pb-14 md:pb-0">
        {/* Desktop header */}
        <header className="flex items-center justify-between border-b px-4 py-3 sm:px-6">
          <div className="flex items-center gap-4 sm:gap-6">
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
                    pathname === item.href ||
                      (item.href !== "/dashboard" &&
                        pathname.startsWith(item.href))
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground",
                  )}
                >
                  {item.label}
                </Link>
              ))}
              <Link
                href="/settings"
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent",
                  pathname === "/settings"
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground",
                )}
              >
                Settings
              </Link>
            </nav>
          </div>
          <UserButton />
        </header>

        {/* Main content */}
        <main className="flex flex-1 flex-col">{children}</main>

        {/* Mobile bottom nav */}
        <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t bg-background md:hidden">
          {mobileNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 flex-col items-center py-2 text-xs font-medium transition-colors",
                pathname === item.href ||
                  (item.href !== "/dashboard" &&
                    pathname.startsWith(item.href))
                  ? "text-primary"
                  : "text-muted-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </WebSocketProvider>
  );
}
