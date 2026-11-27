export type Dir = "BUY" | "SELL" | "NEUTRAL";

export interface Account {
  login: number; server: string; name: string; currency: string; balance: number; equity: number;
  margin_free: number; margin: number; margin_level: number; profit: number; leverage: number;
  demo: boolean; hedging: boolean;
}

export interface BotSummary {
  name: string; method: string; title: string; magic: number; running: boolean; heartbeat: string | null;
  open: number; risk_pct: number | null; max_positions: number | null; max_per_day: number | null;
  trades: number; wins: number; pnl_total: number; pnl_today: number; r_total: number; floating: number;
  last_signal: { time: string; setup_key: string; direction: Dir; accepted: number; reject_reason: string | null } | null;
  initial_equity: number | null; experience: Record<string, [number, number]>;
  /** Vốn hiện tại của bot (đặt tay hoặc mặc định) + % rủi ro đang dùng. */
  capital: number; capital_custom: boolean; risk_custom: boolean; risk_default: number | null;
  risk_now: number | null; max_lot: number | null; risk_caps: [number, number][];
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
  /** Khung chọn được trên chart chính (web.chart_timeframes). */
  chart_timeframes: string[];
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
  /** JSON: hình học mẫu hình + bối cảnh lúc vào lệnh (context.lines). */
  meta?: string | null;
  id: number; run_id: string; setup: string; direction: Dir; bias: string; score: number;
  entry_time: string; exit_time: string; entry: number; sl: number; tp1: number; tp2: number | null;
  volume: number; r_multiple: number; pnl: number | null; exit_reason: string; mae_r: number; mfe_r: number;
  spread_entry: number; news: string | null; chart?: string | null; reasons?: string | null; setup_key?: string;
  levels?: Levels;
}

export interface SignalRow {
  /** JSON: hình học mẫu hình + bối cảnh lúc vào lệnh (context.lines). */
  meta?: string | null;
  id: number; run_id?: string; time: string; setup: string; direction: Dir; trigger: string; score: number; bias: string;
  entry: number | null; sl: number | null; tp1: number | null; rr_tp1: number | null; news: string | null;
  accepted: number; reject_reason: string | null; setup_key?: string | null; reasons?: string | null;
}

/** Giá + số tiền lời (>0) / lỗ (<0) nếu giá chạm mức đó. */
export interface MoneyLevel { price: number; money: number }
export type Levels = Record<string, MoneyLevel | null>;

export interface BrokerPosition {
  ticket: number; volume: number; price_open: number; price_current: number; sl: number; tp: number; profit: number;
  swap: number; buy: boolean; comment: string; time: number; magic: number; bot: string;
}
export interface Leg {
  /** JSON: hình học mẫu hình + bối cảnh lúc vào lệnh (context.lines). */
  meta?: string | null;
  ticket: number; setup: string; setup_key: string; leg: string; direction: number; volume: number; entry: number;
  sl: number; initial_sl: number; tp: number | null; opened_at: string; news: string | null; bot: string;
  reasons: string | null; chart: string | null; exit_at: string | null; broker: BrokerPosition | null;
  levels?: Levels;
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

export interface BacktestStatus { running: boolean; exit_code: number | null; run_id: string | null; run_ids?: string[]; log: string }
export interface BacktestMethod {
  name: string; title: string; risk_pct: number | null; capital_share: number; bot: string | null;
  max_lot: number | null; risk_caps: [number, number][] | null;
}
export type RiskCaps = [number, number][];
export interface BacktestRequest {
  start: string; end: string; methods: string[]; capital: Record<string, number>; risk: Record<string, number>;
  max_lot: Record<string, number>; risk_caps: Record<string, RiskCaps>; refresh: boolean; cent: boolean;
}

/** Vẽ tay + nhận xét lệnh (config.yaml mục review). */
export interface ReviewOption { key: string; label: string; color?: string }
export interface ReviewOptions { roles: ReviewOption[]; verdicts: ReviewOption[]; error_tags: ReviewOption[] }

export interface Annotation {
  scope: string;
  shapes: import("../lib/drawing").Shape[] | null;
  verdict: string | null;
  errors: string[] | null;
  note: string | null;
  updated_at?: string;
}

/** Lệnh/tín hiệu cần nhận xét: loại + journal (mode) + khóa (id hoặc ticket). */
export interface ReviewItem { kind: "trade" | "leg" | "signal"; mode: string; key: number }

/** Dữ liệu chart nhận xét của một lệnh (thời gian Unix giây UTC). */
export interface ReviewChartData {
  tf: string;
  candles: Candle[];
  direction: number;
  open: boolean;
  entry_time: number;
  entry: number | null;
  sl: number | null;
  sl_now: number | null;
  tp: number | null;
  target: number | null;
  exit_time: number | null;
  exit_price: number | null;
  r: number | null;
  edges: [number, number, number, number][];
  breakout_time: number | null;
}

/** Lớp vẽ của bot trên chart chính (GET /api/bot-overlays). Thời gian: Unix giây UTC. */
export interface BotTouch { t: number; p: number; kind?: "high" | "low" }
export interface BotZone {
  tf: string; low: number; high: number; role: "resistance" | "support" | "inside";
  touches: BotTouch[]; start: number; extend_to: number;
}
export interface BotTrendline {
  tf: string; swing: number; side: number; state: "active" | "broken"; touches: number;
  points: [number, number][]; extend_to: number; marks: BotTouch[];
}
export interface BotSetup {
  id: number; time: number; direction: Dir; key: string; tf: string | null; accepted: boolean; reject: string | null;
  breakout: number; edges: [number, number, number, number][];
}
export interface BotOverlays { method: string; sr: BotZone[]; trendlines: BotTrendline[]; setups: BotSetup[]; error?: string }
