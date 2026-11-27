import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createChart, CrosshairMode, LineStyle,
  type IChartApi, type IPriceLine, type ISeriesApi, type SeriesMarker, type Time, type UTCTimestamp,
} from "lightweight-charts";
import { useAnalysis, useBotOverlays, useCandles, useNews, usePositions, useTrades } from "../../api/hooks";
import type { Analysis, BotOverlays, Candle, ZoneOverlay } from "../../api/types";
import type { Shape } from "../../lib/drawing";
import { isoSeconds, TZ_OFFSET } from "../../lib/format";
import { SETUP_ABBR } from "../../lib/labels";
import { useUi, type Overlay } from "../../state/ui";
import type { ShapeEditor } from "../../state/shapeEditor";
import { emaPoints, useCandleHistory } from "../../state/candleHistory";
import { CHART } from "../../theme";
import { DrawingLayer, type ChartApi } from "./DrawingLayer";

const TF_SECONDS: Record<string, number> = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H2: 7200, H4: 14400, D1: 86400, W1: 604800 };
const FVG_EACH_SIDE = 3;
const SETUP_EDGE_BARS = 6;  // cạnh mẫu hình kéo dài tới sau nến phá (giống ảnh lý do vào lệnh)
const ROLE = {
  resistance: { color: "#ef5350", name: "Kháng cự" },
  support: { color: "#2f80ed", name: "Hỗ trợ" },
  inside: { color: "#ffb74d", name: "Giá trong vùng" },
};
const LINE_COLOR = { support: "#2f80ed", resistance: "#ef5350" };
const SETUP_COLOR: Record<string, string> = { BUY: "#5b9cf0", SELL: "#e68a3a", NEUTRAL: "#787b86" };

type Bar = Candle & { time: UTCTimestamp };
interface DrawZone { low: number; high: number; start: number; fill: string; line: string; label: string }

const shift = (t: number) => (t + TZ_OFFSET) as UTCTimestamp;

function snapToBar(bars: Bar[], t: number): UTCTimestamp | null {
  if (!bars.length || t < bars[0].time) return null;
  let lo = 0;
  let hi = bars.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (bars[mid].time <= t) lo = mid; else hi = mid - 1;
  }
  return bars[lo].time;
}

/** Chỉ giữ các vùng gần giá nhất mỗi phía để biểu đồ không bị rối. */
function nearestZones(zones: ZoneOverlay[], price: number, perSide: number): ZoneOverlay[] {
  const dist = (z: ZoneOverlay) => Math.min(Math.abs(z.low - price), Math.abs(z.high - price));
  const above = zones.filter((z) => z.low > price).sort((a, b) => dist(a) - dist(b)).slice(0, perSide);
  const below = zones.filter((z) => z.high < price).sort((a, b) => dist(a) - dist(b)).slice(0, perSide);
  return [...zones.filter((z) => z.low <= price && price <= z.high), ...above, ...below];
}

function zonesToDraw(a: Analysis | undefined, bars: Bar[], ov: Record<Overlay, boolean>): DrawZone[] {
  if (!bars.length) return [];
  const out: DrawZone[] = [];
  const price = bars[bars.length - 1].close;
  if (!a?.ready || !a.overlays) return out;
  if (ov.fvg) nearestZones(a.overlays.fvgs, price, FVG_EACH_SIDE).forEach((z) => out.push({ ...z, start: shift(z.start), label: "FVG",
    fill: z.direction === "BUY" ? "rgba(38,166,154,.12)" : "rgba(239,83,80,.12)", line: z.direction === "BUY" ? CHART.candleUp : CHART.candleDown }));
  if (ov.ob) nearestZones(a.overlays.order_blocks, price, FVG_EACH_SIDE).forEach((z) => out.push({ ...z, start: shift(z.start), label: "OB", fill: "rgba(144,133,233,.12)", line: "#9085e9" }));
  return out;
}

/** Đánh số các lần chạm theo loại: Đỉnh 1, 2… / Đáy 1, 2… */
function touchMarks(touches: BotOverlays["sr"][number]["touches"]) {
  const n = { high: 0, low: 0 };
  return touches.map((m) => {
    const kind = m.kind ?? "low";
    n[kind] += 1;
    return { t: m.t, p: m.p, text: `${kind === "high" ? "Đỉnh" : "Đáy"} ${n[kind]}` };
  });
}

