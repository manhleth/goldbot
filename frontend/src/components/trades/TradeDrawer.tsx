import { useEffect, useState, type ReactNode } from "react";
import { Drawer, Group, Stack, Table, Tabs, Text } from "@mantine/core";
import type { Levels, MoneyLevel } from "../../api/types";
import { fmt, signedMoney } from "../../lib/format";
import { ReviewPanel, type ReviewRef } from "./ReviewPanel";

export { reviewRef } from "./ReviewPanel";

/** Một ô mức giá: SL / TP / mục tiêu, kèm số tiền nếu giá chạm. */
export interface LevelBox {
  label: string;
  level: MoneyLevel | null | undefined;
  hint?: string;
  /** Hiện khi không có mức này (vd "Không đặt TP"). */
  empty?: string;
}

export interface TradeDetail {
  title: ReactNode;
  chartUrl: string | null;
  /** Lệnh đang mở: ảnh trạng thái hiện tại (vẽ lại theo nến mới nhất). */
  liveChartUrl?: string | null;
  levels?: LevelBox[];
  rows: [string, ReactNode][];
  reasons: string[];
  /** Bối cảnh thị trường lúc vào lệnh: xu hướng H4, vĩ mô, ADX. */
  context?: string[];
  /** Có thì thêm tab "Vẽ & nhận xét" (chart tương tác để vẽ và chỉ ra lỗi sai). */
  review?: ReviewRef;
}

function parseReasons(raw: string | string[] | null | undefined): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.map(String) : [String(v)];
  } catch {
    return [raw];
  }
}

export const reasonsOf = parseReasons;

/** Các dòng bối cảnh (meta.context.lines) do bot ghi lúc vào lệnh; lệnh cũ chưa có thì rỗng. */
export function contextOf(meta: string | null | undefined): string[] {
  if (!meta) return [];
  try {
    const lines = JSON.parse(meta)?.context?.lines;
    return Array.isArray(lines) ? lines.map(String) : [];
  } catch {
    return [];
  }
}

/** Ô SL/TP/mục tiêu cho lệnh: dùng chung cho lệnh đang mở và đã đóng. */
export function levelBoxes(levels: Levels | undefined, open: boolean): LevelBox[] {
  const l = levels ?? {};
  const boxes: LevelBox[] = [];
  if (open) {
    boxes.push({ label: "SL ban đầu", level: l.sl_initial, hint: "Mất nếu chạm SL lúc vào lệnh (rủi ro đã định)" });
    const trailed = l.sl && l.sl_initial && Math.abs(l.sl.price - l.sl_initial.price) >= 0.01;  // MT5 làm tròn giá SL
    boxes.push({
      label: trailed ? "SL hiện tại (đã dời)" : "SL hiện tại", level: l.sl,
      hint: l.sl && l.sl.money >= 0 ? "Lời đã chốt chắc nếu giá quay đầu chạm SL" : "Mất nếu giá chạm SL bây giờ",
    });
  } else {
    boxes.push({ label: "SL ban đầu", level: l.sl, hint: "Mất nếu chạm SL lúc vào lệnh (rủi ro đã định)" });
  }
  boxes.push({ label: "TP", level: l.tp, empty: "Không đặt TP — gồng lệnh, dời SL theo đỉnh/đáy" });
  boxes.push({ label: "Mục tiêu tham khảo", level: l.target, hint: "Measured move của mẫu hình (bot không đặt lệnh chốt ở đây)",
    empty: "Không có" });
  return boxes;
}

function LevelCard({ box }: { box: LevelBox }) {
  const lv = box.level;
  return (
    <div className="level-card">
      <Text size="xs" c="dimmed" fw={600} tt="uppercase">{box.label}</Text>
      {lv ? (
        <>
          <Text size="lg" fw={600} className="num">{fmt(lv.price)}</Text>
          <Text size="md" fw={700} className={`num ${lv.money >= 0 ? "up" : "down"}`}>{signedMoney(lv.money)}</Text>
          {box.hint && <Text size="xs" c="dimmed">{box.hint}</Text>}
        </>
      ) : (
        <Text size="sm" c="dimmed" mt={4}>{box.empty ?? "—"}</Text>
      )}
    </div>
  );
}

function ReasonChart({ url }: { url: string | null }) {
  const [failed, setFailed] = useState<string | null>(null);
  useEffect(() => setFailed(null), [url]);
  if (!url || failed === url) {
    return (
      <Text size="sm" c="dimmed">
        Không có chart: lệnh/tín hiệu của phương pháp cũ, hoặc tín hiệu cũ chưa lưu hình học mẫu hình.
      </Text>
    );
  }
  return <img src={url} alt="Chart lý do vào lệnh" className="trade-chart" onError={() => setFailed(url)} />;
}

