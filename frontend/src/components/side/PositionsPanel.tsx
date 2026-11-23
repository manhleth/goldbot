import { Alert, Card, Group, Stack, Text } from "@mantine/core";
import { usePositions } from "../../api/hooks";
import { fmt, isoLocal, signedMoney } from "../../lib/format";
import { SETUP_LABEL, label } from "../../lib/labels";
import { DirBadge, NewsBadge } from "../common/badges";

export function PositionsPanel() {
  const { data } = usePositions();
  if (!data) return <Text c="dimmed" size="sm">Đang tải…</Text>;
  return (
    <Stack gap="sm">
      {data.legs.length === 0 && <Text c="dimmed" size="sm">Không có lệnh đang mở.</Text>}
      {data.legs.map((leg) => {
        const b = leg.broker;
        return (
          <Card key={leg.ticket} padding="sm">
            <Group justify="space-between">
              <Text size="sm" fw={600}>{label(SETUP_LABEL, leg.setup)} · {leg.leg}</Text>
              <DirBadge dir={leg.direction > 0 ? "BUY" : "SELL"} />
            </Group>
            <Group justify="space-between" className="num">
              <Text size="xs" c="dimmed">#{leg.ticket} · {fmt(leg.volume)} lot</Text>
              <Text size="sm" fw={600} className={b && b.profit >= 0 ? "up" : "down"}>{b ? signedMoney(b.profit) : "—"}</Text>
            </Group>
            <Text size="xs" c="dimmed" className="num">Entry {fmt(leg.entry)} · SL {fmt(b?.sl ?? leg.sl)} · TP {fmt(b?.tp ?? leg.tp)}</Text>
            <Group gap={6} mt={4}><Text size="xs" c="dimmed">Mở {isoLocal(leg.opened_at)}</Text><NewsBadge value={leg.news} /></Group>
          </Card>
        );
      })}
      {data.unmanaged.length > 0 && (
        <Alert color="yellow" variant="light" title="Lệnh cùng magic nhưng không có trong journal">
          {data.unmanaged.map((u) => <Text key={u.ticket} size="xs">#{u.ticket} {u.buy ? "BUY" : "SELL"} {fmt(u.volume)} lot · {signedMoney(u.profit)}</Text>)}
        </Alert>
      )}
    </Stack>
  );
}
