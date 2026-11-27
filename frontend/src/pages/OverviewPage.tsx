import { Stack, Text } from "@mantine/core";
import { useBots } from "../api/hooks";
import { BotCard } from "../components/bots/BotCard";
import { Panel } from "../components/layout/Panel";
import { Split } from "../components/layout/Split";
import { PositionsTable } from "../components/positions/PositionsTable";
import { SignalFeed } from "../components/signals/SignalFeed";
import { NewsPanel } from "../components/side/NewsPanel";

function Bots() {
  const { data, isLoading } = useBots();
  if (isLoading) return <Text c="dimmed" size="sm">Đang tải…</Text>;
  return <Stack gap="sm">{(data ?? []).map((bot) => <BotCard key={bot.name} bot={bot} />)}</Stack>;
}

/** Trang tổng quan kiểu 3Commas/MT5: bot, lệnh đang mở, hoạt động gần đây, tin tức. Mọi vùng kéo đổi kích thước được. */
export function OverviewPage() {
  return (
    <Split id="overview.cols" direction="row" initial={[34, 66]} min={300}>
      <Panel title="Bot">
        <Bots />
      </Panel>
      <Split id="overview.right" direction="column" initial={[50, 50]} min={140}>
        <Panel title="Lệnh đang mở">
          <PositionsTable />
        </Panel>
        <Split id="overview.bottom" direction="row" initial={[60, 40]} min={260}>
          <Panel title="Tín hiệu mới">
            <SignalFeed />
          </Panel>
          <Panel title="Tin kinh tế Mỹ">
            <NewsPanel />
          </Panel>
        </Split>
      </Split>
    </Split>
  );
}
