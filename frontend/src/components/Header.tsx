import { useEffect } from "react";
import { Badge, Button, Group, SegmentedControl, Switch, Text, Tooltip } from "@mantine/core";
import { IconChartCandle, IconPlayerPlay, IconPlayerStop } from "@tabler/icons-react";
import { actions, useAction, useStatus } from "../api/hooks";
import type { BotStatus } from "../api/types";
import { isoLocal, money, timeLocal } from "../lib/format";
import { BOT_LABEL, label } from "../lib/labels";
import { useUi } from "../state/ui";

function BotButton({ bot }: { bot: BotStatus }) {
  const name = label(BOT_LABEL, bot.name);
  const start = useAction(actions.startNamedBot, { success: () => `Đã khởi động ${name} (tab Log)`, invalidate: [["status"]] });
  const stop = useAction(actions.stopNamedBot, { success: () => `Đã dừng ${name}`, invalidate: [["status"]] });
  const tip = bot.heartbeat ? `Nhịp gần nhất: ${isoLocal(bot.heartbeat)} · ${bot.open} lệnh mở` : "Chưa chạy";
  return (
    <Tooltip label={tip}>
      <Button size="xs" color={bot.running ? "red" : "blue"} variant={bot.running ? "filled" : "light"}
        loading={start.isPending || stop.isPending}
        leftSection={bot.running ? <IconPlayerStop size={14} /> : <IconPlayerPlay size={14} />}
        onClick={() => (bot.running ? stop.mutate(bot.name) : start.mutate(bot.name))}>
        {name}{bot.open ? ` · ${bot.open}` : ""}
      </Button>
    </Tooltip>
  );
}

export function Header() {
  const { data: status } = useStatus();
  const { tf, setTf, chartVisible, setChartVisible } = useUi();
  const kill = useAction(actions.killSwitch, {
    success: (r) => (r.kill_switch ? "Kill switch BẬT — bot ngừng mở lệnh mới" : "Kill switch TẮT"),
    invalidate: [["status"]],
  });

  const tfs = status ? [...new Set([status.timeframes.trigger, status.timeframes.setup, ...[...status.timeframes.bias].reverse()])] : [];
  useEffect(() => {
    if (status && (!tf || !tfs.includes(tf))) setTf(status.timeframes.setup);
  }, [status, tf, tfs, setTf]);

  const acc = status?.mt5.account;
  const quote = status?.mt5.quote;

  return (
    <Group h={48} px="md" gap="sm" wrap="nowrap" style={{ borderBottom: "1px solid var(--mantine-color-dark-5)", background: "var(--mantine-color-dark-7)" }}>
      <Text fw={700} c="yellow.5">GoldBot</Text>
      <Text fw={600}>{status?.symbol ?? "—"}</Text>
      {chartVisible && tfs.length > 0 && (
        <SegmentedControl size="xs" data={tfs} value={tf ?? undefined} onChange={setTf} />
      )}
      {quote && <Text size="xs" c="dimmed" className="num">Bid {quote.bid} · Ask {quote.ask} · Spread {quote.spread_points}</Text>}
      <div style={{ flex: 1 }} />
      <Tooltip label={status?.mt5.error ?? (acc ? `${acc.server} · ${acc.hedging ? "hedging" : "netting"}` : "")} disabled={!status}>
        <Badge variant="light" color={acc ? (acc.demo ? "teal" : "red") : "red"} radius="sm">
          {acc ? (acc.demo ? `MT5 DEMO #${acc.login}` : "TÀI KHOẢN THẬT — bot từ chối chạy") : "MT5 offline"}
        </Badge>
      </Tooltip>
      {status?.news.blackout ? (
        <Badge variant="light" color="yellow" radius="sm">⚠ Blackout: {status.news.blackout}</Badge>
      ) : status?.news.next ? (
        <Badge variant="light" color="gray" radius="sm" style={{ textTransform: "none" }}>
          Tin tới: {status.news.next.title} · {timeLocal(status.news.next.time)}
        </Badge>
      ) : null}
      <Badge variant="light" color="gray" radius="sm" className="num">Equity {acc ? money(acc.equity) : "—"}</Badge>
      <Switch size="sm" label="Biểu đồ" checked={chartVisible} onChange={(e) => setChartVisible(e.currentTarget.checked)}
        thumbIcon={<IconChartCandle size={10} />} />
      <Switch size="sm" color="red" label="Kill switch" checked={status?.kill_switch ?? false}
        onChange={(e) => kill.mutate(e.currentTarget.checked)} />
      {(status?.bots ?? []).map((bot) => <BotButton key={bot.name} bot={bot} />)}
    </Group>
  );
}
