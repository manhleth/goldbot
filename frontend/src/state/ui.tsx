import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Source } from "../api/client";

export type Overlay = "ema" | "sr" | "fvg" | "ob" | "swings" | "setups" | "trades" | "news";
export type BottomTab = "stats" | "trades" | "signals" | "backtest" | "config" | "logs";

interface UiState {
  tf: string | null;
  setTf: (tf: string) => void;
  source: Source;
  setSource: (s: Source) => void;
  overlays: Record<Overlay, boolean>;
  toggleOverlay: (o: Overlay) => void;
  chartVisible: boolean;
  setChartVisible: (v: boolean) => void;
  bottomTab: BottomTab;
  setBottomTab: (t: BottomTab) => void;
}

const DEFAULT_OVERLAYS: Record<Overlay, boolean> = {
  ema: true, sr: true, fvg: true, ob: false, swings: false, setups: true, trades: true, news: true,
};
const STORAGE_KEY = "goldbot.ui";

/** Chỉ lưu tiện ích hiển thị của người xem; trình duyệt chặn storage thì vẫn chạy bình thường. */
function load(): Partial<{ overlays: Record<Overlay, boolean>; chartVisible: boolean; tf: string }> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function save(patch: object) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...load(), ...patch }));
  } catch {
    /* bỏ qua */
  }
}

const Ctx = createContext<UiState | null>(null);

export function UiProvider({ children }: { children: ReactNode }) {
  const saved = useMemo(load, []);
  const [tf, setTfState] = useState<string | null>(saved.tf ?? null);
  const [source, setSource] = useState<Source>("bot:swing");
  const [overlays, setOverlays] = useState({ ...DEFAULT_OVERLAYS, ...saved.overlays });
  const [chartVisible, setChartVisibleState] = useState(saved.chartVisible ?? true);
  const [bottomTab, setBottomTab] = useState<BottomTab>("stats");

  const setTf = useCallback((value: string) => { setTfState(value); save({ tf: value }); }, []);
  const setChartVisible = useCallback((v: boolean) => { setChartVisibleState(v); save({ chartVisible: v }); }, []);
  const toggleOverlay = useCallback((o: Overlay) => {
    setOverlays((prev) => {
      const next = { ...prev, [o]: !prev[o] };
      save({ overlays: next });
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ tf, setTf, source, setSource, overlays, toggleOverlay, chartVisible, setChartVisible, bottomTab, setBottomTab }),
    [tf, setTf, source, overlays, toggleOverlay, chartVisible, setChartVisible, bottomTab],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useUi(): UiState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useUi phải nằm trong UiProvider");
  return ctx;
}
