import { useEffect, useRef, useState } from "react";
import { Badge, Button, Card, Checkbox, Group, MultiSelect, NumberInput, ScrollArea, SimpleGrid, Stack, Text, TextInput } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { IconPlayerPlay, IconPlayerStop } from "@tabler/icons-react";
import { actions, useAction, useBacktestMethods, useBacktestStatus, useRuns } from "../../api/hooks";
import type { BacktestMethod, RiskCaps, Run } from "../../api/types";
import { RiskCapsInput } from "../common/RiskCapsInput";
import { isoLocal, signed } from "../../lib/format";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";

const isoDate = (d: Date) => d.toISOString().slice(0, 10);
const DEFAULT_CAPITAL = 1000;
const money = (v: number) => v.toLocaleString("vi-VN", { maximumFractionDigits: 0 });

/** Chọn phương pháp ONE + vốn và % rủi ro riêng từng phương pháp (mặc định: bot live đang chạy; vốn = 1.000$ × phần
 * chia của config; % theo config). */
function useBacktestForm(methods: BacktestMethod[] | undefined) {
  const [selected, setSelected] = useState<string[]>([]);
  const [capital, setCapital] = useState<Record<string, number>>({});
  const [risk, setRisk] = useState<Record<string, number>>({});
  const [maxLot, setMaxLot] = useState<Record<string, number | "">>({});
  const [caps, setCaps] = useState<Record<string, RiskCaps>>({});
  useEffect(() => {
    if (!methods || selected.length) return;
    setSelected(methods.filter((m) => m.bot).map((m) => m.name));
    setCapital(Object.fromEntries(methods.map((m) => [m.name, DEFAULT_CAPITAL * m.capital_share])));
    setRisk(Object.fromEntries(methods.map((m) => [m.name, m.risk_pct ?? 1])));
    setMaxLot(Object.fromEntries(methods.map((m) => [m.name, m.max_lot ?? ""])));
    setCaps(Object.fromEntries(methods.map((m) => [m.name, m.risk_caps ?? []])));
  }, [methods, selected.length]);
  const capitalOf = (name: string) => capital[name] ?? DEFAULT_CAPITAL;
  return { selected, setSelected, capital, setCapital, capitalOf, risk, setRisk, maxLot, setMaxLot, caps, setCaps };
}

function period(run: Run) {
  try {
    const p = JSON.parse(run.params);
    const range = `${String(p.start).slice(0, 10)} → ${String(p.end).slice(0, 10)}`;
    return p.title ? `${p.title} · ${range}` : range;
  } catch {
    return "—";
  }
}

