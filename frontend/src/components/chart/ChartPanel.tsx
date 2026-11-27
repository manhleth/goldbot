import { useCallback, useEffect, useMemo } from "react";
import { Checkbox, Group, SegmentedControl, Text } from "@mantine/core";
import { useReviewOptions, useStatus } from "../../api/hooks";
import type { Shape } from "../../lib/drawing";
import { useShapeEditor } from "../../state/shapeEditor";
import { useAnnotation } from "../../state/annotation";
import { useUi, type Overlay } from "../../state/ui";
import { SourceSelect } from "../common/SourceSelect";
import { DrawToolbar } from "./DrawToolbar";
import { PriceChart, type ChartDrawing } from "./PriceChart";

const OVERLAYS: [Overlay, string][] = [
  ["ema", "EMA"], ["sr", "S/R"], ["fvg", "FVG"], ["ob", "OB"], ["swings", "Swing"],
  ["setups", "Setup"], ["trades", "Lệnh"], ["news", "Tin"],
];

/** Nét vẽ tay của chart chung (một bộ cho mọi khung, lưu theo symbol). */
function useChartDrawing(scope: string | null) {
  const { data: options } = useReviewOptions();
  const key = scope ?? "chart:none";
  const annotation = useAnnotation(key);
  const { update } = annotation;
  const save = useCallback((shapes: Shape[]) => update({ shapes }), [update]);
  const editor = useShapeEditor(key, annotation.data?.shapes ?? [], save, "note");
  if (!scope || !options || !annotation.data) return null;
  const chart: ChartDrawing = { editor, colors: Object.fromEntries(options.roles.map((r) => [r.key, r.color ?? "#ffb74d"])) };
  return { chart, toolbar: { editor, roles: options.roles } };
}

/** Thanh công cụ kiểu TradingView (khung thời gian, lớp hiển thị, nguồn lệnh) + biểu đồ giá. */
export function ChartPanel() {
  const { overlays, toggleOverlay, tf, setTf } = useUi();
  const { data: status } = useStatus();
  const tfs = useMemo(() => {
    if (!status) return [];
    const t = status.timeframes;
    return [...new Set([t.trigger, t.setup, ...[...t.bias].reverse()])];
  }, [status]);
  useEffect(() => {
    if (tfs.length && (!tf || !tfs.includes(tf))) setTf(tfs[0]);
  }, [tfs, tf, setTf]);
  const drawing = useChartDrawing(status ? `chart:${status.symbol}` : null);
  return (
    <>
      <Group gap="md" px="sm" py={6} wrap="wrap" style={{ borderBottom: "1px solid var(--line)" }}>
        {tfs.length > 0 && <SegmentedControl size="xs" data={tfs} value={tf ?? undefined} onChange={setTf} />}
        {OVERLAYS.map(([key, label]) => (
          <Checkbox key={key} size="xs" label={label} checked={overlays[key]} onChange={() => toggleOverlay(key)} />
        ))}
        {drawing && <DrawToolbar {...drawing.toolbar} />}
        <div style={{ flex: 1 }} />
        <Text size="xs" c="dimmed">Nguồn lệnh</Text>
        <SourceSelect />
      </Group>
      <PriceChart drawing={drawing?.chart} />
    </>
  );
}
