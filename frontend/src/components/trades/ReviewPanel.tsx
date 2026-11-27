import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Chip, Group, SegmentedControl, Stack, Text, Textarea } from "@mantine/core";
import {
  createChart, CrosshairMode, LineStyle, type SeriesMarker, type Time, type UTCTimestamp,
} from "lightweight-charts";
import { useReviewChart, useReviewOptions } from "../../api/hooks";
import type { ReviewChartData, ReviewItem } from "../../api/types";
import { timeToLogical, logicalToTime, type Shape, type TimeAxis } from "../../lib/drawing";
import { useShapeEditor, type ShapeEditor } from "../../state/shapeEditor";
import { TZ_OFFSET } from "../../lib/format";
import { saveStateText, useAnnotation } from "../../state/annotation";
import { CHART } from "../../theme";
import { DrawingLayer, type ChartApi } from "../chart/DrawingLayer";
import { DrawToolbar } from "../chart/DrawToolbar";

const TF_SECONDS: Record<string, number> = { M5: 300, M15: 900, M30: 1800, H1: 3600, H2: 7200, H4: 14400, D1: 86400 };
const EDGE_AFTER_BREAK = 6;  // cạnh mẫu hình kéo dài tới sau nến phá (giống ảnh lý do vào lệnh)

/** Lệnh cần nhận xét + khóa lưu nét vẽ/nhận xét. */
export interface ReviewRef extends ReviewItem { scope: string }

/** Khóa nhận xét theo ý tưởng lệnh (setup_key): lệnh đang mở → đóng, và tín hiệu đã vào lệnh dùng chung một nhận xét.
 *  Backtest thêm run_id vì setup_key lặp lại giữa các lần chạy. Không có setup_key thì theo loại + id. */
export function reviewRef(item: ReviewItem, runId: string | null | undefined, setupKey: string | null | undefined): ReviewRef {
  const live = item.mode === "live" || item.mode.startsWith("bot:");
  const scope = setupKey ? `setup:${item.mode}:${live ? "" : `${runId ?? ""}:`}${setupKey}`
    : `${item.kind}:${item.mode}:${runId ?? ""}:${item.key}`;
  return { ...item, scope };
}

/** Cạnh trendline bot đã vẽ thành nét chỉ đọc, kéo dài tới sau nến phá. */
function botEdges(d: ReviewChartData, axis: TimeAxis): Shape[] {
  const brk = timeToLogical(axis, (d.breakout_time ?? d.entry_time) + TZ_OFFSET);
  return d.edges.map(([t1, p1, t2, p2], i) => {
    const a = timeToLogical(axis, t1 + TZ_OFFSET);
    const b = timeToLogical(axis, t2 + TZ_OFFSET);
    const end = Math.max(b, brk + EDGE_AFTER_BREAK);
    const pEnd = b > a ? p1 + ((p2 - p1) / (b - a)) * (end - a) : p2;
    return { id: `bot${i}`, kind: "trend", role: "bot",
      points: [{ t: t1, p: p1 }, { t: logicalToTime(axis, end) - TZ_OFFSET, p: pEnd }] };
  });
}

function snap(times: number[], t: number): UTCTimestamp | null {
  let found: number | null = null;
  for (const x of times) { if (x <= t) found = x; else break; }
  return found as UTCTimestamp | null;
}

