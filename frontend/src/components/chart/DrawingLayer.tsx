import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { IChartApi, ISeriesApi, Logical } from "lightweight-charts";
import {
  logicalToTime, newShapeId, POINTS_NEEDED, timeToLogical, type DrawPoint, type Shape, type TimeAxis,
} from "../../lib/drawing";
import type { ShapeEditor } from "../../state/shapeEditor";

export const BOT_COLOR = "#f5f5f5";
const CLICK_PX = 3;  // di chuột ít hơn thế = bấm chọn, không phải kéo

export interface ChartApi { chart: IChartApi; series: ISeriesApi<"Candlestick"> }

interface Props {
  api: ChartApi | null;
  /** Thời gian hiển thị của nến (đã cộng `offset`) + độ dài 1 nến. */
  axis: TimeAxis;
  /** Thời gian hiển thị = UTC + offset (giây). */
  offset: number;
  editor: ShapeEditor;
  /** Nét chỉ đọc (vd trendline bot đã vẽ). */
  fixed?: Shape[];
  colors: Record<string, string>;
}

interface Px { x: number; y: number }
/** Đang kéo: cả nét (index null) hoặc một đầu mút; điểm gốc theo chỉ số nến để kéo qua khoảng nghỉ cuối tuần vẫn đúng. */
interface Drag { id: string; index: number | null; startX: number; startY: number; start: { l: number; p: number };
  orig: { l: number; p: number }[]; moved: boolean }

/** Nhiều chart cùng mở (chart chính + chart trong khung lệnh): phím tắt chỉ áp cho chart dùng gần nhất. */
const layers: symbol[] = [];
const activate = (id: symbol) => { const i = layers.indexOf(id); if (i >= 0) layers.splice(i, 1); layers.push(id); };
const isActive = (id: symbol) => layers[layers.length - 1] === id;
/** Chỉ số nến (có phần lẻ) → toạ độ x. Thư viện chỉ đổi được chỉ số nguyên (lẻ trả 0), nên nội suy giữa hai nến kề —
 *  cần cho điểm nằm giữa hai nến (vd nến H4 gộp theo UTC trên chart H4 của MT5 lệch giờ). */
function logicalX(chart: IChartApi, l: number): number | null {
  if (!Number.isFinite(l)) return null;
  const ts = chart.timeScale();
  const i = Math.floor(l);
  const x0 = ts.logicalToCoordinate(i as Logical);
  if (x0 === null || l === i) return x0;
  const x1 = ts.logicalToCoordinate((i + 1) as Logical);
  return x1 === null ? null : x0 + (l - i) * (x1 - x0);
}

const typing = (e: KeyboardEvent) => {
  const el = e.target as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
};

/** Lớp SVG phủ lên chart: vẽ trendline / đường ngang / vùng; con trỏ: bấm chọn, kéo nét hoặc kéo đầu mút để sửa;
 *  Delete xoá nét đang chọn, Ctrl+Z / Ctrl+Y hoàn tác / làm lại, Esc huỷ. */
