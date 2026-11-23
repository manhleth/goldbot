import { Alert, Button, Card, FileButton, Group, Stack, Text } from "@mantine/core";
import { IconRefresh, IconUpload } from "@tabler/icons-react";
import { actions, useAction, useNews } from "../../api/hooks";
import type { NewsEvent } from "../../api/types";
import { isoLocal, signed } from "../../lib/format";
import { RULE_LABEL, label } from "../../lib/labels";
import { DirBadge } from "../common/badges";

function groupByDay(events: NewsEvent[]): [string, NewsEvent[]][] {
  const days = new Map<string, NewsEvent[]>();
  for (const ev of events) {
    const day = new Date(ev.time * 1000).toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit" });
    days.set(day, [...(days.get(day) ?? []), ev]);
  }
  return [...days.entries()];
}

export function NewsPanel() {
  const { data } = useNews();
  const refresh = useAction(actions.refreshNews, { success: (r) => `Đã tải ${r.count} tin`, invalidate: [["news"], ["status"]] });
  const importCsv = useAction(actions.importNews, { success: (r) => `Đã nhập ${r.count} tin`, invalidate: [["news"]] });

  return (
    <Stack gap="sm">
      <Group gap="xs">
        <Button size="xs" leftSection={<IconRefresh size={14} />} loading={refresh.isPending} onClick={() => refresh.mutate(undefined)}>Cập nhật tin</Button>
        <FileButton accept=".csv" onChange={(f) => f && importCsv.mutate(f)}>
          {(props) => <Button {...props} size="xs" variant="default" leftSection={<IconUpload size={14} />} loading={importCsv.isPending}>Nhập CSV lịch sử</Button>}
        </FileButton>
      </Group>
      {data && (
        <>
          <Card padding="sm">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Kỳ vọng cho vàng ({data.lookahead_hours}h tới)</Text>
            <Group gap="xs" mt={4}><DirBadge dir={data.outlook.direction} size="lg" /><Text size="xs" c="dimmed" className="num">điểm {signed(data.outlook.score, 0)}</Text></Group>
            <Text size="xs" c="dimmed" mt={4}>Quy tắc: {label(RULE_LABEL, data.rule)}{data.enabled ? "" : " (bộ lọc tin đang TẮT)"}</Text>
            <Text size="xs" c="dimmed">Cập nhật: {isoLocal(data.last_refresh)}</Text>
          </Card>
          {data.blackout && <Alert color="yellow" variant="light" p="xs">Đang trong blackout: {data.blackout}</Alert>}
          {data.events.length === 0 && <Text size="xs" c="dimmed">Không có tin USD impact High trong khoảng này. Bấm "Cập nhật tin".</Text>}
          {groupByDay(data.events).map(([day, events]) => (
            <div key={day}>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>{day}</Text>
              {events.map((ev) => (
                <Group key={`${ev.time}-${ev.title}`} wrap="nowrap" align="flex-start" gap="xs" py={4}
                  style={{ borderBottom: "1px solid var(--mantine-color-dark-5)", opacity: ev.past ? 0.5 : 1 }}>
                  <Text size="xs" c="dimmed" w={40} className="num">
                    {new Date(ev.time * 1000).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false })}
                  </Text>
                  <div style={{ flex: 1 }}>
                    <Text size="xs">{ev.title}</Text>
                    <Text size="xs" c="dimmed" className="num">Dự báo {ev.forecast || "—"} · Trước {ev.previous || "—"}</Text>
                  </div>
                  {ev.gold !== "NEUTRAL" ? <Text size="xs" className={ev.gold === "BUY" ? "up" : "down"}>{ev.gold === "BUY" ? "▲ vàng" : "▼ vàng"}</Text> : <Text size="xs" c="dimmed">—</Text>}
                </Group>
              ))}
            </div>
          ))}
        </>
      )}
    </Stack>
  );
}
