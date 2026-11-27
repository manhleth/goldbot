import { useState } from "react";
import { Badge, Group, Stack, Text, Tooltip, UnstyledButton } from "@mantine/core";
import { useBotSignals, useBots } from "../../api/hooks";
import { isoLocal } from "../../lib/format";
import { BOT_LABEL, REJECT_LABEL, kindLabel, label } from "../../lib/labels";
import { DirBadge } from "../common/badges";
import { TradeDrawer, type TradeDetail } from "../trades/TradeDrawer";
import { signalDetail } from "./signalDetail";

/** Dòng hoạt động gần đây của mọi bot: tín hiệu nào vào lệnh, bị bỏ vì sao; bấm để xem lý do vào lệnh + chart. */
export function SignalFeed({ limit = 40 }: { limit?: number }) {
  const bots = useBots();
  const rows = useBotSignals((bots.data ?? []).map((b) => b.name), limit);
  const [detail, setDetail] = useState<TradeDetail | null>(null);
  if (!rows.length) return <Text c="dimmed" size="sm">Chưa có tín hiệu. Bot ONE quét mẫu hình mỗi khi nến M15 đóng.</Text>;
  return (
    <>
      <Stack gap={2}>
        {rows.slice(0, limit).map((s) => (
          <UnstyledButton key={`${s.bot}-${s.id}`} className="feed-row" onClick={() => setDetail(signalDetail(s, `bot:${s.bot}`, s.bot))}>
            <Group gap={8} wrap="nowrap">
              <span className={`dot dot-${s.accepted ? "teal" : "gray"}`} />
              <Text size="xs" c="dimmed" w={118} className="num">{isoLocal(s.time)}</Text>
              <DirBadge dir={s.direction} size="xs" />
              <Text size="xs" fw={500} truncate style={{ flex: 1 }}>{kindLabel(s.setup_key ?? s.setup)}</Text>
              <Text size="xs" c="dimmed">{label(BOT_LABEL, s.bot)}</Text>
              <Tooltip label={s.accepted ? "Đã vào lệnh" : label(REJECT_LABEL, s.reject_reason ?? "")}>
                <Badge size="xs" variant="light" color={s.accepted ? "teal" : "gray"} maw={190}>
                  {s.accepted ? "Vào lệnh" : label(REJECT_LABEL, s.reject_reason ?? "")}
                </Badge>
              </Tooltip>
            </Group>
          </UnstyledButton>
        ))}
      </Stack>
      <TradeDrawer detail={detail} onClose={() => setDetail(null)} />
    </>
  );
}