/** Chart nến quanh lệnh: vào/SL/TP/mục tiêu, điểm vào/thoát, trendline bot (trắng) + lớp vẽ tay. */
function ReviewChart({ data, editor, colors }: { data: ReviewChartData; editor: ShapeEditor; colors: Record<string, string> }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [api, setApi] = useState<ChartApi | null>(null);
  const axis = useMemo<TimeAxis>(() => ({ times: data.candles.map((c) => c.time + TZ_OFFSET),
    step: TF_SECONDS[data.tf] ?? 3600 }), [data]);
  const fixed = useMemo(() => botEdges(data, axis), [data, axis]);

  useEffect(() => {
    const chart = createChart(boxRef.current!, {
      autoSize: true,
      layout: { background: { color: CHART.surface }, textColor: CHART.text, fontFamily: "Inter, Segoe UI, sans-serif" },
      grid: { vertLines: { color: CHART.grid }, horzLines: { color: CHART.grid } },
      rightPriceScale: { borderColor: CHART.grid },
      timeScale: { borderColor: CHART.grid, timeVisible: true, secondsVisible: false, rightOffset: 6 },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const series = chart.addCandlestickSeries({
      upColor: CHART.candleUp, downColor: CHART.candleDown, borderVisible: false,
      wickUpColor: CHART.candleUp, wickDownColor: CHART.candleDown,
    });
    setApi({ chart, series });
    return () => { setApi(null); chart.remove(); };
  }, []);

  useEffect(() => {
    if (!api) return;
    const { chart, series } = api;
    const times = axis.times;
    series.setData(data.candles.map((c, i) => ({ ...c, time: times[i] as UTCTimestamp })));
    const line = (price: number | null, color: string, title: string, style = LineStyle.Dashed) =>
      price ? series.createPriceLine({ price, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true, title }) : null;
    const lines = [
      line(data.entry, CHART.positive, "Vào"),
      line(data.sl, CHART.candleDown, "SL"),
      data.sl_now && data.sl && Math.abs(data.sl_now - data.sl) >= 0.01 ? line(data.sl_now, "#ff9800", "SL hiện tại") : null,
      line(data.tp, CHART.candleUp, "TP"),
      line(data.target, "#ffb74d", "Mục tiêu", LineStyle.Dotted),
    ].filter((l) => l !== null);
    const markers: SeriesMarker<Time>[] = [];
    const buy = data.direction > 0;
    const entry = snap(times, data.entry_time + TZ_OFFSET);
    if (entry) markers.push({ time: entry, position: buy ? "belowBar" : "aboveBar", shape: buy ? "arrowUp" : "arrowDown",
      color: CHART.positive, text: buy ? "BUY" : "SELL" });
    const exit = data.exit_time ? snap(times, data.exit_time + TZ_OFFSET) : null;
    if (exit) markers.push({ time: exit, position: buy ? "aboveBar" : "belowBar", shape: "circle", color: "#ffeb3b",
      text: data.r != null ? `${data.r > 0 ? "+" : ""}${data.r.toFixed(2)}R` : "Thoát" });
    series.setMarkers(markers);
    const n = times.length;
    const from = Math.max(0, Math.floor(timeToLogical(axis, (fixed[0]?.points[0].t ?? data.entry_time) + TZ_OFFSET)) - 10);
    chart.timeScale().setVisibleLogicalRange({ from: Math.min(from, Math.max(0, n - 60)), to: n + 4 });
    return () => lines.forEach((l) => series.removePriceLine(l));
  }, [api, data, axis, fixed]);

  return (
    <div className="review-chart" ref={boxRef}>
      <DrawingLayer api={api} axis={axis} offset={TZ_OFFSET} editor={editor} fixed={fixed} colors={colors}
        />
    </div>
  );
}

/** Tab "Vẽ & nhận xét": vẽ lên chart của lệnh, chọn kết luận + lỗi sai + ghi chú (tự lưu) để dạy lại quy tắc cho bot. */
export function ReviewPanel({ review }: { review: ReviewRef }) {
  const { scope, kind, mode, key } = review;
  const itemKey = useMemo<ReviewItem>(() => ({ kind, mode, key }), [kind, mode, key]);
  const chart = useReviewChart(itemKey, kind === "leg");
  const { data: options } = useReviewOptions();
  const annotation = useAnnotation(scope, itemKey);
  const { update } = annotation;
  const save = useCallback((shapes: Shape[]) => update({ shapes }), [update]);
  const editor = useShapeEditor(scope, annotation.data?.shapes ?? [], save, "wrong");
  const a = annotation.data;
  if (!options || !a) return <Text size="sm" c="dimmed">Đang tải…</Text>;
  const colors = Object.fromEntries(options.roles.map((r) => [r.key, r.color ?? "#ffb74d"]));
  return (
    <Stack gap="sm">
      <Group justify="space-between" wrap="nowrap">
        <DrawToolbar editor={editor} roles={options.roles} />
        <Text size="xs" c={annotation.state.kind === "error" ? "red" : "dimmed"}>{saveStateText(annotation.state)}</Text>
      </Group>
      {chart.data ? (
        <ReviewChart data={chart.data} editor={editor} colors={colors} />
      ) : (
        <Text size="sm" c="dimmed">{chart.error ? chart.error.message : "Đang tải nến…"}</Text>
      )}
      <Text size="xs" c="dimmed">
        Trắng: trendline bot vẽ · {options.roles.map((r) => r.label).join(" / ")}: nét bạn vẽ · bấm chọn rồi kéo để sửa, Delete xoá, Ctrl+Z hoàn tác
      </Text>
      <Group gap="sm" align="center">
        <Text size="xs" c="dimmed" fw={600} w={90}>KẾT LUẬN</Text>
        <SegmentedControl size="xs" value={a.verdict ?? ""} onChange={(v) => annotation.update({ verdict: v || null })}
          data={[{ value: "", label: "Chưa xét" }, ...options.verdicts.map((v) => ({ value: v.key, label: v.label }))]} />
      </Group>
      <Stack gap={6}>
        <Text size="xs" c="dimmed" fw={600}>LỖI SAI (chọn nhiều)</Text>
        <Chip.Group multiple value={a.errors ?? []} onChange={(v) => annotation.update({ errors: v })}>
          <Group gap={6}>
            {options.error_tags.map((t) => <Chip key={t.key} value={t.key} size="xs" color="red" variant="outline">{t.label}</Chip>)}
          </Group>
        </Chip.Group>
      </Stack>
      <Textarea label="Ghi chú cho bot" placeholder="Vd: nên vẽ trendline nối 2 đỉnh tuần trước, sell ở biên trên thay vì đợi phá biên dưới"
        autosize minRows={2} maxRows={6} value={a.note ?? ""} onChange={(e) => annotation.update({ note: e.currentTarget.value })} />
    </Stack>
  );
}
