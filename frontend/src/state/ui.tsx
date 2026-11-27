import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Source } from "../api/client";

export type Overlay = "ema" | "sr" | "fvg" | "ob" | "swings" | "setups" | "trades" | "news";
export type Page = "overview" | "chart" | "trades" | "signals" | "stats" | "backtest" | "config" | "logs";

interface UiState {
  page: Page;
  setPage: (p: Page) => void;
  tf: string | null;
  setTf: (tf: string) => void;
  source: Source;
  setSource: (s: Source) => void;
  overlays: Record<Overlay, boolean>;
  toggleOverlay: (o: Overlay) => void;
}

const DEFAULT_OVERLAYS: Record<Overlay, boolean> = {
  ema: true, sr: false, fvg: false, ob: false, swings: false, setups: false, trades: true, news: true,
};
const STORAGE_KEY = "goldbot.ui";

type Saved = Partial<{ overlays: Record<Overlay, boolean>; tf: string; page: Page; source: Source }>;

/** Chỉ lưu tiện ích hiển thị của người xem; trình duyệt chặn storage thì vẫn chạy bình thường. */
function load(): Saved {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function save(patch: Saved) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...load(), ...patch }));
  } catch {
    /* bỏ qua */
  }
}

const Ctx = createContext<UiState | null>(null);

export function UiProvider({ children }: { children: ReactNode }) {
  const saved = useMemo(load, []);
  const [page, setPageState] = useState<Page>(saved.page ?? "overview");
  const [tf, setTfState] = useState<string | null>(saved.tf ?? null);
  const [source, setSourceState] = useState<Source>(saved.source ?? "bot:swing");
  const [overlays, setOverlays] = useState({ ...DEFAULT_OVERLAYS, ...saved.overlays });

  const setPage = useCallback((p: Page) => { setPageState(p); save({ page: p }); }, []);
  const setTf = useCallback((value: string) => { setTfState(value); save({ tf: value }); }, []);
  const setSource = useCallback((s: Source) => { setSourceState(s); save({ source: s }); }, []);
  const toggleOverlay = useCallback((o: Overlay) => {
    setOverlays((prev) => {
      const next = { ...prev, [o]: !prev[o] };
      save({ overlays: next });
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ page, setPage, tf, setTf, source, setSource, overlays, toggleOverlay }),
    [page, setPage, tf, setTf, source, setSource, overlays, toggleOverlay],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useUi(): UiState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useUi phải nằm trong UiProvider");
  return ctx;
}
