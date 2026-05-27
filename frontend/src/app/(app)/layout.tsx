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

  useEffect(() => {
    // Force dark mode — this is a dark-first app
    document.documentElement.classList.add("dark");
  }, []);

  useEffect(() => {
    if (!isLoading && user && !user.onboarded) {
      router.replace("/onboarding");
    }
  }, [user, isLoading, router]);

  const isActive = (href: string) =>
    pathname === href || (href !== "/dashboard" && pathname.startsWith(href));

  return (
    <WebSocketProvider>
      <div className="flex min-h-full flex-col pb-14 md:pb-0">
        {/* ── Top bar ── */}
        <header className="glass-card-solid sticky top-0 z-30 flex items-center justify-between rounded-none border-x-0 border-t-0 px-4 py-2.5 sm:px-6">
          <div className="flex items-center gap-5">
            {/* Logo */}
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
                <span className="font-heading text-sm font-bold text-primary-foreground">
                  N
                </span>
              </div>
              <span className="hidden font-heading text-base font-semibold tracking-tight sm:block">
                Novestia
              </span>
            </Link>

            {/* Desktop nav */}
            <nav className="hidden items-center gap-0.5 md:flex">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "relative rounded-md px-3 py-1.5 text-xs font-medium uppercase tracking-wider transition-all",
                    isActive(item.href)
                      ? "text-primary"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {item.label}
                  {isActive(item.href) && (
                    <span className="absolute -bottom-2.5 left-1/2 h-px w-6 -translate-x-1/2 bg-primary" />
                  )}
                </Link>
              ))}
              <Link
                href="/settings"
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium uppercase tracking-wider transition-all",
                  isActive("/settings")
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Settings
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "h-7 w-7",
                },
              }}
            />
          </div>
        </header>

        {/* ── Content ── */}
        <main className="flex flex-1 flex-col">{children}</main>

        {/* ── Mobile bottom nav ── */}
        <nav className="glass-card-solid fixed bottom-0 left-0 right-0 z-40 flex rounded-none border-x-0 border-b-0 md:hidden">
          {mobileNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium uppercase tracking-wider transition-colors",
                isActive(item.href)
                  ? "text-primary"
                  : "text-muted-foreground",
              )}
            >
              {item.label}
              {isActive(item.href) && (
                <span className="h-0.5 w-4 rounded-full bg-primary" />
              )}
            </Link>
          ))}
        </nav>
      </div>
    </WebSocketProvider>
  );
}
