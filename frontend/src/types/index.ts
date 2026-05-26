export interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  onboarded: boolean;
  portfolio_id: string | null;
  created_at: string;
}

export interface OnboardResponse {
  user: UserResponse;
  portfolio_id: string;
}

export interface ApiResponse<T> {
  data: T;
}

// Portfolio types
export interface HoldingSummary {
  ticker: string;
  company_name: string;
  quantity: string;
  average_cost: string;
  current_price: string;
  market_value: string;
  total_cost: string;
  unrealized_pnl: string;
  unrealized_pnl_pct: string;
  daily_change: string;
  daily_change_pct: string;
  weight: string;
  instrument_type: string;
  sector: string | null;
}

export interface PortfolioSummary {
  id: string;
  name: string;
  cash_balance: string;
  total_value: string;
  starting_balance: string;
  total_return: string;
  total_return_pct: string;
  daily_change: string;
  daily_change_pct: string;
  holdings: HoldingSummary[];
  holdings_count: number;
}

export interface TransactionItem {
  id: string;
  ticker: string;
  company_name: string | null;
  type: "BUY" | "SELL";
  quantity: string;
  execution_price: string;
  total_amount: string;
  realized_pnl: string | null;
  executed_after_hours: boolean;
  journal_note: string | null;
  executed_at: string;
}

export interface PaginatedTransactions {
  data: TransactionItem[];
  next_cursor: string | null;
}

export interface PerformancePoint {
  date: string;
  value: string;
}

export interface PerformanceData {
  starting_balance: string;
  current_value: string;
  total_return: string;
  total_return_pct: string;
  points: PerformancePoint[];
}

// Trade types
export interface TradeWarning {
  code: string;
  message: string;
}

export interface TradePreview {
  ticker: string;
  type: string;
  quantity: string;
  estimated_price: string;
  estimated_total: string;
  market_open: boolean;
  after_hours: boolean;
  portfolio_after: { cash_balance: string };
  holding_after: { ticker: string; quantity: string; average_cost: string } | null;
  warnings: TradeWarning[];
}

export interface TradeResult {
  transaction: {
    id: string;
    ticker: string;
    type: string;
    quantity: string;
    execution_price: string;
    total_amount: string;
    realized_pnl: string | null;
    executed_after_hours: boolean;
    journal_note: string;
    executed_at: string;
  };
  portfolio_after: { cash_balance: string };
  holding_after: { ticker: string; quantity: string; average_cost: string } | null;
  risk_score_after: number | null;
}

// Watchlist types
export interface WatchlistItem {
  ticker: string;
  company_name: string;
  current_price: string;
  previous_close: string;
  daily_change: string;
  daily_change_pct: string;
  added_at: string;
}
