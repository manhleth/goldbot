import { useMemo, useState } from "react";
import { Group, SegmentedControl, Stack, Text } from "@mantine/core";
import { sourceMode } from "../../api/client";
import { useSignals } from "../../api/hooks";
import type { SignalRow } from "../../api/types";
import { isoLocal } from "../../lib/format";
import { REJECT_LABEL, SETUP_LABEL, kindLabel, label } from "../../lib/labels";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";
import { DirBadge } from "../common/badges";
import { SourceSelect } from "../common/SourceSelect";
import { reasonsOf, TradeDrawer, type TradeDetail } from "../trades/TradeDrawer";
import { signalDetail } from "../signals/signalDetail";

const nameOf = (s: SignalRow) => (s.setup_key?.includes("@") ? kindLabel(s.setup_key) : label(SETUP_LABEL, s.setup));

/** Mọi tín hiệu của một nguồn (bot hoặc lần backtest); bấm một dòng để xem lý do vào lệnh và chart. */
export function SignalsPanel() {
  const { source } = useUi();
  const { data = [] } = useSignals(source);
  const [filter, setFilter] = useState("all");
  const [detail, setDetail] = useState<TradeDetail | null>(null);
  const rows = useMemo(() => data.filter((s) => filter === "all" || (filter === "accepted") === Boolean(s.accepted)), [data, filter]);
  const mode = sourceMode(source);
  const bot = mode.startsWith("bot:") ? mode.slice(4) : undefined;
  return (
    <Stack gap="sm">
      <Group gap="sm">
        <SourceSelect width={460} />
        <SegmentedControl size="xs" value={filter} onChange={setFilter}
          data={[{ value: "all", label: "Tất cả" }, { value: "accepted", label: "Vào lệnh" }, { value: "rejected", label: "Bị bỏ" }]} />
        <Text size="xs" c="dimmed">{rows.length} tín hiệu (tối đa 1000 gần nhất) · bấm một dòng để xem lý do và chart</Text>
      </Group>
      <DataTable<SignalRow> rows={rows} rowKey={(r) => r.id} empty="Chưa có tín hiệu nào"
        onRowClick={(s) => setDetail(signalDetail(s, mode, bot))} columns={[
          { key: "time", label: "Thời gian", render: (r) => isoLocal(r.time) },
          { key: "setup", label: "Mẫu hình", render: nameOf },
          { key: "direction", label: "Chiều", render: (r) => <DirBadge dir={r.direction} size="xs" /> },
          { key: "why", label: "Lý do vào lệnh", render: (r) => (
            <Text size="xs" truncate maw={420}>{reasonsOf(r.reasons).slice(1).join(" · ") || "—"}</Text>) },
          { key: "result", label: "Kết quả", render: (r) => (r.accepted ? <b className="up">Vào lệnh</b>
            : <Text size="xs" c="dimmed">{label(REJECT_LABEL, r.reject_reason)}</Text>) },
        ]} />
      <TradeDrawer detail={detail} onClose={() => setDetail(null)} />
    </Stack>
  );
}
