import { Alert, Card, Group, List, Stack, Text } from "@mantine/core";
import { useAnalysis } from "../../api/hooks";
import { fmt, signed, timeLocal } from "../../lib/format";
import { SETUP_LABEL, label } from "../../lib/labels";
import { useUi } from "../../state/ui";
import { DirBadge } from "../common/badges";

export function AnalysisPanel() {
  const { tf } = useUi();
  const { data: a, error, isLoading } = useAnalysis(tf);
  if (isLoading) return <Text c="dimmed" size="sm">Đang phân tích…</Text>;
  if (error) return <Text c="dimmed" size="sm">{error.message}</Text>;
  if (!a?.ready) return <Text c="dimmed" size="sm">{a?.message ?? "Chưa có dữ liệu"}</Text>;
  const ov = a.overlays;
  return (
    <Stack gap="sm">
      <Card padding="sm">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Bias tổng hợp</Text>
        <Group gap="xs" mt={4}>
          <DirBadge dir={a.direction} size="lg" />
          <Text size="xs" c="dimmed">nến đóng {timeLocal(a.time)}</Text>
        </Group>
        {a.direction === "NEUTRAL" && <Text size="xs" c="dimmed" mt={4}>Các khung lớn không đồng thuận → không giao dịch.</Text>}
      </Card>

      {a.signals.length > 0 && (
        <Alert color="yellow" variant="light" title="Tín hiệu ở nến vừa đóng" p="sm">
          {a.signals.map((s) => (
            <Group key={s.key} gap={6}><DirBadge dir={s.direction} size="xs" /><Text size="xs">{label(SETUP_LABEL, s.setup)} · {s.trigger} @ {fmt(s.close)}</Text></Group>
          ))}
        </Alert>
      )}

      <Card padding="sm">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={6}>Bias từng khung</Text>
        {Object.entries(a.biases).map(([name, b]) => (
          <div key={name}>
            <Group justify="space-between"><Text fw={600} size="sm">{name}</Text><Group gap={6}><DirBadge dir={b.direction} /><Text size="xs" className="num">điểm {signed(b.score, 0)}</Text></Group></Group>
            <List size="xs" c="dimmed" mb={6} withPadding>{b.reasons.map((r) => <List.Item key={r}>{r}</List.Item>)}</List>
          </div>
        ))}
      </Card>

      <Card padding="sm">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={6}>Setup đang chờ trigger</Text>
        {a.setups.length === 0 ? (
          <Text size="xs" c="dimmed">Không có setup hợp lệ lúc này.</Text>
        ) : a.setups.map((s) => (
          <Card key={s.key} padding="xs" mb={6} withBorder>
            <Group justify="space-between"><Text size="sm" fw={600}>{label(SETUP_LABEL, s.name)}</Text><DirBadge dir={s.direction} /></Group>
            <Text size="xs" c="dimmed" className="num">Vùng {fmt(s.low)} – {fmt(s.high)} · invalidation {fmt(s.invalidation)} · điểm {s.score}</Text>
            <List size="xs" c="dimmed" withPadding>{s.reasons.map((r) => <List.Item key={r}>{r}</List.Item>)}</List>
          </Card>
        ))}
      </Card>

      {ov && (
        <Card padding="sm">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={6}>Cấu trúc khung {tf}</Text>
          {[["Vùng S/R", ov.sr_zones.length], ["FVG còn hiệu lực", ov.fvgs.length], ["Order block", ov.order_blocks.length], ["ATR(14)", fmt(ov.atr)]].map(([k, v]) => (
            <Group key={k} justify="space-between"><Text size="xs">{k}</Text><Text size="xs" fw={600} className="num">{v}</Text></Group>
          ))}
        </Card>
      )}
    </Stack>
  );
}
