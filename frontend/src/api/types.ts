export type Dir = "BUY" | "SELL" | "NEUTRAL";

export interface Account {
  login: number; server: string; name: string; currency: string; balance: number; equity: number;
  margin_free: number; demo: boolean; hedging: boolean;
}
export interface Quote { bid: number; ask: number; spread_points: number }
export interface Timeframes { bias: string[]; setup: string; trigger: string }

export interface Status {
  symbol: string;
  mt5: { connected: boolean; error: string | null; account: Account | null; quote: Quote | null };
  bot: { running: boolean; heartbeat: string | null };
  bots: BotStatus[];
  kill_switch: boolean;
  backtest_running: boolean;
  news: { blackout: string | null; next: { title: string; time: number } | null };
  timeframes: Timeframes;
}

export interface BotStatus { name: string; method: string; running: boolean; heartbeat: string | null; open: number }

export interface Candle { time: number; open: number; high: number; low: number; close: number }
export interface CandlesResp { source: "mt5" | "cache"; candles: Candle[]; ema: Record<string, { time: number; value: number }[]> }

export interface ZoneOverlay { low: number; high: number; start: number; direction?: Dir; touches?: number }
export interface SetupInfo { name: string; direction: Dir; low: number; high: number; invalidation: number; score: number; reasons: string[]; key: string }
export interface Analysis {
  source: string; ready: boolean; message?: string; time: number; direction: Dir;
  biases: Record<string, { direction: Dir; score: number; reasons: string[] }>;
  setups: SetupInfo[];
  signals: { setup: string; direction: Dir; trigger: string; close: number; key: string }[];
  overlays: {
    sr_zones: ZoneOverlay[]; fvgs: ZoneOverlay[]; order_blocks: ZoneOverlay[];
    swings: { time: number; price: number; kind: "high" | "low" }[]; atr: number | null;
  } | null;
}

export interface Trade {
  id: number; run_id: string; setup: string; direction: Dir; bias: string; score: number;
  entry_time: string; exit_time: string; entry: number; sl: number; tp1: number; tp2: number | null;
  volume: number; r_multiple: number; pnl: number | null; exit_reason: string; mae_r: number; mfe_r: number;
  spread_entry: number; news: string | null; chart?: string | null;
}

export interface SignalRow {
  id: number; time: string; setup: string; direction: Dir; trigger: string; score: number; bias: string;
  entry: number | null; sl: number | null; tp1: number | null; rr_tp1: number | null; news: string | null;
  accepted: number; reject_reason: string | null;
}

export interface BrokerPosition { ticket: number; volume: number; price_open: number; price_current: number; sl: number; tp: number; profit: number; buy: boolean; comment: string }
export interface Leg {
  ticket: number; setup: string; setup_key: string; leg: string; direction: number; volume: number; entry: number;
  sl: number; tp: number | null; opened_at: string; news: string | null; broker: BrokerPosition | null;
}
export interface PositionsResp { legs: Leg[]; unmanaged: BrokerPosition[] }

export interface NewsEvent { time: number; title: string; country: string; impact: string; forecast: string; previous: string; gold: Dir; past: boolean; source: string }
export interface NewsResp {
  enabled: boolean; rule: string; lookahead_hours: number; last_refresh: string | null; blackout: string | null;
  outlook: { direction: Dir; score: number }; events: NewsEvent[];
}

export interface Run { run_id: string; created_at: string; config_hash: string; params: string; trades: number; total_r: number | null }

export interface RSummary {
  trades: number; wins: number; winrate: number; winrate_ci_low: number; winrate_ci_high: number;
  avg_win_r: number; avg_loss_r: number; expectancy_r: number; profit_factor: number | null; total_r: number;
  max_dd_r: number; longest_losing_streak: number;
}
export interface MoneySummary {
  initial_equity: number; final_equity: number; net_profit: number; return_pct: number | null; gross_profit: number;
  gross_loss: number; profit_factor: number | null; avg_win: number; avg_loss: number; largest_win: number;
  largest_loss: number; expectancy: number; max_drawdown: number; max_drawdown_pct: number; avg_hold_hours: number;
}
export interface BreakdownRow extends Omit<RSummary, "wins"> { key: string; pnl: number }
export interface Report {
  run: string; verdict: string; summary: RSummary | null; money: MoneySummary | null;
  breakdowns: Record<string, BreakdownRow[]>;
  equity_curve: { time: number; equity: number; drawdown_pct: number }[];
  monthly: { month: string; pnl: number; r: number; trades: number; winrate: number }[];
  r_histogram: { from: number; to: number; count: number }[];
  signals: { total: number; accepted: number; rejected: Record<string, number> };
  max_drawdown_floating_pct: number | null;
  text: string;
}

export interface BacktestStatus { running: boolean; exit_code: number | null; run_id: string | null; log: string }
