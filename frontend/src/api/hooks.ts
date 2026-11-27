import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { api, isLiveSource, send, sourceQuery, type Source } from "./client";
import type {
  Analysis, BacktestMethod, BacktestRequest, BacktestStatus, BotSummary, CandlesResp, NewsResp, PositionsResp, Report,
  ReviewChartData, ReviewItem, ReviewOptions, Run, SignalRow, Status, Trade,
} from "./types";

const SECOND = 1000;

export const useStatus = () =>
  useQuery({ queryKey: ["status"], queryFn: () => api<Status>("/api/status"), refetchInterval: 5 * SECOND });

export const useCandles = (tf: string | null, enabled: boolean) =>
  useQuery({
    queryKey: ["candles", tf], enabled: enabled && !!tf, refetchInterval: 30 * SECOND,
    queryFn: () => api<CandlesResp>(`/api/candles?tf=${tf}&bars=800`),
  });

export const useAnalysis = (tf: string | null) =>
  useQuery({
    queryKey: ["analysis", tf], enabled: !!tf, refetchInterval: 30 * SECOND,
    queryFn: () => api<Analysis>(`/api/analysis?tf=${tf}`),
  });

export const useBots = () =>
  useQuery({ queryKey: ["bots"], queryFn: () => api<BotSummary[]>("/api/bots/summary"), refetchInterval: 10 * SECOND });

export const usePositions = () =>
  useQuery({ queryKey: ["positions"], queryFn: () => api<PositionsResp>("/api/positions"), refetchInterval: 10 * SECOND });

export const useNews = () =>
  useQuery({ queryKey: ["news"], queryFn: () => api<NewsResp>("/api/news"), refetchInterval: 300 * SECOND });

export const useRuns = () =>
  useQuery({ queryKey: ["runs"], queryFn: () => api<Run[]>("/api/runs?mode=backtest") });

const liveInterval = (source: Source) => (isLiveSource(source) ? 30 * SECOND : false);

export const useTrades = (source: Source) =>
  useQuery({
    queryKey: ["trades", source], refetchInterval: liveInterval(source),
    queryFn: () => api<Trade[]>(`/api/trades?${sourceQuery(source)}`).catch(() => [] as Trade[]),
  });

export const useSignals = (source: Source) =>
  useQuery({
    queryKey: ["signals", source], refetchInterval: liveInterval(source),
    queryFn: () => api<SignalRow[]>(`/api/signals?${sourceQuery(source)}&limit=1000`).catch(() => [] as SignalRow[]),
  });

/** Tín hiệu gần nhất của nhiều bot, gộp và sắp theo thời gian (mới nhất trước). */
export function useBotSignals(names: string[], limit = 60) {
  return useQueries({
    queries: names.map((name) => ({
      queryKey: ["signals", `bot:${name}`, limit], refetchInterval: 30 * SECOND,
      queryFn: () => api<SignalRow[]>(`/api/signals?mode=${encodeURIComponent(`bot:${name}`)}&limit=${limit}`)
        .then((rows) => rows.map((r) => ({ ...r, bot: name })))
        .catch(() => [] as (SignalRow & { bot: string })[]),
    })),
    combine: (results) => results.flatMap((r) => r.data ?? []).sort((a, b) => Date.parse(b.time) - Date.parse(a.time)),
  });
}

export const useReport = (source: Source) =>
  useQuery({
    queryKey: ["report", source], refetchInterval: liveInterval(source),
    queryFn: () => api<Report>(`/api/report?${sourceQuery(source)}`),
  });

export const useBacktestStatus = () =>
  useQuery({
    queryKey: ["backtest-status"],
    queryFn: () => api<BacktestStatus>("/api/backtest/status?lines=200"),
    refetchInterval: (q) => (q.state.data?.running ? 2 * SECOND : 15 * SECOND),
  });

export const useBacktestMethods = () =>
  useQuery({ queryKey: ["backtest-methods"], queryFn: () => api<BacktestMethod[]>("/api/backtest/methods"), staleTime: Infinity });

export const useConfigText = () =>
  useQuery({ queryKey: ["config"], queryFn: () => api<{ text: string }>("/api/config"), staleTime: Infinity });

export const useLog = (name: string, auto: boolean) =>
  useQuery({
    queryKey: ["log", name], refetchInterval: auto ? 5 * SECOND : false,
    queryFn: () => api<{ text: string }>(`/api/logs/${name}?lines=400`),
  });

export const useReviewOptions = () =>
  useQuery({ queryKey: ["review-options"], queryFn: () => api<ReviewOptions>("/api/review/options"), staleTime: Infinity });

/** Nến + hình học bot quanh một lệnh (lệnh đang mở thì làm mới mỗi phút). */
export const useReviewChart = (item: ReviewItem, live: boolean) =>
  useQuery({
    queryKey: ["review-chart", item.kind, item.mode, item.key], refetchInterval: live ? 60 * SECOND : false,
    queryFn: () => api<ReviewChartData>(`/api/review-chart/${item.kind}/${encodeURIComponent(item.mode)}/${item.key}`),
  });

/** Mutation có thông báo thành công/lỗi và làm mới các query liên quan. */
export function useAction<TVars, TResult>(
  fn: (vars: TVars) => Promise<TResult>,
  opts: { success?: (r: TResult) => string; invalidate?: string[][] } = {},
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      if (opts.success) notifications.show({ color: "blue", message: opts.success(result) });
      opts.invalidate?.forEach((key) => qc.invalidateQueries({ queryKey: key }));
    },
    onError: (err: Error) => notifications.show({ color: "red", title: "Lỗi", message: err.message }),
  });
}

export const actions = {
  startBot: () => send("POST", "/api/bot/start"),
  stopBot: () => send("POST", "/api/bot/stop"),
  startNamedBot: (name: string) => send("POST", `/api/bots/${name}/start`),
  stopNamedBot: (name: string) => send("POST", `/api/bots/${name}/stop`),
  saveBotSettings: ({ name, ...body }: { name: string; capital: number | null; risk_pct: number | null;
    max_lot: number | null; risk_caps: [number, number][] | null }) => send("POST", `/api/bots/${name}/settings`, body),
  killSwitch: (enabled: boolean) => send<{ kill_switch: boolean }>("POST", "/api/killswitch", { enabled }),
  refreshNews: () => send<{ count: number }>("POST", "/api/news/refresh"),
  importNews: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return send<{ count: number }>("POST", "/api/news/import", form);
  },
  runBacktest: (body: BacktestRequest) => send("POST", "/api/backtest", body),
  stopBacktest: () => send("POST", "/api/backtest/stop"),
  saveConfig: (text: string) => send<{ backup: string; bot_running: boolean }>("PUT", "/api/config", { text }),
};
