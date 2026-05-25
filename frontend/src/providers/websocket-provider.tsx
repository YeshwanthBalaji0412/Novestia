"use client";

import { useAuth } from "@clerk/nextjs";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  PriceStream,
  type PriceStreamStatus,
  type PriceUpdate,
} from "@/lib/ws/price-stream";

type PriceStore = Record<string, PriceUpdate>;

interface WebSocketContextValue {
  subscribe: (tickers: string[]) => void;
  unsubscribe: (tickers: string[]) => void;
  prices: PriceStore;
  status: PriceStreamStatus;
}

const WebSocketContext = createContext<WebSocketContextValue>({
  subscribe: () => {},
  unsubscribe: () => {},
  prices: {},
  status: "disconnected",
});

export function WebSocketProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { getToken, isSignedIn } = useAuth();
  const streamRef = useRef<PriceStream | null>(null);
  const [prices, setPrices] = useState<PriceStore>({});
  const [status, setStatus] = useState<PriceStreamStatus>("disconnected");

  useEffect(() => {
    if (!isSignedIn) return;

    const stream = new PriceStream();
    streamRef.current = stream;

    const unsubPrice = stream.onPrice((update) => {
      setPrices((prev) => ({ ...prev, [update.ticker]: update }));
    });

    const unsubStatus = stream.onStatus((s) => {
      setStatus(s);
    });

    // Get token and connect
    getToken().then((token) => {
      if (token) {
        stream.connect(token);
      }
    });

    return () => {
      unsubPrice();
      unsubStatus();
      stream.destroy();
      streamRef.current = null;
    };
  }, [isSignedIn, getToken]);

  const subscribe = useCallback((tickers: string[]) => {
    streamRef.current?.subscribe(tickers);
  }, []);

  const unsubscribe = useCallback((tickers: string[]) => {
    streamRef.current?.unsubscribe(tickers);
  }, []);

  return (
    <WebSocketContext.Provider
      value={{ subscribe, unsubscribe, prices, status }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  return useContext(WebSocketContext);
}
