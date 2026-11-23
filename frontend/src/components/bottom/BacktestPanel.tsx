import { useEffect, useRef, useState } from "react";
import { Badge, Button, Card, Checkbox, Group, ScrollArea, SimpleGrid, Stack, Text, TextInput } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { IconPlayerPlay, IconPlayerStop } from "@tabler/icons-react";
import { actions, useAction, useBacktestStatus, useRuns } from "../../api/hooks";
import type { Run } from "../../api/types";
import { isoLocal, signed } from "../../lib/format";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";

const isoDate = (d: Date) => d.toISOString().slice(0, 10);

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
  const status = useBacktestStatus();
  const runs = useRuns();
  const { setSource, setBottomTab } = useUi();
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
        notifications.show({ color: "teal", message: "Backtest xong — đang mở thống kê" });
        setSource(status.data.run_id);
        setBottomTab("stats");
      }
    }
  }, [running, status.data, qc, setSource, setBottomTab]);

  const openRun = (r: Run) => { setSource(r.run_id); setBottomTab("stats"); };
  const stateBadge = running ? <Badge color="blue">Đang chạy</Badge>
    : status.data?.exit_code === 0 ? <Badge color="teal">Hoàn tất</Badge>
      : status.data?.exit_code ? <Badge color="red">Lỗi (mã {status.data.exit_code})</Badge> : null;

  return (
    <Stack gap="sm">
      <Group gap="sm" align="flex-end">
        <TextInput size="xs" type="date" label="Từ ngày" value={start} onChange={(e) => setStart(e.currentTarget.value)} />
        <TextInput size="xs" type="date" label="Đến ngày" value={end} onChange={(e) => setEnd(e.currentTarget.value)} />
        <Checkbox size="xs" label="Tải lại dữ liệu MT5" checked={refresh} onChange={(e) => setRefresh(e.currentTarget.checked)} mb={6} />
        <Button size="xs" leftSection={<IconPlayerPlay size={14} />} disabled={running} loading={run.isPending}
          onClick={() => run.mutate({ start, end, refresh })}>Chạy backtest</Button>
        <Button size="xs" variant="default" leftSection={<IconPlayerStop size={14} />} disabled={!running} onClick={() => stop.mutate(undefined)}>Dừng</Button>
        {stateBadge}
      </Group>
      <Text size="xs" c="dimmed">Vốn ban đầu, số tiền rủi ro mỗi lệnh và mọi quy tắc lấy từ tab Cấu hình (mục backtest / risk). Mỗi lần chạy lưu kèm phiên bản config.</Text>
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
