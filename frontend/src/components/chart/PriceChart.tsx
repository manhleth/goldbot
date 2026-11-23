import { useCallback, useEffect, useRef } from "react";
import {
  createChart, CrosshairMode, LineStyle,
  type IChartApi, type IPriceLine, type ISeriesApi, type SeriesMarker, type Time, type UTCTimestamp,
} from "lightweight-charts";
import { useAnalysis, useCandles, useNews, usePositions, useTrades } from "../../api/hooks";
import type { Analysis, Candle, ZoneOverlay } from "../../api/types";
import { isoSeconds, TZ_OFFSET } from "../../lib/format";
import { SETUP_ABBR } from "../../lib/labels";
import { useUi, type Overlay } from "../../state/ui";
import { CHART } from "../../theme";

const TF_SECONDS: Record<string, number> = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400, D1: 86400 };
const SR_EACH_SIDE = 4;
const FVG_EACH_SIDE = 3;
const SETUP_BARS = 40;

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
  if (!a?.ready || !a.overlays || !bars.length) return [];
  const out: DrawZone[] = [];
  const price = bars[bars.length - 1].close;
  const isSetup = (z: ZoneOverlay) => ov.setups && a.setups.some((s) => s.low === z.low && s.high === z.high);
  if (ov.sr) nearestZones(a.overlays.sr_zones, price, SR_EACH_SIDE).forEach((z) =>
    out.push({ ...z, start: shift(z.start), fill: "rgba(140,145,158,.10)", line: "rgba(174,178,188,.5)", label: `S/R ×${z.touches}` }));
  if (ov.fvg) nearestZones(a.overlays.fvgs.filter((z) => !isSetup(z)), price, FVG_EACH_SIDE).forEach((z) => out.push({ ...z, start: shift(z.start), label: "FVG",
    fill: z.direction === "BUY" ? "rgba(38,166,154,.12)" : "rgba(239,83,80,.12)", line: z.direction === "BUY" ? CHART.candleUp : CHART.candleDown }));
  if (ov.ob) nearestZones(a.overlays.order_blocks, price, FVG_EACH_SIDE).forEach((z) => out.push({ ...z, start: shift(z.start), label: "OB", fill: "rgba(144,133,233,.12)", line: "#9085e9" }));
  if (ov.setups) {
    const start = bars[Math.max(0, bars.length - SETUP_BARS)].time;
    a.setups.forEach((s) => out.push({ low: s.low, high: s.high, start, fill: "rgba(57,135,229,.16)", line: CHART.positive,
      label: `${SETUP_ABBR[s.name] ?? s.name} ${s.direction}` }));
  }
  return out;
}

export function PriceChart() {
  const { tf, overlays } = useUi();
  const candles = useCandles(tf, true);
  const analysis = useAnalysis(tf);
  const { source } = useUi();
  const trades = useTrades(source);
  const news = useNews();
  const positions = usePositions();

  const boxRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaRef = useRef<Record<string, ISeriesApi<"Line">>>({});
  const linesRef = useRef<IPriceLine[]>([]);
  const barsRef = useRef<Bar[]>([]);
  const zonesRef = useRef<DrawZone[]>([]);
  const lastTfRef = useRef<string | null>(null);

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
    let frame = 0;
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(drawZones); };
    chart.timeScale().subscribeVisibleLogicalRangeChange(schedule);
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
    if (!chart || !series || !candles.data) return;
    const bars = candles.data.candles.map((c) => ({ ...c, time: shift(c.time) }));
    barsRef.current = bars;
    series.setData(bars);
    Object.entries(candles.data.ema).forEach(([period, points], i) => {
      if (!emaRef.current[period]) {
        emaRef.current[period] = chart.addLineSeries({
          color: CHART.emas[i % CHART.emas.length], lineWidth: 2, priceLineVisible: false,
          lastValueVisible: false, crosshairMarkerVisible: false, title: `EMA${period}`,
        });
      }
      emaRef.current[period].setData(points.map((p) => ({ time: shift(p.time), value: p.value })));
    });
    if (lastTfRef.current !== tf) {
      lastTfRef.current = tf;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - 160), to: bars.length + 8 });
    }
  }, [candles.data, tf]);

  useEffect(() => {
    Object.values(emaRef.current).forEach((s) => s.applyOptions({ visible: overlays.ema }));
  }, [overlays.ema, candles.data]);

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
    if (overlays.swings && analysis.data?.overlays) {
      for (const s of analysis.data.overlays.swings) {
        const t = place(s.time + TZ_OFFSET);
        if (t) markers.push({ time: t, position: s.kind === "high" ? "aboveBar" : "belowBar", color: CHART.axis, shape: "circle", size: 0.4 });
      }
    }
    markers.sort((a, b) => (a.time as number) - (b.time as number));
    series.setMarkers(markers);
  }, [trades.data, news.data, analysis.data, overlays.trades, overlays.news, overlays.swings, candles.data, tf]);

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
  }, [analysis.data, candles.data, overlays, drawZones]);

  const error = candles.error?.message;
  return (
    <div className="chart-box" ref={boxRef}>
      <div className="chart-overlay" ref={overlayRef} />
      {error && <div className="chart-msg">{error}</div>}
    </div>
  );
}
