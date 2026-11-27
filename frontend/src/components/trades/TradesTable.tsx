import { useState } from "react";
import { Group, Text } from "@mantine/core";
import { IconPhoto } from "@tabler/icons-react";
import { sourceMode } from "../../api/client";
import { useTrades } from "../../api/hooks";
import type { Trade } from "../../api/types";
import { fmt, isoLocal, signed, signedMoney } from "../../lib/format";
import { SETUP_LABEL, kindLabel, label } from "../../lib/labels";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";
import { DirBadge } from "../common/badges";
import { SourceSelect } from "../common/SourceSelect";
import { TradeDrawer, levelBoxes, reasonsOf, contextOf, reviewRef, type TradeDetail } from "./TradeDrawer";

const setupName = (t: Trade) => (t.setup.includes("@") || t.setup_key?.includes("@") ? kindLabel(t.setup_key ?? t.setup)
  : label(SETUP_LABEL, t.setup));

function detailOf(t: Trade, mode: string): TradeDetail {
  return {
    title: `${setupName(t)} · ${t.direction} · ${signed(t.r_multiple)}R`,
    chartUrl: t.chart ? `/api/charts/${encodeURIComponent(mode)}/${t.id}` : null,
    reasons: reasonsOf(t.reasons),
    context: contextOf(t.meta),
    levels: levelBoxes(t.levels, false),
    review: reviewRef({ kind: "trade", mode, key: t.id }, t.run_id, t.setup_key),
    rows: [
      ["Chiều", <DirBadge dir={t.direction} size="xs" />],
      ["Vào → ra", `${isoLocal(t.entry_time)} → ${isoLocal(t.exit_time)}`],
      ["Giá vào", fmt(t.entry)],
      ["Khối lượng", `${fmt(t.volume)} lot`],
      ["Kết quả", <b className={t.r_multiple > 0 ? "up" : "down"}>{signed(t.r_multiple)}R · {signedMoney(t.pnl)}</b>],
      ["Lý do thoát", t.exit_reason],
    ],
  };
}

function Summary({ rows }: { rows: Trade[] }) {
  const wins = rows.filter((t) => t.r_multiple > 0).length;
  const r = rows.reduce((s, t) => s + t.r_multiple, 0);
  const pnl = rows.reduce((s, t) => s + (t.pnl ?? 0), 0);
  return (
    <Group gap="lg" className="num">
      <Text size="xs" c="dimmed">{rows.length} lệnh</Text>
      <Text size="xs" c="dimmed">Thắng {rows.length ? Math.round((wins / rows.length) * 100) : 0}%</Text>
      <Text size="xs">Tổng <b className={r >= 0 ? "up" : "down"}>{signed(r)}R</b></Text>
      <Text size="xs">Lãi/lỗ <b className={pnl >= 0 ? "up" : "down"}>{signedMoney(pnl)}</b></Text>
    </Group>
  );
}

/** Lịch sử lệnh đã đóng (live từng bot hoặc một lần backtest); bấm một dòng để xem chart lý do vào lệnh. */
export function TradesTable() {
  const { source } = useUi();
  const { data = [] } = useTrades(source);
  const [detail, setDetail] = useState<TradeDetail | null>(null);
  const mode = sourceMode(source);
  const rows = data;
  return (
    <>
      <Group gap="md" mb="sm" justify="space-between">
        <SourceSelect width={460} />
        <Summary rows={rows} />
      </Group>
      <DataTable<Trade> rows={rows} rowKey={(r) => r.id} empty="Chưa có lệnh nào ở nguồn này"
        onRowClick={(t) => setDetail(detailOf(t, mode))} columns={[
          { key: "entry_time", label: "Vào", render: (r) => isoLocal(r.entry_time) },
          { key: "exit_time", label: "Ra", render: (r) => isoLocal(r.exit_time) },
          { key: "setup", label: "Mẫu hình", render: setupName },
          { key: "direction", label: "Chiều", render: (r) => <DirBadge dir={r.direction} size="xs" /> },
          { key: "entry", label: "Giá vào", align: "right", render: (r) => fmt(r.entry) },
          { key: "sl", label: "SL", align: "right", render: (r) => fmt(r.sl) },
          { key: "volume", label: "Lot", align: "right", render: (r) => fmt(r.volume) },
          { key: "r", label: "R", align: "right", render: (r) => <b className={r.r_multiple > 0 ? "up" : "down"}>{signed(r.r_multiple)}</b> },
          { key: "pnl", label: "Lãi/lỗ", align: "right", render: (r) => <span className={(r.pnl ?? 0) > 0 ? "up" : "down"}>{signedMoney(r.pnl)}</span> },
          { key: "exit_reason", label: "Lý do thoát" },
          { key: "chart", label: "", render: (r) => (r.chart ? <IconPhoto size={14} aria-label="Có chart" /> : null) },
        ]} />
      <TradeDrawer detail={detail} onClose={() => setDetail(null)} />
    </>
  );
}
