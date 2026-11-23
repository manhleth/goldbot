import { Group, Stack, Text } from "@mantine/core";
import { sourceMode } from "../../api/client";
import { useTrades } from "../../api/hooks";
import type { Trade } from "../../api/types";
import { fmt, isoLocal, signed, signedMoney } from "../../lib/format";
import { SETUP_LABEL, label } from "../../lib/labels";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";
import { DirBadge, NewsBadge } from "../common/badges";
import { SourceSelect } from "../common/SourceSelect";

export function TradesPanel() {
  const { source } = useUi();
  const { data = [] } = useTrades(source);
  return (
    <Stack gap="sm">
      <Group gap="sm"><Text size="sm" fw={600}>Nguồn</Text><SourceSelect width={420} /><Text size="xs" c="dimmed">{data.length} lệnh</Text></Group>
      <DataTable<Trade> rows={data} rowKey={(r) => r.id} empty="Chưa có lệnh nào ở nguồn này" columns={[
        { key: "entry_time", label: "Vào", render: (r) => isoLocal(r.entry_time) },
        { key: "exit_time", label: "Ra", render: (r) => isoLocal(r.exit_time) },
        { key: "setup", label: "Setup", render: (r) => label(SETUP_LABEL, r.setup) },
        { key: "direction", label: "Chiều", render: (r) => <DirBadge dir={r.direction} size="xs" /> },
        { key: "entry", label: "Entry", align: "right", render: (r) => fmt(r.entry) },
        { key: "sl", label: "SL", align: "right", render: (r) => fmt(r.sl) },
        { key: "tp1", label: "TP1", align: "right", render: (r) => fmt(r.tp1) },
        { key: "tp2", label: "TP2", align: "right", render: (r) => fmt(r.tp2) },
        { key: "volume", label: "Lot", align: "right", render: (r) => fmt(r.volume) },
        { key: "r", label: "R", align: "right", render: (r) => <b className={r.r_multiple > 0 ? "up" : "down"}>{signed(r.r_multiple)}</b> },
        { key: "pnl", label: "Lãi/lỗ", align: "right", render: (r) => <span className={(r.pnl ?? 0) > 0 ? "up" : "down"}>{signedMoney(r.pnl)}</span> },
        { key: "mae", label: "MAE/MFE (R)", align: "right", render: (r) => `${fmt(r.mae_r)} / ${fmt(r.mfe_r)}` },
        { key: "news", label: "Tin", render: (r) => <NewsBadge value={r.news} /> },
        { key: "exit_reason", label: "Lý do thoát" },
        { key: "chart", label: "Chart", render: (r) => (r.chart
          ? <a href={`/api/charts/${encodeURIComponent(sourceMode(source))}/${r.id}`} target="_blank" rel="noreferrer">Xem</a>
          : "—") },
      ]} />
    </Stack>
  );
}
