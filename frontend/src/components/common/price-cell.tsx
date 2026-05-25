"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface PriceCellProps {
  price: string | null | undefined;
  previousPrice?: string | null;
  className?: string;
}

/**
 * Displays a price that briefly flashes green (up) or red (down)
 * when the value changes. Uses CSS animation triggered by key change.
 */
export function PriceCell({
  price,
  previousPrice,
  className,
}: PriceCellProps) {
  const flash = useMemo(() => {
    if (!price || !previousPrice) return null;
    const current = parseFloat(price);
    const previous = parseFloat(previousPrice);
    if (current > previous) return "up" as const;
    if (current < previous) return "down" as const;
    return null;
  }, [price, previousPrice]);

  const displayPrice = price ?? "—";

  return (
    <span
      // Key forces remount → re-triggers the CSS animation on each price change
      key={price ?? "none"}
      className={cn(
        "tabular-nums",
        flash === "up" && "animate-flash-green",
        flash === "down" && "animate-flash-red",
        className,
      )}
    >
      {displayPrice}
    </span>
  );
}
