import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Candle } from "../api/types";

const CHUNK = 1500;  // số nến cũ nạp thêm mỗi lần kéo tới mép trái

/** Gộp: giữ nến cũ hơn nến đầu của `latest`, phần còn lại lấy từ `latest` (nến mới nhất luôn theo server). */
function merge(prev: Candle[], latest: Candle[]): Candle[] {
  if (!latest.length) return prev;
  const first = latest[0].time;
  return [...prev.filter((c) => c.time < first), ...latest];
}

interface State { tf: string | null; bars: Candle[]; done: boolean }

const EMPTY: Candle[] = [];

/** Nến của chart: cửa sổ mới nhất (tự làm mới) + nến cũ nạp dần khi kéo sang trái (`loadOlder`).
 *  Nến luôn gắn với khung của nó: đổi khung thì trả rỗng tới khi có nến của khung mới (chart không lẫn khung). */
export function useCandleHistory(tf: string | null, latest: Candle[] | undefined) {
  const [state, setState] = useState<State>({ tf, bars: [], done: false });
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);
  const asked = useRef<string | null>(null);  // tránh xin lại cùng một đoạn trước khi state kịp cập nhật
  const current = state.tf === tf ? state : { tf, bars: EMPTY, done: false };
  const ref = useRef(current);
  ref.current = current;

  useEffect(() => {
    setState((prev) => {
      const base = prev.tf === tf ? prev : { tf, bars: [], done: false };
      return latest ? { ...base, bars: merge(base.bars, latest) } : base;
    });
  }, [tf, latest]);

  const loadOlder = useCallback(async () => {
    const { tf: at, bars, done } = ref.current;
    const key = `${at}:${bars[0]?.time}`;
    if (busy.current || done || !at || !bars.length || asked.current === key) return;
    asked.current = key;
    busy.current = true;
    setLoading(true);
    try {
      const res = await api<{ candles: Candle[] }>(`/api/candles/history?tf=${at}&before=${bars[0].time}&bars=${CHUNK}`);
      setState((prev) => {
        if (prev.tf !== at) return prev;
        if (!res.candles.length) return { ...prev, done: true };
        const first = prev.bars[0]?.time ?? Infinity;
        return { ...prev, bars: [...res.candles.filter((c) => c.time < first), ...prev.bars] };
      });
    } catch {
      setState((prev) => (prev.tf === at ? { ...prev, done: true } : prev));
    } finally {
      busy.current = false;
      setLoading(false);
    }
  }, []);

  return { bars: current.bars, loadOlder, loading, done: current.done };
}

/** EMA như pandas ewm(span, adjust=False, min_periods=span): bỏ `period - 1` điểm đầu. */
export function emaPoints(bars: { time: number; close: number }[], period: number): { time: number; value: number }[] {
  const alpha = 2 / (period + 1);
  const out: { time: number; value: number }[] = [];
  let e = 0;
  bars.forEach((b, i) => {
    e = i === 0 ? b.close : alpha * b.close + (1 - alpha) * e;
    if (i >= period - 1) out.push({ time: b.time, value: e });
  });
  return out;
}
