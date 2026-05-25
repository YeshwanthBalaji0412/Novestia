/**
 * WebSocket price stream client with reconnection and subscription management.
 *
 * Creates a single WS connection per session. Handles reconnect with
 * exponential backoff. Manages a subscription set and re-subscribes on reconnect.
 */

export type PriceUpdate = {
  ticker: string;
  price: string;
  timestamp: string;
};

export type PriceStreamStatus = "connecting" | "connected" | "disconnected";

export type PriceListener = (update: PriceUpdate) => void;
export type StatusListener = (status: PriceStreamStatus) => void;

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;

export class PriceStream {
  private ws: WebSocket | null = null;
  private subscriptions = new Set<string>();
  private listeners = new Set<PriceListener>();
  private statusListeners = new Set<StatusListener>();
  private status: PriceStreamStatus = "disconnected";
  private reconnectDelay = RECONNECT_BASE_DELAY;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private token: string | null = null;
  private destroyed = false;

  connect(token: string): void {
    this.token = token;
    this.destroyed = false;
    this._connect();
  }

  destroy(): void {
    this.destroyed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._setStatus("disconnected");
  }

  subscribe(tickers: string[]): void {
    const newTickers = tickers.filter((t) => !this.subscriptions.has(t));
    if (newTickers.length === 0) return;

    for (const t of newTickers) {
      this.subscriptions.add(t.toUpperCase());
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({ action: "subscribe", tickers: newTickers }),
      );
    }
  }

  unsubscribe(tickers: string[]): void {
    const removeTickers = tickers.filter((t) => this.subscriptions.has(t));
    if (removeTickers.length === 0) return;

    for (const t of removeTickers) {
      this.subscriptions.delete(t.toUpperCase());
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({ action: "unsubscribe", tickers: removeTickers }),
      );
    }
  }

  onPrice(listener: PriceListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  getStatus(): PriceStreamStatus {
    return this.status;
  }

  private _connect(): void {
    if (this.destroyed || !this.token) return;

    this._setStatus("connecting");
    const url = `${WS_BASE_URL}/api/v1/ws/prices?token=${this.token}`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this._setStatus("connected");
      this.reconnectDelay = RECONNECT_BASE_DELAY;

      // Re-subscribe to all active tickers
      if (this.subscriptions.size > 0) {
        this.ws?.send(
          JSON.stringify({
            action: "subscribe",
            tickers: Array.from(this.subscriptions),
          }),
        );
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as Record<
          string,
          unknown
        >;
        if (data["type"] === "price") {
          const update: PriceUpdate = {
            ticker: data["ticker"] as string,
            price: data["price"] as string,
            timestamp: data["timestamp"] as string,
          };
          for (const listener of this.listeners) {
            listener(update);
          }
        }
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this._setStatus("disconnected");
      this._scheduleReconnect();
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror
    };
  }

  private _scheduleReconnect(): void {
    if (this.destroyed) return;
    this.reconnectTimer = setTimeout(() => {
      this._connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(
      this.reconnectDelay * 2,
      RECONNECT_MAX_DELAY,
    );
  }

  private _setStatus(status: PriceStreamStatus): void {
    this.status = status;
    for (const listener of this.statusListeners) {
      listener(status);
    }
  }
}