const LIVE_REFRESH_MS = 60_000;

/** Ảnh hiện tại của lệnh đang mở: tải lại mỗi phút (thêm tham số thời gian để không dùng ảnh cũ). */
function LiveChart({ url }: { url: string }) {
  const [tick, setTick] = useState(() => Date.now());
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const id = setInterval(() => setTick(Date.now()), LIVE_REFRESH_MS);
    return () => clearInterval(id);
  }, [url]);
  useEffect(() => setFailed(false), [url, tick]);
  if (failed) return <Text size="sm" c="dimmed">Không lấy được nến để vẽ trạng thái hiện tại (MT5 chưa kết nối?).</Text>;
  return (
    <Stack gap={4}>
      <img src={`${url}?t=${tick}`} alt="Chart hiện tại của lệnh" className="trade-chart" onError={() => setFailed(true)} />
      <Text size="xs" c="dimmed">
        Tự cập nhật mỗi phút · cam: SL hiện tại (đã dời) · đỏ: SL ban đầu · trắng chấm: giá hiện tại
      </Text>
    </Stack>
  );
}

function Charts({ detail }: { detail: TradeDetail }) {
  if (!detail.liveChartUrl && !detail.review) return <ReasonChart url={detail.chartUrl} />;
  return (
    <Tabs defaultValue={detail.liveChartUrl ? "now" : "entry"} keepMounted={false}>
      <Tabs.List>
        {detail.liveChartUrl && <Tabs.Tab value="now">Hiện tại</Tabs.Tab>}
        <Tabs.Tab value="entry">Lúc vào lệnh</Tabs.Tab>
        {detail.review && <Tabs.Tab value="review">Vẽ & nhận xét</Tabs.Tab>}
      </Tabs.List>
      {detail.liveChartUrl && <Tabs.Panel value="now" pt="sm"><LiveChart url={detail.liveChartUrl} /></Tabs.Panel>}
      <Tabs.Panel value="entry" pt="sm"><ReasonChart url={detail.chartUrl} /></Tabs.Panel>
      {detail.review && <Tabs.Panel value="review" pt="sm"><ReviewPanel review={detail.review} /></Tabs.Panel>}
    </Tabs>
  );
}

/** Khung chi tiết lệnh/tín hiệu trượt từ phải (kiểu Binance/MT5): chart lý do + SL/TP kèm tiền + lý do + thông số. */
export function TradeDrawer({ detail, onClose }: { detail: TradeDetail | null; onClose: () => void }) {
  return (
    <Drawer opened={detail !== null} onClose={onClose} position="right" size={1000} title={detail?.title}
      overlayProps={{ backgroundOpacity: 0.4, blur: 1 }}>
      {detail && (
        <Stack gap="md">
          <Charts detail={detail} />
          {detail.levels && (
            <div className="level-grid">{detail.levels.map((b) => <LevelCard key={b.label} box={b} />)}</div>
          )}
          <Stack gap={4}>
            <Text size="xs" c="dimmed" fw={600}>XU HƯỚNG LÚC VÀO LỆNH</Text>
            {detail.context && detail.context.length > 0
              ? detail.context.map((r) => <Text key={r} size="sm">• {r}</Text>)
              : <Text size="sm" c="dimmed">Lệnh/tín hiệu cũ chưa ghi bối cảnh xu hướng.</Text>}
          </Stack>
          <Stack gap={4}>
            <Text size="xs" c="dimmed" fw={600}>LÝ DO VÀO LỆNH</Text>
            {detail.reasons.length > 0
              ? detail.reasons.map((r) => <Text key={r} size="sm">• {r}</Text>)
              : <Text size="sm" c="dimmed">Không có lý do được ghi lại.</Text>}
          </Stack>
          <Table withRowBorders={false} fz="sm" className="num" verticalSpacing={4}>
            <Table.Tbody>
              {detail.rows.map(([k, v]) => (
                <Table.Tr key={k}>
                  <Table.Td c="dimmed" w={180}>{k}</Table.Td>
                  <Table.Td><Group gap={6}>{v}</Group></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Text size="xs" c="dimmed">Số tiền tính theo khối lượng lệnh và thông số hợp đồng, chưa gồm spread/trượt giá khi khớp.</Text>
        </Stack>
      )}
    </Drawer>
  );
}