/** Vùng S/R quan trọng (dải ngang từ lần chạm đầu, đánh dấu từng đỉnh/đáy), trendline quan trọng nhất mỗi phía
 *  (liền: còn hiệu lực; đứt: đã phá, giá đang retest) + cạnh mẫu hình các setup đã quét. */
function botShapes(bot: BotOverlays | undefined, ov: Record<Overlay, boolean>): Shape[] {
  if (!bot) return [];
  const out: Shape[] = [];
  if (ov.sr) {
    bot.sr.forEach((z, i) => {
      const role = ROLE[z.role];
      out.push({ id: `sr${i}`, kind: "zone", role: "bot", points: [{ t: z.start, p: z.high }, { t: z.extend_to, p: z.low }],
        text: `${role.name} ${z.tf} · ${z.touches.length} lần chạm`, marks: touchMarks(z.touches),
        style: { color: role.color, width: 1.5 } });
    });
  }
  if (ov.trendlines) {
    bot.trendlines.forEach((l, i) => out.push({
      id: `tl${i}`, kind: "trend", role: "bot", points: l.points.map(([t, p]) => ({ t, p })), extendTo: l.extend_to,
      text: `Trendline ${l.tf} · ${l.touches} chạm${l.state === "broken" ? " · đã phá, đang retest" : ""}`,
      marks: l.marks.map((m) => ({ t: m.t, p: m.p })),
      style: { color: l.side > 0 ? LINE_COLOR.support : LINE_COLOR.resistance, width: 2,
        dash: l.state === "broken" ? "6 4" : undefined },
    }));
  }
  if (ov.setups) {
    bot.setups.forEach((s) => s.edges.forEach(([t1, p1, t2, p2], j) => out.push({
      id: `su${s.id}_${j}`, kind: "trend", role: "bot", points: [{ t: t1, p: p1 }, { t: t2, p: p2 }],
      extendTo: s.breakout + SETUP_EDGE_BARS * (TF_SECONDS[s.tf ?? "H1"] ?? 3600),
      style: { color: SETUP_COLOR[s.direction], width: 1.2, dash: s.accepted ? undefined : "3 3", opacity: s.accepted ? 0.9 : 0.5 },
    })));
  }
  return out;
}

/** Nét vẽ tay trên chart chính (do ChartPanel giữ trạng thái và tự lưu). */
export interface ChartDrawing {
  editor: ShapeEditor;
  colors: Record<string, string>;
}

