import { useCallback, useEffect, useMemo } from "react";
import { Chip, Group, SegmentedControl, Text, Tooltip } from "@mantine/core";
import { useReviewOptions, useStatus } from "../../api/hooks";
import type { Shape } from "../../lib/drawing";
import { useShapeEditor } from "../../state/shapeEditor";
import { useAnnotation } from "../../state/annotation";
import { useUi, type Overlay } from "../../state/ui";
import { SourceSelect } from "../common/SourceSelect";
import { DrawToolbar } from "./DrawToolbar";
import { PriceChart, type ChartDrawing } from "./PriceChart";

/** [lớp, nhãn, giải thích]: nhóm đầu là thứ bot ONE thực sự dùng; FVG/OB/Swing là phân tích cũ. */
const OVERLAYS: [Overlay, string, string][] = [
  ["ema", "EMA", "EMA50 / EMA200"],
  ["sr", "S/R bot", "Vùng kháng cự (đỏ) / hỗ trợ (xanh) gần giá nhất từ các đỉnh/đáy trong quá khứ mà bot dùng lọc lệnh"],
  ["trendlines", "Trendline", "Trendline quan trọng nhất mỗi phía (H4/D1) — nét đứt: đã phá, giá đang retest"],
  ["setups", "Setup bot", "Cạnh mẫu hình các tín hiệu bot đã quét (nét đứt mờ: bị bỏ qua)"],
  ["trades", "Lệnh", "Điểm vào/thoát và SL/TP lệnh đang mở"],
  ["news", "Tin", "Tin kinh tế Mỹ"],
  ["fvg", "FVG", "Phân tích cũ (không dùng trong ONE)"],
  ["ob", "OB", "Phân tích cũ (không dùng trong ONE)"],
  ["swings", "Swing", "Phân tích cũ (không dùng trong ONE)"],
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
  const tfs = useMemo(() => status?.chart_timeframes ?? [], [status]);
  useEffect(() => {
    if (tfs.length && (!tf || !tfs.includes(tf))) setTf(tfs[0]);
  }, [tfs, tf, setTf]);
  const drawing = useChartDrawing(status ? `chart:${status.symbol}` : null);
  return (
    <>
      <Group gap="md" px="sm" py={6} wrap="wrap" style={{ borderBottom: "1px solid var(--line)" }}>
        {tfs.length > 0 && <SegmentedControl size="xs" data={tfs} value={tf ?? undefined} onChange={setTf} />}
        <Group gap={4} wrap="wrap">
          {OVERLAYS.map(([key, label, hint]) => (
            <Tooltip key={key} label={hint} withArrow openDelay={400}>
              <Chip size="xs" variant="light" checked={overlays[key]} onChange={() => toggleOverlay(key)}>{label}</Chip>
            </Tooltip>
          ))}
        </Group>
        {drawing && <DrawToolbar {...drawing.toolbar} />}
        <div style={{ flex: 1 }} />
        <Text size="xs" c="dimmed">Nguồn lệnh</Text>
        <SourceSelect />
      </Group>
      <PriceChart drawing={drawing?.chart} />
    </>
  );
}
