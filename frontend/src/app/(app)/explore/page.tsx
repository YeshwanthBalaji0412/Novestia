"use client";

import { StockSearch } from "@/components/common/stock-search";

const POPULAR = [
  { ticker: "AAPL", name: "Apple" },
  { ticker: "MSFT", name: "Microsoft" },
  { ticker: "GOOGL", name: "Alphabet (Google)" },
  { ticker: "AMZN", name: "Amazon" },
  { ticker: "NVDA", name: "NVIDIA" },
  { ticker: "TSLA", name: "Tesla" },
  { ticker: "META", name: "Meta (Facebook)" },
  { ticker: "JPM", name: "JPMorgan Chase" },
  { ticker: "V", name: "Visa" },
  { ticker: "JNJ", name: "Johnson & Johnson" },
  { ticker: "VOO", name: "S&P 500 ETF" },
  { ticker: "QQQ", name: "Nasdaq 100 ETF" },
  { ticker: "VTI", name: "Total Stock Market ETF" },
  { ticker: "BND", name: "Total Bond Market ETF" },
  { ticker: "ARKK", name: "ARK Innovation ETF" },
];

export default function ExplorePage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-bold sm:text-2xl">Explore Stocks</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search by company name or ticker symbol. Click any stock to view
          details and trade.
        </p>
      </div>

      <StockSearch
        showWatchlistButton
        placeholder="Search stocks (e.g. Apple, Tesla, Microsoft, VOO...)"
      />

      <div>
        <h2 className="mb-3 text-lg font-semibold">Popular Stocks & ETFs</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {POPULAR.map((stock) => (
            <a
              key={stock.ticker}
              href={`/stocks/${stock.ticker}`}
              className="flex items-center justify-between rounded-lg border bg-card p-3 transition-colors hover:bg-accent"
            >
              <div>
                <span className="font-medium">{stock.ticker}</span>
                <span className="ml-2 text-sm text-muted-foreground">
                  {stock.name}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">View →</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