export function PriceChart({ drawing }: { drawing?: ChartDrawing }) {
  const { tf, overlays } = useUi();
  const candles = useCandles(tf, true);
  const history = useCandleHistory(tf, candles.data?.candles);
  const loadOlder = useRef(history.loadOlder);
  loadOlder.current = history.loadOlder;
  const analysis = useAnalysis(tf);
  const { source } = useUi();
  const trades = useTrades(source);
  const news = useNews();
  const positions = usePositions();
  const since = history.bars[0]?.time ?? null;
  const bot = useBotOverlays(source, since, overlays.sr || overlays.trendlines || overlays.setups);

  const boxRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaRef = useRef<Record<string, ISeriesApi<"Line">>>({});
  const linesRef = useRef<IPriceLine[]>([]);
  const barsRef = useRef<Bar[]>([]);
  const zonesRef = useRef<DrawZone[]>([]);
  const lastTfRef = useRef<string | null>(null);
  const firstRef = useRef<number | null>(null);
  const LOAD_EDGE_BARS = 20;  // còn ≤ N nến bên trái khung nhìn thì nạp thêm nến cũ
  const [api, setApi] = useState<ChartApi | null>(null);

  const drawZones = useCallback(() => {
    const chart = chartRef.current;
    const series = candleRef.current;
    const layer = overlayRef.current;
    if (!chart || !series || !layer) return;
    layer.replaceChildren();
    const bars = barsRef.current;
    if (!bars.length) return;
    const scale = chart.timeScale();
    const width = scale.width();
    const first = bars[0].time;
    for (const z of zonesRef.current) {
      const top = series.priceToCoordinate(z.high);
      const bottom = series.priceToCoordinate(z.low);
      if (top === null || bottom === null) continue;
      let x = z.start <= first ? 0 : scale.timeToCoordinate(z.start as UTCTimestamp);
      if (x === null) continue;
      x = Math.max(0, x);
      if (x >= width) continue;
      const div = document.createElement("div");
      div.className = "chart-zone";
      Object.assign(div.style, {
        left: `${x}px`, width: `${width - x}px`, top: `${Math.min(top, bottom)}px`,
        height: `${Math.max(2, Math.abs(bottom - top))}px`, background: z.fill, borderColor: z.line,
      });
      const label = document.createElement("span");
      label.textContent = z.label;
      label.style.color = z.line;
      div.appendChild(label);
      layer.appendChild(div);
    }
  }, []);

  // Tạo chart một lần.
  useEffect(() => {
    const box = boxRef.current!;
    const chart = createChart(box, {
      autoSize: true,
      layout: { background: { color: CHART.surface }, textColor: CHART.text, fontFamily: "Inter, Segoe UI, sans-serif" },
      grid: { vertLines: { color: CHART.grid }, horzLines: { color: CHART.grid } },
      rightPriceScale: { borderColor: CHART.grid },
      timeScale: { borderColor: CHART.grid, timeVisible: true, secondsVisible: false, rightOffset: 8 },
      crosshair: { mode: CrosshairMode.Normal },
    });
    candleRef.current = chart.addCandlestickSeries({
      upColor: CHART.candleUp, downColor: CHART.candleDown, borderVisible: false,
      wickUpColor: CHART.candleUp, wickDownColor: CHART.candleDown,
    });
    chartRef.current = chart;
    setApi({ chart, series: candleRef.current });
    let frame = 0;
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(drawZones); };
    chart.timeScale().subscribeVisibleLogicalRangeChange(schedule);
    const nearLeft = (range: { from: number } | null) => { if (range && range.from < LOAD_EDGE_BARS) void loadOlder.current(); };
    chart.timeScale().subscribeVisibleLogicalRangeChange(nearLeft);
    const resize = new ResizeObserver(schedule);
    resize.observe(box);
    const onMove = (e: MouseEvent) => { if (e.buttons) schedule(); };
    box.addEventListener("wheel", schedule, { passive: true });
    box.addEventListener("mousemove", onMove);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      box.removeEventListener("wheel", schedule);
      box.removeEventListener("mousemove", onMove);
      setApi(null);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      emaRef.current = {};
      linesRef.current = [];
    };
  }, [drawZones]);

  // Nến + EMA.
  useEffect(() => {
    const chart = chartRef.current;
    const series = candleRef.current;
    if (!chart || !series || !candles.data || !history.bars.length) return;
    const bars = history.bars.map((c) => ({ ...c, time: shift(c.time) }));
    // Nạp thêm nến cũ phía trước: dời khung nhìn đúng số nến vừa thêm để chart không nhảy.
    const range = chart.timeScale().getVisibleLogicalRange();
    const prevFirst = firstRef.current;
    const added = prevFirst !== null && lastTfRef.current === tf ? bars.findIndex((b) => b.time === prevFirst) : 0;
    firstRef.current = bars[0].time;
    barsRef.current = bars;
    series.setData(bars);
    Object.keys(candles.data.ema).forEach((period, i) => {  // EMA tính trên toàn bộ nến (kể cả nến cũ vừa nạp)
      if (!emaRef.current[period]) {
        emaRef.current[period] = chart.addLineSeries({
          color: CHART.emas[i % CHART.emas.length], lineWidth: 2, priceLineVisible: false,
          lastValueVisible: false, crosshairMarkerVisible: false, title: `EMA${period}`,
        });
      }
      emaRef.current[period].setData(emaPoints(bars, Number(period)).map((p) => ({ ...p, time: p.time as UTCTimestamp })));
    });
    if (lastTfRef.current !== tf) {
      lastTfRef.current = tf;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - 160), to: bars.length + 8 });
    } else if (added > 0 && range) {
      chart.timeScale().setVisibleLogicalRange({ from: range.from + added, to: range.to + added });
    }
  }, [history.bars, candles.data, tf]);

  useEffect(() => {
    Object.values(emaRef.current).forEach((s) => s.applyOptions({ visible: overlays.ema }));
  }, [overlays.ema, history.bars]);

  // Marker: lệnh, tin, swing.
  useEffect(() => {
    const series = candleRef.current;
    const bars = barsRef.current;
    if (!series || !bars.length || !tf) return;
    const lastEnd = bars[bars.length - 1].time + TF_SECONDS[tf];
    const place = (t: number) => (t <= lastEnd ? snapToBar(bars, t) : null);
    const markers: SeriesMarker<Time>[] = [];
    if (overlays.trades) {
      for (const tr of trades.data ?? []) {
        const buy = tr.direction === "BUY";
        const entry = place(isoSeconds(tr.entry_time) + TZ_OFFSET);
        if (entry) markers.push({ time: entry, position: buy ? "belowBar" : "aboveBar", color: buy ? CHART.candleUp : CHART.candleDown,
          shape: buy ? "arrowUp" : "arrowDown", text: SETUP_ABBR[tr.setup] ?? tr.setup });
        const exit = tr.exit_time ? place(isoSeconds(tr.exit_time) + TZ_OFFSET) : null;
        if (exit) markers.push({ time: exit, position: buy ? "aboveBar" : "belowBar", shape: "circle",
          color: tr.r_multiple > 0 ? CHART.positive : CHART.negative, text: `${tr.r_multiple > 0 ? "+" : ""}${tr.r_multiple.toFixed(2)}R` });
      }
    }
    if (overlays.news) {
      for (const ev of news.data?.events ?? []) {
        const t = place(ev.time + TZ_OFFSET);
        if (t) markers.push({ time: t, position: "aboveBar", shape: "square", text: ev.title.slice(0, 18),
          color: ev.gold === "BUY" ? CHART.positive : ev.gold === "SELL" ? CHART.negative : CHART.warn });
      }
    }
    if (overlays.setups) {
      for (const s of bot.data?.setups ?? []) {
        const t = place(s.breakout + TZ_OFFSET);
        if (t) markers.push({ time: t, position: s.direction === "BUY" ? "belowBar" : "aboveBar", shape: "square", size: 0.6,
          color: s.accepted ? SETUP_COLOR[s.direction] : CHART.axis, text: s.accepted ? s.key.split(":")[1] ?? "" : "" });
      }
    }
    if (overlays.swings && analysis.data?.overlays) {
      for (const s of analysis.data.overlays.swings) {
        const t = place(s.time + TZ_OFFSET);
        if (t) markers.push({ time: t, position: s.kind === "high" ? "aboveBar" : "belowBar", color: CHART.axis, shape: "circle", size: 0.4 });
      }
    }
    markers.sort((a, b) => (a.time as number) - (b.time as number));
    series.setMarkers(markers);
  }, [trades.data, news.data, analysis.data, bot.data, overlays.trades, overlays.news, overlays.swings, overlays.setups,
    history.bars, tf]);

  // Đường giá của lệnh đang mở.
  useEffect(() => {
    const series = candleRef.current;
    if (!series) return;
    linesRef.current.forEach((l) => series.removePriceLine(l));
    linesRef.current = [];
    if (!overlays.trades) return;
    const add = (price: number | null | undefined, color: string, title: string) => {
      if (price) linesRef.current.push(series.createPriceLine({ price, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title }));
    };
    for (const leg of positions.data?.legs ?? []) {
      add(leg.entry, CHART.axis, `${leg.leg} entry`);
      add(leg.broker?.sl ?? leg.sl, CHART.candleDown, `SL ${leg.leg}`);
      add(leg.broker?.tp ?? leg.tp, CHART.candleUp, `TP ${leg.leg}`);
    }
  }, [positions.data, overlays.trades]);

  // Vùng S/R, FVG, OB, setup.
  useEffect(() => {
    zonesRef.current = zonesToDraw(analysis.data, barsRef.current, overlays);
    requestAnimationFrame(drawZones);
  }, [analysis.data, history.bars, overlays, drawZones]);

  const fixed = useMemo(() => botShapes(bot.data, overlays), [bot.data, overlays]);

  const axis = useMemo(() => ({
    times: history.bars.map((c) => c.time + TZ_OFFSET), step: TF_SECONDS[tf ?? "H1"] ?? 3600,
  }), [history.bars, tf]);

  const error = candles.error?.message;
  return (
    <div className="chart-box" ref={boxRef}>
      <div className="chart-overlay" ref={overlayRef} />
      {drawing && <DrawingLayer api={api} axis={axis} offset={TZ_OFFSET} fixed={fixed} {...drawing} />}
      {error && <div className="chart-msg">{error}</div>}
      {history.loading && <div className="chart-loading">Đang nạp nến cũ…</div>}
    </div>
  );
}
