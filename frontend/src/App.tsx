import { Tabs } from "@mantine/core";
import { Header } from "./components/Header";
import { ChartPanel } from "./components/chart/ChartPanel";
import { AnalysisPanel } from "./components/side/AnalysisPanel";
import { PositionsPanel } from "./components/side/PositionsPanel";
import { NewsPanel } from "./components/side/NewsPanel";
import { StatsDashboard } from "./components/stats/StatsDashboard";
import { TradesPanel } from "./components/bottom/TradesPanel";
import { SignalsPanel } from "./components/bottom/SignalsPanel";
import { BacktestPanel } from "./components/bottom/BacktestPanel";
import { ConfigPanel } from "./components/bottom/ConfigPanel";
import { LogsPanel } from "./components/bottom/LogsPanel";
import { useUi, type BottomTab } from "./state/ui";

export default function App() {
  const { chartVisible, bottomTab, setBottomTab } = useUi();
  return (
    <div className="app">
      <Header />
      <div className="app-body">
        <main className="app-main">
          {chartVisible && <section className="chart-panel"><ChartPanel /></section>}
          <section className={`bottom-panel${chartVisible ? "" : " full"}`}>
            <Tabs value={bottomTab} onChange={(v) => v && setBottomTab(v as BottomTab)} className="tabs-fill" keepMounted={false}>
              <Tabs.List>
                <Tabs.Tab value="stats">Thống kê</Tabs.Tab>
                <Tabs.Tab value="trades">Lịch sử lệnh</Tabs.Tab>
                <Tabs.Tab value="signals">Tín hiệu</Tabs.Tab>
                <Tabs.Tab value="backtest">Backtest</Tabs.Tab>
                <Tabs.Tab value="config">Cấu hình</Tabs.Tab>
                <Tabs.Tab value="logs">Log</Tabs.Tab>
              </Tabs.List>
              <Tabs.Panel value="stats"><StatsDashboard /></Tabs.Panel>
              <Tabs.Panel value="trades"><TradesPanel /></Tabs.Panel>
              <Tabs.Panel value="signals"><SignalsPanel /></Tabs.Panel>
              <Tabs.Panel value="backtest"><BacktestPanel /></Tabs.Panel>
              <Tabs.Panel value="config"><ConfigPanel /></Tabs.Panel>
              <Tabs.Panel value="logs"><LogsPanel /></Tabs.Panel>
            </Tabs>
          </section>
        </main>
        <aside className="app-side">
          <Tabs defaultValue="analysis" className="tabs-fill">
            <Tabs.List grow>
              <Tabs.Tab value="analysis">Phân tích</Tabs.Tab>
              <Tabs.Tab value="positions">Lệnh mở</Tabs.Tab>
              <Tabs.Tab value="news">Tin tức</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="analysis"><AnalysisPanel /></Tabs.Panel>
            <Tabs.Panel value="positions"><PositionsPanel /></Tabs.Panel>
            <Tabs.Panel value="news"><NewsPanel /></Tabs.Panel>
          </Tabs>
        </aside>
      </div>
    </div>
  );
}