export function DrawingLayer({ api, axis, offset, editor, fixed = [], colors }: Props) {
  const { shapes, tool, role, selected } = editor;
  const svgRef = useRef<SVGSVGElement>(null);
  const self = useRef(Symbol("layer")).current;
  const [, setTick] = useState(0);
  const [draft, setDraft] = useState<DrawPoint[]>([]);
  const [hover, setHover] = useState<DrawPoint | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const [dragged, setDragged] = useState<Shape | null>(null);
  const latest = useRef({ editor, shapes });
  latest.current = { editor, shapes };

  useEffect(() => {
    activate(self);
    return () => { const i = layers.indexOf(self); if (i >= 0) layers.splice(i, 1); };
  }, [self]);

  // Vẽ lại khi cuộn/zoom/đổi kích thước/kéo thang giá.
  useEffect(() => {
    const host = svgRef.current?.parentElement;
    if (!api || !host) return;
    let frame = 0;
    const bump = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => setTick((t) => t + 1)); };
    const onMove = (e: MouseEvent) => { if (e.buttons) bump(); };
    const onDown = (e: PointerEvent) => {
      activate(self);
      const target = e.target as Element | null;
      if (!target?.closest?.(".draw-hit, .draw-hit-fill, .draw-handle")) latest.current.editor.setSelected(null);
    };
    api.chart.timeScale().subscribeVisibleLogicalRangeChange(bump);
    const resize = new ResizeObserver(bump);
    resize.observe(host);
    host.addEventListener("wheel", bump, { passive: true });
    host.addEventListener("mousemove", onMove);
    host.addEventListener("pointerdown", onDown, true);
    bump();
    return () => {
      cancelAnimationFrame(frame);
      api.chart.timeScale().unsubscribeVisibleLogicalRangeChange(bump);
      resize.disconnect();
      host.removeEventListener("wheel", bump);
      host.removeEventListener("mousemove", onMove);
      host.removeEventListener("pointerdown", onDown, true);
    };
  }, [api, self]);

  useEffect(() => { setDraft([]); setHover(null); }, [tool]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!isActive(self) || typing(e)) return;
      const key = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && key === "z") { e.preventDefault(); if (e.shiftKey) editor.redo(); else editor.undo(); }
      else if ((e.ctrlKey || e.metaKey) && key === "y") { e.preventDefault(); editor.redo(); }
      else if ((key === "delete" || key === "backspace") && selected) { e.preventDefault(); editor.remove(selected); }
      else if (key === "escape") { setDraft([]); setHover(null); editor.setSelected(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [self, editor, selected]);

  const toPx = useCallback((pt: DrawPoint): Px | null => {
    if (!api) return null;
    const x = logicalX(api.chart, timeToLogical(axis, pt.t + offset));
    const y = api.series.priceToCoordinate(pt.p);
    return x === null || y === null ? null : { x, y };
  }, [api, axis, offset]);

  /** Vị trí chuột → (chỉ số nến, giá). */
  const locate = useCallback((clientX: number, clientY: number): { l: number; p: number } | null => {
    if (!api || !svgRef.current || !axis.times.length) return null;
    const box = svgRef.current.getBoundingClientRect();
    const l = api.chart.timeScale().coordinateToLogical(clientX - box.left);
    const p = api.series.coordinateToPrice(clientY - box.top);
    return l === null || p === null ? null : { l, p };
  }, [api, axis]);

  const toPoint = useCallback((l: number, p: number): DrawPoint =>
    ({ t: Math.round(logicalToTime(axis, l) - offset), p: Math.round(p * 100) / 100 }), [axis, offset]);

  // Kéo nét / đầu mút: theo dõi chuột trên cả cửa sổ, nhả chuột mới ghi (một bước undo).
  useEffect(() => {
    if (!drag) return;
    const shape = latest.current.shapes.find((s) => s.id === drag.id);
    if (!shape) return;
    const apply = (e: PointerEvent): Shape | null => {
      const at = locate(e.clientX, e.clientY);
      if (!at) return null;
      const dl = at.l - drag.start.l;
      const dp = at.p - drag.start.p;
      const points = drag.orig.map((o, i) => (drag.index === null ? toPoint(o.l + dl, o.p + dp)
        : i === drag.index ? toPoint(at.l, at.p) : shape.points[i]));
      return { ...shape, points };
    };
    let last: Shape | null = null;
    let moved = false;
    const onMove = (e: PointerEvent) => {
      moved ||= Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY) > CLICK_PX;
      if (!moved) return;
      last = apply(e);
      setDragged(last);
    };
    const onUp = () => {
      const done = last;
      if (moved && done) {
        const { editor: ed, shapes: all } = latest.current;
        ed.change(all.map((s) => (s.id === done.id ? done : s)));
      }
      setDrag(null);
      setDragged(null);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
    return () => { window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onUp); };
  }, [drag, locate, toPoint]);

  const startDrag = (e: ReactPointerEvent, s: Shape, index: number | null) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.preventDefault();
    if (tool === "erase") { editor.remove(s.id); return; }
    const start = locate(e.clientX, e.clientY);
    if (!start) return;
    editor.setSelected(s.id);
    setDrag({ id: s.id, index, startX: e.clientX, startY: e.clientY, start, moved: false,
      orig: s.points.map((pt) => ({ l: timeToLogical(axis, pt.t + offset), p: pt.p })) });
  };

  const drawing = tool !== "cursor" && tool !== "erase";
  const onPointerDown = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (!drawing || e.button !== 0) return;
    const at = locate(e.clientX, e.clientY);
    if (!at) return;
    const points = [...draft, toPoint(at.l, at.p)];
    if (points.length < POINTS_NEEDED[tool]) { setDraft(points); return; }
    const shape: Shape = { id: newShapeId(), kind: tool, role, points };
    editor.change([...shapes, shape]);
    editor.setSelected(shape.id);
    setDraft([]);
    setHover(null);
    editor.setTool("cursor");
  };
  const onPointerMove = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (!drawing || !draft.length) return;
    const at = locate(e.clientX, e.clientY);
    setHover(at && toPoint(at.l, at.p));
  };

  const width = api?.chart.timeScale().width() ?? 0;
  const preview = useMemo<Shape | null>(() => (drawing && draft.length && hover
    ? { id: "draft", kind: tool, role, points: [...draft, hover] } : null), [drawing, draft, hover, tool, role]);
  const editable = tool === "cursor" || tool === "erase";

  /** Điểm cuối kéo dài theo độ dốc tính trên chỉ số nến (đúng như đường thẳng hiển thị trên chart). */
  const extended = (s: Shape): Px | null => {
    const [p1, p2] = s.points;
    const l1 = timeToLogical(axis, p1.t + offset);
    const l2 = timeToLogical(axis, p2.t + offset);
    const le = timeToLogical(axis, s.extendTo! + offset);
    if (!(l2 > l1)) return null;
    return toPx({ t: s.extendTo!, p: p1.p + ((p2.p - p1.p) * (le - l1)) / (l2 - l1) });
  };

  /** Vòng tròn đánh dấu các lần chạm, nhãn phía trên (đỉnh) / dưới (đáy) điểm. */
  const marksOf = (s: Shape, color: string) => s.marks?.map((m, i) => {
    const p = toPx(m);
    if (!p) return null;
    const below = m.text?.startsWith("Đáy");
    return (
      <g key={`m${i}`}>
        <circle cx={p.x} cy={p.y} r={5} fill="none" stroke={color} strokeWidth={1.5} />
        {m.text && <text x={p.x} y={p.y + (below ? 17 : -9)} fill={color} fontSize={10} textAnchor="middle">{m.text}</text>}
      </g>
    );
  });

  const render = (s: Shape, interactive: boolean) => {
    const color = s.style?.color ?? (s.role === "bot" ? BOT_COLOR : colors[s.role] ?? "#ffb74d");
    const pts = s.points.map(toPx);
    if (pts.some((p) => p === null)) return null;
    const [a, b] = pts as Px[];
    const live = interactive && editable;
    const isSel = interactive && selected === s.id;
    const erase = tool === "erase" ? " erase" : "";
    const body = live ? { onPointerDown: (e: ReactPointerEvent) => startDrag(e, s, null), className: `draw-hit${erase}` } : null;
    const handles = isSel && tool === "cursor" ? (pts as Px[]).map((p, i) => (
      <circle key={i} cx={s.kind === "hline" ? Math.min(width - 40, Math.max(40, width / 2)) : p.x} cy={p.y} r={5}
        className="draw-handle" stroke={color} onPointerDown={(e) => startDrag(e, s, i)} />
    )) : null;
    const weight = isSel ? 2.5 : s.kind === "trend" ? 2 : 1.5;
    if (s.kind === "hline") {
      return (
        <g key={s.id}>
          <line x1={0} x2={width} y1={a.y} y2={a.y} stroke={color} strokeWidth={weight} strokeDasharray="6 4" />
          <text x={width - 4} y={a.y - 4} fill={color} fontSize={11} textAnchor="end">{s.points[0].p.toFixed(2)}</text>
          {body && <line x1={0} x2={width} y1={a.y} y2={a.y} {...body} />}
          {handles}
        </g>
      );
    }
    if (s.kind === "zone") {
      const x = Math.min(a.x, b.x);
      const y = Math.min(a.y, b.y);
      return (
        <g key={s.id} opacity={s.style?.opacity}>
          <rect x={x} y={y} width={Math.abs(b.x - a.x)} height={Math.max(2, Math.abs(b.y - a.y))} fill={color}
            fillOpacity={0.14} stroke={color} strokeWidth={isSel ? 2 : s.style?.width ?? 1}
            className={body ? `draw-hit-fill${erase}` : undefined} onPointerDown={body?.onPointerDown} />
          {s.text && <text x={Math.min(Math.max(a.x, b.x), width) - 6} y={y - 5} fill={color} fontSize={11}
            fontWeight={600} textAnchor="end">{s.text}</text>}
          {marksOf(s, color)}
          {handles}
        </g>
      );
    }
    const end = s.extendTo !== undefined ? extended(s) ?? b : b;
    return (
      <g key={s.id} opacity={s.style?.opacity}>
        <line x1={a.x} y1={a.y} x2={end.x} y2={end.y} stroke={color} strokeWidth={s.style?.width ?? weight}
          strokeDasharray={s.style?.dash} />
        {s.text && <text x={Math.min(end.x, width) - 4} y={end.y - 6} fill={color} fontSize={11} fontWeight={600}
          textAnchor="end">{s.text}</text>}
        {marksOf(s, color)}
        {!isSel && <><circle cx={a.x} cy={a.y} r={3} fill={color} /><circle cx={b.x} cy={b.y} r={3} fill={color} /></>}
        {body && <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} {...body} />}
        {handles}
      </g>
    );
  };

  return (
    <svg ref={svgRef} className={`draw-layer${drawing ? " drawing" : ""}${drag ? " dragging" : ""}`}
      onPointerDown={onPointerDown} onPointerMove={onPointerMove}>
      {fixed.map((s) => render(s, false))}
      {shapes.map((s) => render(dragged?.id === s.id ? dragged : s, true))}
      {preview && render(preview, false)}
      {drawing && draft.length === 1 && hover === null && (() => {
        const p = toPx(draft[0]);
        return p ? <circle cx={p.x} cy={p.y} r={3} fill={colors[role]} /> : null;
      })()}
    </svg>
  );
}
