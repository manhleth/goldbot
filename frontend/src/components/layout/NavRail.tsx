import { Stack, Tooltip, UnstyledButton } from "@mantine/core";
import {
  IconBolt, IconChartBar, IconChartCandle, IconLayoutDashboard, IconListDetails, IconSettings, IconTerminal2,
  type Icon,
} from "@tabler/icons-react";
import { useUi, type Page } from "../../state/ui";

const ITEMS: { page: Page; label: string; icon: Icon }[] = [
  { page: "overview", label: "Tổng quan", icon: IconLayoutDashboard },
  { page: "chart", label: "Biểu đồ", icon: IconChartCandle },
  { page: "trades", label: "Lệnh", icon: IconListDetails },
  { page: "signals", label: "Tín hiệu", icon: IconBolt },
  { page: "stats", label: "Thống kê & backtest", icon: IconChartBar },
];
const BOTTOM: { page: Page; label: string; icon: Icon }[] = [
  { page: "logs", label: "Log", icon: IconTerminal2 },
  { page: "config", label: "Cấu hình", icon: IconSettings },
];

function Item({ page, label, icon: Ico }: { page: Page; label: string; icon: Icon }) {
  const { page: current, setPage } = useUi();
  const active = current === page;
  return (
    <Tooltip label={label} position="right" withArrow openDelay={250}>
      <UnstyledButton className={`rail-item${active ? " active" : ""}`} onClick={() => setPage(page)} aria-label={label}
        aria-current={active ? "page" : undefined}>
        <Ico size={20} stroke={1.6} />
        <span>{label}</span>
      </UnstyledButton>
    </Tooltip>
  );
}

/** Menu icon dọc bên trái (kiểu TradingView/Binance desktop). */
export function NavRail() {
  return (
    <nav className="rail">
      <div className="rail-logo" aria-hidden>G</div>
      <Stack gap={2} align="stretch">{ITEMS.map((it) => <Item key={it.page} {...it} />)}</Stack>
      <div style={{ flex: 1 }} />
      <Stack gap={2} align="stretch">{BOTTOM.map((it) => <Item key={it.page} {...it} />)}</Stack>
    </nav>
  );
}
