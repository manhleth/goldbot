const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

export const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
export const fmt = (v: number | null | undefined, digits = 2) => (isNum(v) ? v.toFixed(digits) : "—");
export const money = (v: number | null | undefined) => (isNum(v) ? usd.format(v) : "—");
export const signedMoney = (v: number | null | undefined) => (isNum(v) ? `${v > 0 ? "+" : ""}${usd.format(v)}` : "—");
export const signed = (v: number | null | undefined, digits = 2) => (isNum(v) ? `${v > 0 ? "+" : ""}${v.toFixed(digits)}` : "—");
export const pct = (ratio: number | null | undefined, digits = 1) => (isNum(ratio) ? `${(ratio * 100).toFixed(digits)}%` : "—");
export const pctValue = (v: number | null | undefined, digits = 1) => (isNum(v) ? `${v.toFixed(digits)}%` : "—");

export const timeLocal = (sec: number) => new Date(sec * 1000).toLocaleString("vi-VN", { hour12: false });
export const isoLocal = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("vi-VN", { hour12: false }) : "—";
export const isoSeconds = (iso: string) => Date.parse(iso) / 1000;
export const dateShort = (sec: number) => new Date(sec * 1000).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "2-digit" });

/** Lệch múi giờ của máy (giây) — biểu đồ giá hiển thị theo giờ máy. */
export const TZ_OFFSET = -new Date().getTimezoneOffset() * 60;
