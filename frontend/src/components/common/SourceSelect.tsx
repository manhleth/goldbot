import { Select } from "@mantine/core";
import { useRuns, useStatus } from "../../api/hooks";
import { signed } from "../../lib/format";
import { BOT_LABEL, label } from "../../lib/labels";
import { useUi } from "../../state/ui";

/** Chọn nguồn dữ liệu lệnh/thống kê: từng bot ONE, bot cũ hoặc một lần backtest. */
export function SourceSelect({ width = 360 }: { width?: number }) {
  const { source, setSource } = useUi();
  const runs = useRuns();
  const status = useStatus();
  const data = [
    ...(status.data?.bots ?? []).map((b) => ({ value: `bot:${b.name}`, label: `${label(BOT_LABEL, b.name)} (demo)` })),
    { value: "live", label: "Live demo (phương pháp cũ)" },
    ...(runs.data ?? []).map((r) => {
      let period = "";
      let name = "Backtest";
      try {
        const p = JSON.parse(r.params);
        period = `${String(p.start).slice(0, 10)} → ${String(p.end).slice(0, 10)}`;
        if (p.title) name = String(p.title);
      } catch { /* params cũ */ }
      return { value: r.run_id, label: `${name} ${period} · ${r.trades} lệnh · ${signed(r.total_r)}R` };
    }),
  ];
  return (
    <Select size="xs" w={width} data={data} value={source} allowDeselect={false}
      onChange={(v) => v && setSource(v)} comboboxProps={{ withinPortal: true }} aria-label="Nguồn dữ liệu" />
  );
}