export function BacktestPanel() {
  const today = new Date();
  const [start, setStart] = useState(isoDate(new Date(today.getFullYear() - 3, today.getMonth(), today.getDate())));
  const [end, setEnd] = useState(isoDate(today));
  const [refresh, setRefresh] = useState(false);
  const [cent, setCent] = useState(false);
  const methods = useBacktestMethods();
  const form = useBacktestForm(methods.data);
  const byName = Object.fromEntries((methods.data ?? []).map((m) => [m.name, m]));
  const status = useBacktestStatus();
  const runs = useRuns();
  const { setSource, setPage } = useUi();
  const qc = useQueryClient();
  const wasRunning = useRef(false);
  const run = useAction(actions.runBacktest, { success: () => "Đã bắt đầu backtest", invalidate: [["backtest-status"]] });
  const stop = useAction(actions.stopBacktest, { success: () => "Đã dừng backtest", invalidate: [["backtest-status"]] });

  const running = status.data?.running ?? false;
  useEffect(() => {
    if (running) wasRunning.current = true;
    else if (wasRunning.current && status.data) {
      wasRunning.current = false;
      qc.invalidateQueries({ queryKey: ["runs"] });
      if (status.data.exit_code === 0 && status.data.run_id) {
        const n = status.data.run_ids?.length ?? 1;
        notifications.show({ color: "teal", message: `Backtest xong ${n} phương pháp — đang mở thống kê phương pháp đầu` });
        setSource(status.data.run_id);
        setPage("stats");
      }
    }
  }, [running, status.data, qc, setSource, setPage]);

  const openRun = (r: Run) => { setSource(r.run_id); setPage("stats"); };
  const stateBadge = running ? <Badge color="blue">Đang chạy</Badge>
    : status.data?.exit_code === 0 ? <Badge color="teal">Hoàn tất</Badge>
      : status.data?.exit_code ? <Badge color="red">Lỗi (mã {status.data.exit_code})</Badge> : null;

  return (
    <Stack gap="sm">
      <Group gap="sm" align="flex-end">
        <TextInput size="xs" type="date" label="Từ ngày" value={start} onChange={(e) => setStart(e.currentTarget.value)} />
        <TextInput size="xs" type="date" label="Đến ngày" value={end} onChange={(e) => setEnd(e.currentTarget.value)} />
        <Checkbox size="xs" label="Tải lại dữ liệu MT5" checked={refresh} onChange={(e) => setRefresh(e.currentTarget.checked)} mb={6} />
        <Checkbox size="xs" label="Tài khoản cent" checked={cent} onChange={(e) => setCent(e.currentTarget.checked)} mb={6}
          title="1 lot cent = 0,01 lot thường: vốn nhỏ vẫn vào lệnh đúng % rủi ro. Lot tối đa nhập theo lot thường." />
        <Button size="xs" leftSection={<IconPlayerPlay size={14} />} disabled={running || !form.selected.length}
          loading={run.isPending}
          onClick={() => run.mutate({ start, end, refresh, cent, methods: form.selected,
            capital: Object.fromEntries(form.selected.map((m) => [m, form.capitalOf(m)])),
            risk: Object.fromEntries(form.selected.map((m) => [m, form.risk[m] ?? 1])),
            max_lot: Object.fromEntries(form.selected.filter((m) => form.maxLot[m]).map((m) => [m, Number(form.maxLot[m])])),
            risk_caps: Object.fromEntries(form.selected.filter((m) => form.caps[m]?.length).map((m) => [m, form.caps[m]])) })}>
          Chạy backtest</Button>
        <Button size="xs" variant="default" leftSection={<IconPlayerStop size={14} />} disabled={!running} onClick={() => stop.mutate(undefined)}>Dừng</Button>
        {stateBadge}
      </Group>
      <MultiSelect size="xs" label="Phương pháp" placeholder="Chọn phương pháp" searchable
        data={(methods.data ?? []).map((m) => ({ value: m.name, label: `${m.title}${m.bot ? " · đang chạy live" : ""}` }))}
        value={form.selected} onChange={form.setSelected} />
      {form.selected.length > 0 && (
        <Stack gap={6}>
          {form.selected.map((name) => {
            const m = byName[name];
            const capital = form.capitalOf(name);
            const pct = form.risk[name] ?? 1;
            return (
              <Group key={name} gap="sm" align="flex-start" wrap="nowrap">
                <Text size="xs" w={260} truncate="end" title={m?.title}>{m?.bot ? `Bot ${m.bot}` : name} · {m?.title}</Text>
                <NumberInput size="xs" w={140} label="Vốn ($)" min={10} step={100} thousandSeparator=","
                  value={capital} onChange={(v) => form.setCapital({ ...form.capital, [name]: Number(v) || DEFAULT_CAPITAL })} />
                <NumberInput size="xs" w={150} label="Rủi ro (% vốn/lệnh)" min={0.1} max={100} step={0.5} decimalScale={2}
                  value={pct} onChange={(v) => form.setRisk({ ...form.risk, [name]: Number(v) || 1 })} />
                <NumberInput size="xs" w={110} label="Lot tối đa" placeholder="không giới hạn" min={0.01} step={1}
                  decimalScale={2} value={form.maxLot[name] ?? ""}
                  onChange={(v) => form.setMaxLot({ ...form.maxLot, [name]: v === "" ? "" : Number(v) })} />
                <RiskCapsInput value={form.caps[name] ?? []} onChange={(v) => form.setCaps({ ...form.caps, [name]: v })} />
                <Text size="xs" c="dimmed" mt={26}>≈ {money(capital * pct / 100)}$ mỗi lệnh lúc đầu</Text>
              </Group>
            );
          })}
          <Text size="xs" fw={600}>Tổng vốn: {money(form.selected.reduce((sum, n) => sum + form.capitalOf(n), 0))}$</Text>
        </Stack>
      )}
      <Text size="xs" c="dimmed">Chạy cùng logic bot live (nến M15, gồng SL theo đỉnh/đáy). Mỗi phương pháp chạy với vốn riêng đã nhập, lãi kép theo % rủi ro. Quy tắc khác lấy từ playbook.yaml; mỗi lần chạy lưu kèm phiên bản config.</Text>
      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="sm">
        <Card padding="xs">
          <Text size="xs" c="dimmed" mb={4}>Nhật ký lần chạy gần nhất</Text>
          <ScrollArea h={260}><pre className="pre">{status.data?.log || "Chưa chạy backtest nào trong phiên này."}</pre></ScrollArea>
        </Card>
        <Card padding="xs">
          <Text size="xs" c="dimmed" mb={4}>Các lần backtest — bấm để xem thống kê</Text>
          <ScrollArea h={260}>
            <DataTable<Run> rows={runs.data ?? []} rowKey={(r) => r.run_id} onRowClick={openRun} empty="Chưa có lần backtest nào" columns={[
              { key: "created_at", label: "Chạy lúc", render: (r) => isoLocal(r.created_at) },
              { key: "period", label: "Giai đoạn", render: period },
              { key: "trades", label: "Lệnh", align: "right" },
              { key: "total_r", label: "Tổng R", align: "right", render: (r) => <span className={(r.total_r ?? 0) > 0 ? "up" : "down"}>{signed(r.total_r)}</span> },
              { key: "config_hash", label: "Config" },
            ]} />
          </ScrollArea>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
