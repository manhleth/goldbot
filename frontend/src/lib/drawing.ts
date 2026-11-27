/** Nét vẽ tay trên chart: lưu theo (thời gian UTC, giá) để vẽ lại đúng chỗ ở mọi khung/khi cuộn. */

export interface DrawPoint { t: number; p: number }
export type ShapeKind = "trend" | "hline" | "zone";
export type Tool = "cursor" | ShapeKind | "erase";

export interface Shape {
  id: string;
  kind: ShapeKind;
  /** Khóa vai trò (review.roles trong config: note / right / wrong); "bot" = nét của bot, chỉ đọc. */
  role: string;
  points: DrawPoint[];
  text?: string | null;
  /** Nét chỉ đọc của bot: kiểu vẽ riêng (màu, nét đứt, độ đậm, độ mờ). */
  style?: ShapeStyle;
  /** Trendline: kéo dài theo đúng độ dốc tới thời điểm này (UTC giây). */
  extendTo?: number;
  /** Điểm đánh dấu (vd các lần chạm đỉnh/đáy) vẽ vòng tròn + nhãn. */
  marks?: { t: number; p: number; text?: string }[];
}

export interface ShapeStyle { color?: string; dash?: string; width?: number; opacity?: number }

/** Số điểm cần click để xong một nét. */
export const POINTS_NEEDED: Record<ShapeKind, number> = { trend: 2, hline: 1, zone: 2 };

/** Trục thời gian theo nến: `times` là thời gian hiển thị của từng nến (tăng dần), `step` = độ dài 1 nến (giây). */
export interface TimeAxis { times: number[]; step: number }

/** Thời gian → chỉ số nến (có phần lẻ), ngoại suy theo `step` ngoài hai đầu dữ liệu. */
export function timeToLogical({ times, step }: TimeAxis, t: number): number {
  const n = times.length;
  if (!n) return NaN;
  if (t <= times[0]) return (t - times[0]) / step;
  if (t >= times[n - 1]) return n - 1 + (t - times[n - 1]) / step;
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (times[mid] <= t) lo = mid; else hi = mid;
  }
  return lo + (t - times[lo]) / (times[hi] - times[lo]);
}

/** Chỉ số nến (có phần lẻ) → thời gian; ngược của timeToLogical. */
export function logicalToTime({ times, step }: TimeAxis, l: number): number {
  const n = times.length;
  if (!n) return NaN;
  if (l <= 0) return times[0] + l * step;
  if (l >= n - 1) return times[n - 1] + (l - (n - 1)) * step;
  const i = Math.floor(l);
  return times[i] + (l - i) * (times[i + 1] - times[i]);
}

export const newShapeId = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
