import { BacktestPanel } from "../components/bottom/BacktestPanel";
import { Panel } from "../components/layout/Panel";
import { Split } from "../components/layout/Split";
import { StatsDashboard } from "../components/stats/StatsDashboard";

/** Thống kê + chạy backtest trên cùng một trang: chạy xong thống kê chuyển ngay sang lần chạy mới. */
export function StatsPage() {
  return (
    <Split id="stats.rows" direction="column" initial={[62, 38]} min={160}>
      <Panel title="Thống kê"><StatsDashboard /></Panel>
      <Panel title="Backtest"><BacktestPanel /></Panel>
    </Split>
  );
}
