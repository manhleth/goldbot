import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, send } from "../api/client";
import type { Annotation, ReviewItem } from "../api/types";

const AUTOSAVE_MS = 700;

export type SaveState = { kind: "idle" } | { kind: "dirty" } | { kind: "saving" } | { kind: "saved"; at: Date }
  | { kind: "error"; message: string };

type Patch = Partial<Pick<Annotation, "shapes" | "verdict" | "errors" | "note">>;

const keyOf = (scope: string) => ["annotation", scope];

/** Nét vẽ + nhận xét của một scope: sửa cục bộ ngay, tự lưu sau AUTOSAVE_MS; rời đi thì lưu nốt phần chưa lưu. */
export function useAnnotation(scope: string, item?: ReviewItem) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: keyOf(scope), staleTime: Infinity,
    queryFn: () => api<Annotation>(`/api/review/${encodeURIComponent(scope)}`),
  });
  const [draft, setDraft] = useState<Annotation | null>(null);
  const [state, setState] = useState<SaveState>({ kind: "idle" });
  const pending = useRef<Patch>({});
  const timer = useRef<number>();
  const loaded = useRef<string | null>(null);

  // Chỉ nạp từ server khi đổi scope (không đè lên phần đang sửa khi server trả kết quả lưu).
  useEffect(() => {
    if (query.data && loaded.current !== scope) {
      loaded.current = scope;
      setDraft(query.data);
    }
  }, [query.data, scope]);

  const flush = useCallback(async () => {
    window.clearTimeout(timer.current);
    const body = pending.current;
    if (!Object.keys(body).length) return;
    pending.current = {};
    setState({ kind: "saving" });
    try {
      const saved = await send<Annotation>("PUT", `/api/review/${encodeURIComponent(scope)}`, { ...body, item });
      qc.setQueryData(keyOf(scope), saved);
      qc.invalidateQueries({ queryKey: ["reviews"] });
      setState(Object.keys(pending.current).length ? { kind: "dirty" } : { kind: "saved", at: new Date() });
    } catch (err) {
      pending.current = { ...body, ...pending.current };
      setState({ kind: "error", message: (err as Error).message });
    }
  }, [scope, item, qc]);

  const update = useCallback((patch: Patch) => {
    setDraft((d) => (d ? { ...d, ...patch } : d));
    pending.current = { ...pending.current, ...patch };
    setState({ kind: "dirty" });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(flush, AUTOSAVE_MS);
  }, [flush]);

  const flushRef = useRef(flush);
  flushRef.current = flush;
  useEffect(() => () => { void flushRef.current(); }, [scope]);

  return { data: draft, loading: query.isLoading, error: query.error as Error | null, state, update };
}

export function saveStateText(s: SaveState): string {
  switch (s.kind) {
    case "dirty": return "Chưa lưu…";
    case "saving": return "Đang lưu…";
    case "saved": return `Đã lưu lúc ${s.at.toLocaleTimeString("vi-VN")}`;
    case "error": return `Lỗi lưu: ${s.message}`;
    default: return "Tự lưu khi thay đổi";
  }
}
