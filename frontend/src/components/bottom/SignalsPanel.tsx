import { useMemo, useState } from "react";
import { Group, SegmentedControl, Stack, Text } from "@mantine/core";
import { useSignals } from "../../api/hooks";
import type { SignalRow } from "../../api/types";
import { fmt, isoLocal } from "../../lib/format";
import { REJECT_LABEL, SETUP_LABEL, label } from "../../lib/labels";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";
import { DirBadge, NewsBadge } from "../common/badges";
import { SourceSelect } from "../common/SourceSelect";

export function SignalsPanel() {
  const { source } = useUi();
  const { data = [] } = useSignals(source);
  const [filter, setFilter] = useState("all");
  const rows = useMemo(() => data.filter((s) => filter === "all" || (filter === "accepted") === Boolean(s.accepted)), [data, filter]);
  return (
    <Stack gap="sm">
      <Group gap="sm">
        <Text size="sm" fw={600}>Nguồn</Text><SourceSelect width={420} />
        <SegmentedControl size="xs" value={filter} onChange={setFilter}
          data={[{ value: "all", label: "Tất cả" }, { value: "accepted", label: "Vào lệnh" }, { value: "rejected", label: "Bị bỏ" }]} />
        <Text size="xs" c="dimmed">{rows.length} tín hiệu (tối đa 1000 gần nhất)</Text>
      </Group>
      <DataTable<SignalRow> rows={rows} rowKey={(r) => r.id} empty="Chưa có tín hiệu nào" columns={[
        { key: "time", label: "Thời gian", render: (r) => isoLocal(r.time) },
        { key: "setup", label: "Setup", render: (r) => label(SETUP_LABEL, r.setup) },
        { key: "direction", label: "Chiều", render: (r) => <DirBadge dir={r.direction} size="xs" /> },
        { key: "trigger", label: "Trigger" },
        { key: "score", label: "Điểm", align: "right" },
        { key: "bias", label: "Bias" },
        { key: "entry", label: "Entry", align: "right", render: (r) => fmt(r.entry) },
        { key: "sl", label: "SL", align: "right", render: (r) => fmt(r.sl) },
        { key: "tp1", label: "TP1", align: "right", render: (r) => fmt(r.tp1) },
        { key: "rr_tp1", label: "R:R", align: "right", render: (r) => fmt(r.rr_tp1) },
        { key: "news", label: "Tin", render: (r) => <NewsBadge value={r.news} /> },
        { key: "result", label: "Kết quả", render: (r) => (r.accepted ? <b className="up">Vào lệnh</b> : <Text size="xs" c="dimmed">{label(REJECT_LABEL, r.reject_reason)}</Text>) },
      ]} />
    </Stack>
  );
}
