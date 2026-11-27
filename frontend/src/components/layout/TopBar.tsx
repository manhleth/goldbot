import { Badge, Group, Switch, Text, Tooltip } from "@mantine/core";
import { actions, useAction, useStatus } from "../../api/hooks";
import { fmt, money, signedMoney, timeLocal } from "../../lib/format";

function Metric({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className={`metric-value num${tone ? ` ${tone}` : ""}`}>{value}</span>
    </div>
  );
}

/** Thanh trên cùng: giá + tài khoản kiểu MT5 (balance, equity, lãi thả nổi, margin), tin tức, kill switch. */
export function TopBar() {
  const { data: status } = useStatus();
  const kill = useAction(actions.killSwitch, {
    success: (r) => (r.kill_switch ? "Kill switch BẬT — mọi bot ngừng mở lệnh mới" : "Kill switch TẮT"),
    invalidate: [["status"]],
  });
  const acc = status?.mt5.account;
  const q = status?.mt5.quote;
  const floating = acc?.profit ?? 0;
  return (
    <header className="topbar">
      <Group gap={10} wrap="nowrap">
        <Text fw={700} size="sm">{status?.symbol ?? "XAUUSD"}</Text>
        <div className="ticker num">
          <span className="ticker-bid">{q ? fmt(q.bid) : "—"}</span>
          <span className="ticker-sep">/</span>
          <span className="ticker-ask">{q ? fmt(q.ask) : "—"}</span>
          <span className="ticker-spread">spread {q?.spread_points ?? "—"}</span>
        </div>
      </Group>
      <div className="topbar-fill" />
      {status?.news.blackout ? (
        <Badge variant="light" color="yellow" radius="sm">⚠ Blackout: {status.news.blackout}</Badge>
      ) : status?.news.next ? (
        <Tooltip label="Tin USD tác động mạnh sắp tới">
          <Badge variant="default" radius="sm" style={{ textTransform: "none" }}>
            Tin: {status.news.next.title} · {timeLocal(status.news.next.time)}
          </Badge>
        </Tooltip>
      ) : null}
      <Group gap={18} wrap="nowrap" className="account">
        <Metric label="Balance" value={acc ? money(acc.balance) : "—"} />
        <Metric label="Equity" value={acc ? money(acc.equity) : "—"} />
        <Metric label="Lãi thả nổi" value={acc ? signedMoney(floating) : "—"}
          tone={floating > 0 ? "up" : floating < 0 ? "down" : undefined} />
        <Metric label="Margin level" value={acc && acc.margin > 0 ? `${fmt(acc.margin_level, 0)}%` : "—"} />
      </Group>
      <Tooltip label={status?.mt5.error ?? (acc ? `${acc.server} · đòn bẩy 1:${acc.leverage} · ${acc.hedging ? "hedging" : "netting"}` : "")}
        disabled={!status}>
        <Badge variant="light" color={acc ? (acc.demo ? "teal" : "red") : "red"} radius="sm">
          {acc ? (acc.demo ? `DEMO #${acc.login}` : "TÀI KHOẢN THẬT — bot từ chối") : "MT5 offline"}
        </Badge>
      </Tooltip>
      <Tooltip label="Bật = mọi bot ngừng mở lệnh mới (lệnh đang mở vẫn được quản lý)">
        <Switch size="sm" color="red" label="Kill switch" checked={status?.kill_switch ?? false}
          onChange={(e) => kill.mutate(e.currentTarget.checked)} />
      </Tooltip>
    </header>
  );
}
