import type { ReactNode } from "react";
import { ConfigPanel } from "./components/bottom/ConfigPanel";
import { LogsPanel } from "./components/bottom/LogsPanel";
import { SignalsPanel } from "./components/bottom/SignalsPanel";
import { NavRail } from "./components/layout/NavRail";
import { Panel } from "./components/layout/Panel";
import { TopBar } from "./components/layout/TopBar";
import { TradesTable } from "./components/trades/TradesTable";
import { ChartPage } from "./pages/ChartPage";
import { OverviewPage } from "./pages/OverviewPage";
import { StatsPage } from "./pages/StatsPage";
import { useUi, type Page } from "./state/ui";

const PAGES: Record<Page, () => ReactNode> = {
  overview: () => <OverviewPage />,
  chart: () => <ChartPage />,
  trades: () => <Panel title="Lịch sử lệnh"><TradesTable /></Panel>,
  signals: () => <Panel title="Tín hiệu"><SignalsPanel /></Panel>,
  stats: () => <StatsPage />,
  backtest: () => <StatsPage />,  // trang cũ (giá trị đã lưu trong trình duyệt) → gộp vào Thống kê
  config: () => <Panel title="Cấu hình"><ConfigPanel /></Panel>,
  logs: () => <Panel title="Nhật ký"><LogsPanel /></Panel>,
};

/** Khung app kiểu nền tảng giao dịch desktop: menu icon trái, thanh tài khoản trên, trang nội dung chia vùng kéo được. */
export default function App() {
  const { page } = useUi();
  return (
    <div className="shell">
      <NavRail />
      <div className="shell-main">
        <TopBar />
        <main className="page">{PAGES[page]()}</main>
      </div>
    </div>
  );
}
