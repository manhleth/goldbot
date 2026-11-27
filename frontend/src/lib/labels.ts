export const SETUP_LABEL: Record<string, string> = {
  fvg_retest: "FVG retest",
  sr_flip_retest: "S/R đổi vai",
  sweep_reversal: "Quét thanh khoản",
  trendline_break_retest: "Phá trendline",
  sweep_mss_fvg: "Sweep → MSS → FVG",
  judas_swing: "Judas swing (phiên Á)",
  range_breakout: "Breakout range (H1 theo H4)",
};

export const SETUP_ABBR: Record<string, string> = {
  fvg_retest: "FVG", sr_flip_retest: "SRF", sweep_reversal: "SWP", trendline_break_retest: "TLB",
  sweep_mss_fvg: "MSS", judas_swing: "JDS", range_breakout: "RBO",
};

export const REJECT_LABEL: Record<string, string> = {
  tp1_rr_too_low: "Mục tiêu gần nhất chưa đạt R:R tối thiểu",
  no_tp1_target: "Không có mục tiêu cấu trúc",
  sl_too_far: "SL quá xa (vượt giới hạn ATR)",
  sl_wrong_side: "SL sai phía",
  rsi_overbought: "RSI quá mua",
  rsi_oversold: "RSI quá bán",
  score_below_min: "Điểm confluence thấp",
  same_direction_same_zone: "Đã có lệnh cùng chiều cùng vùng",
  max_open_trades: "Đủ số lệnh mở tối đa",
  daily_loss_limit: "Chạm giới hạn lỗ ngày",
  paused_after_losses: "Tạm dừng sau chuỗi thua",
  spread_too_wide: "Spread quá rộng",
  blocked_window: "Khung giờ cấm",
  news_blackout: "Gần giờ ra tin",
  news_forecast_against: "Dự báo tin ngược chiều",
  news_forecast_not_aligned: "Dự báo tin không cùng chiều",
  lot_below_minimum: "Lot nhỏ hơn mức tối thiểu",
  atr_unavailable: "Chưa có ATR",
  outside_killzone: "Ngoài killzone",
  after_flat_time: "Sau giờ đóng lệnh (flat_time)",
  learning_insufficient: "Loại mẫu hình chưa đủ kết quả nháp",
  learning_negative: "Loại mẫu hình đang thua gần đây",
  against_channel_bias: "Ngược hướng channel MJ Capital",
  no_channel_bias: "Không có nhận định channel",
  max_trades_per_day: "Đủ số lệnh trong ngày",
  stale_signal: "Tín hiệu cũ",
  stop_file: "Kill switch đang bật",
  order_failed: "Gửi lệnh thất bại",
  lot_too_small: "Lot nhỏ hơn mức tối thiểu",
  expired: "Lệnh chờ hết hạn",
  cancelled: "Lệnh chờ bị huỷ",
};

/** Loại mẫu hình của ONE (phần `loại@khung` trong khoá lệnh). */
export const KIND_LABEL: Record<string, string> = {
  flag: "Cờ", triangle_break: "Phá tam giác", channel_break: "Phá kênh", neckline_break: "Thủng neckline",
  channel_bounce: "Bật cạnh kênh", broadening_break: "Phá mẫu hình loe", asia_box: "Phá hộp Á",
};

/** "flag@H4" hoặc khoá "one_swing:flag@H4:2026…:BUY" → "Cờ · H4". */
export function kindLabel(value: string | null | undefined): string {
  if (!value) return "—";
  const part = value.includes(":") ? value.split(":")[1] ?? value : value;
  const [kind, tf] = part.split("@");
  return `${KIND_LABEL[kind] ?? kind}${tf ? ` · ${tf}` : ""}`;
}

export const NEWS_LABEL: Record<string, string> = {
  aligned: "Cùng chiều", against: "Ngược chiều", neutral: "Trung tính", none: "Không có tin",
};

export const RULE_LABEL: Record<string, string> = {
  off: "Tắt — chỉ hiển thị",
  block_against: "Bỏ tín hiệu ngược chiều dự báo",
  require_aligned: "Chỉ vào khi cùng chiều dự báo",
};

export const label = (map: Record<string, string>, key: string | null | undefined) => (key ? map[key] ?? key : "—");

export const BOT_LABEL: Record<string, string> = { swing: "Bot swing", day: "Bot trong ngày", live: "Bot cũ" };
