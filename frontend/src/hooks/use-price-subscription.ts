"use client";

import { useEffect, useMemo, useRef } from "react";
import { useWebSocket } from "@/providers/websocket-provider";
import type { PriceUpdate } from "@/lib/ws/price-stream";

/**
 * Subscribe to live price updates for a set of tickers.
 * Subscribes on mount, unsubscribes on unmount.
 *
 * @returns A map of ticker → latest PriceUpdate
 */
export function usePriceSubscription(
  tickers: string[],
): Record<string, PriceUpdate | undefined> {
  const { subscribe, unsubscribe, prices } = useWebSocket();

  // Stable reference for the ticker list — only changes when the actual tickers change
  const tickerKey = tickers.map((t) => t.toUpperCase()).join(",");
  const upperTickers = useMemo(
    () => tickers.map((t) => t.toUpperCase()),
    [tickerKey], // eslint-disable-line react-hooks/exhaustive-deps
  );

  // Track previous tickers for cleanup
  const prevTickersRef = useRef<string[]>([]);

  useEffect(() => {
    if (upperTickers.length === 0) return;
    subscribe(upperTickers);
    prevTickersRef.current = upperTickers;
    return () => {
      unsubscribe(prevTickersRef.current);
    };
  }, [upperTickers, subscribe, unsubscribe]);

  return useMemo(() => {
    const result: Record<string, PriceUpdate | undefined> = {};
    for (const ticker of upperTickers) {
      result[ticker] = prices[ticker];
    }
    return result;
  }, [upperTickers, prices]);
}
