import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-full flex-col items-center justify-center px-4">
      {/* Ambient glow */}
      <div
        className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[400px] w-[400px] rounded-full opacity-15 blur-[100px]"
        style={{ background: "oklch(0.7 0.18 240)" }}
      />

      {/* Logo */}
      <Link href="/" className="mb-8 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
          <span className="font-heading text-sm font-bold text-primary">N</span>
        </div>
        <span className="font-heading text-lg font-semibold tracking-tight">Novestia</span>
      </Link>

      {children}
    </div>
  );
}
