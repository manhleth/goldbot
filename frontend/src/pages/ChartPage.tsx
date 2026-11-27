import { Tabs } from "@mantine/core";
import { ChartPanel } from "../components/chart/ChartPanel";
import { Split } from "../components/layout/Split";
import { PositionsTable } from "../components/positions/PositionsTable";
import { SignalFeed } from "../components/signals/SignalFeed";
import { NewsPanel } from "../components/side/NewsPanel";

/** Trang biểu đồ kiểu TradingView: biểu đồ lớn phía trên, khu lệnh/tín hiệu/tin phía dưới (kéo đổi kích thước). */
export function ChartPage() {
  return (
    <Split id="chart.rows" direction="column" initial={[68, 32]} min={140}>
      <section className="panel chart-host">
        <ChartPanel />
      </section>
      <section className="panel">
        <Tabs defaultValue="positions" className="tabs-fill">
          <Tabs.List>
            <Tabs.Tab value="positions">Lệnh đang mở</Tabs.Tab>
            <Tabs.Tab value="signals">Tín hiệu mới</Tabs.Tab>
            <Tabs.Tab value="news">Tin tức</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="positions"><PositionsTable /></Tabs.Panel>
          <Tabs.Panel value="signals"><SignalFeed /></Tabs.Panel>
          <Tabs.Panel value="news"><NewsPanel /></Tabs.Panel>
        </Tabs>
      </section>
    </Split>
  );
}
