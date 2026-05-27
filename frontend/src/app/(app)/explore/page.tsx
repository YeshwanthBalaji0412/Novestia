"use client";

import Link from "next/link";
import { PageHeader } from "@/components/layout/page-header";
import { StockSearch } from "@/components/common/stock-search";

const POPULAR = [
  { ticker: "AAPL", name: "Apple", type: "STOCK" },
  { ticker: "MSFT", name: "Microsoft", type: "STOCK" },
  { ticker: "GOOGL", name: "Alphabet", type: "STOCK" },
  { ticker: "AMZN", name: "Amazon", type: "STOCK" },
  { ticker: "NVDA", name: "NVIDIA", type: "STOCK" },
  { ticker: "TSLA", name: "Tesla", type: "STOCK" },
  { ticker: "META", name: "Meta", type: "STOCK" },
  { ticker: "JPM", name: "JPMorgan", type: "STOCK" },
  { ticker: "V", name: "Visa", type: "STOCK" },
  { ticker: "JNJ", name: "J&J", type: "STOCK" },
  { ticker: "VOO", name: "S&P 500", type: "ETF" },
  { ticker: "QQQ", name: "Nasdaq 100", type: "ETF" },
  { ticker: "VTI", name: "Total Market", type: "ETF" },
  { ticker: "BND", name: "Bonds", type: "ETF" },
  { ticker: "ARKK", name: "ARK Innovation", type: "ETF" },
];

export default function ExplorePage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        title="Explore Stocks"
        subtitle="Search by company name or ticker. Click any stock to view details and trade."
      />

      <StockSearch
        showWatchlistButton
        placeholder="Search stocks (e.g. Apple, Tesla, Microsoft, VOO...)"
      />

      <div>
        <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          Popular Stocks & ETFs
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {POPULAR.map((stock) => (
            <Link
              key={stock.ticker}
              href={`/stocks/${stock.ticker}`}
              className="glass-card flex items-center justify-between p-3 transition-all hover:border-primary/30"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">{stock.ticker}</span>
                <span className="text-xs text-muted-foreground">{stock.name}</span>
              </div>
              <span className="rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-[9px] uppercase tracking-wider text-muted-foreground">
                {stock.type}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
