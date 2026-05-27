import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-background">
      {/* Ambient glow */}
      <div
        className="pointer-events-none absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full opacity-20 blur-[120px]"
        style={{ background: "oklch(0.7 0.18 240)" }}
      />

      <main className="relative flex flex-col items-center gap-8 text-center px-6">
        {/* Logo mark */}
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
          <span className="font-heading text-3xl font-bold text-primary">N</span>
        </div>

        <div className="space-y-4">
          <h1 className="font-heading text-5xl font-bold tracking-tight sm:text-6xl">
            Novestia
          </h1>
          <p className="mx-auto max-w-lg text-lg text-muted-foreground">
            Learn investing with real market data, paper trading, and AI-powered
            insights. No real money. No risk.
          </p>
        </div>

        <div className="flex gap-3">
          <Link
            href="/sign-up?redirect_url=/dashboard"
            className="inline-flex h-11 items-center rounded-lg bg-primary px-6 text-sm font-semibold text-primary-foreground transition-all hover:brightness-110 hover:shadow-[0_0_20px_oklch(0.7_0.18_240_/_0.3)]"
          >
            Get Started
          </Link>
          <Link
            href="/sign-in?redirect_url=/dashboard"
            className="glass-card inline-flex h-11 items-center px-6 text-sm font-semibold transition-all hover:border-primary/30"
          >
            Sign In
          </Link>
        </div>

        {/* Feature pills */}
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {["Real-time prices", "$10k virtual cash", "AI risk analysis", "Trade journal"].map(
            (f) => (
              <span
                key={f}
                className="rounded-full border border-border/50 bg-muted/30 px-3 py-1 text-xs text-muted-foreground"
              >
                {f}
              </span>
            ),
          )}
        </div>
      </main>
    </div>
  );
}
