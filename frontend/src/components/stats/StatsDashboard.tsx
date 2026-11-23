import { useState, type ReactNode } from "react";
import { Alert, Card, Collapse, Group, SegmentedControl, SimpleGrid, Stack, Text, Button } from "@mantine/core";
import { IconAlertTriangle, IconCircleCheck, IconInfoCircle } from "@tabler/icons-react";
import { useReport } from "../../api/hooks";
import type { BreakdownRow, Report } from "../../api/types";
import { fmt, isNum, money, pct, pctValue, signed, signedMoney } from "../../lib/format";
import { REJECT_LABEL, SETUP_LABEL, NEWS_LABEL, label } from "../../lib/labels";
import { useUi } from "../../state/ui";
import { DataTable } from "../common/DataTable";
import { SourceSelect } from "../common/SourceSelect";
import { ChartCard, DrawdownChart, EquityChart, MonthlyChart, RHistogram } from "./charts";

function Kpi({ title, value, sub, trend }: { title: string; value: ReactNode; sub?: ReactNode; trend?: number | null }) {
  const arrow = isNum(trend) && trend !== 0 ? (trend > 0 ? <span className="up">▲ </span> : <span className="down">▼ </span>) : null;
  return (
    <Card padding="sm">
      <Text size="xs" c="dimmed">{title}</Text>
      <Text size="lg" fw={700} className="num">{arrow}{value}</Text>
      {sub && <Text size="xs" c="dimmed" className="num">{sub}</Text>}
    </Card>
  );
}

function Verdict({ report }: { report: Report }) {
  const n = report.summary?.trades ?? 0;
  const ok = n >= 100;
  return (
    <Alert variant="light" color={n < 30 ? "red" : ok ? "teal" : "yellow"} p="xs"
      icon={n < 30 ? <IconAlertTriangle size={16} /> : ok ? <IconCircleCheck size={16} /> : <IconInfoCircle size={16} />}>
      {report.verdict}
    </Alert>
  );
}

const DIMENSIONS: [string, string][] = [
  ["SETUP", "Setup"], ["CHIỀU", "Chiều"], ["PHIÊN", "Phiên"], ["BIAS", "Bias"],
  ["TIN TỨC (dự báo so với chiều lệnh)", "Tin tức"], ["GIAI ĐOẠN (quý) — kiểm tra độ ổn định", "Quý"],
];

function groupLabel(dimension: string, key: string) {
  if (dimension === "SETUP") return label(SETUP_LABEL, key);
  if (dimension.startsWith("TIN")) return label(NEWS_LABEL, key);
  return key;
}

function Breakdown({ report }: { report: Report }) {
  const available = DIMENSIONS.filter(([k]) => report.breakdowns[k]);
  const [dimension, setDimension] = useState(available[0]?.[0] ?? "SETUP");
  const rows = report.breakdowns[dimension] ?? [];
  return (
    <Card padding="sm">
      <Group justify="space-between" mb="xs">
        <Text size="sm" fw={600}>Phân tích theo nhóm</Text>
        <SegmentedControl size="xs" value={dimension} onChange={setDimension} data={available.map(([value, lbl]) => ({ value, label: lbl }))} />
      </Group>
      <DataTable<BreakdownRow> rows={rows} rowKey={(r) => r.key} columns={[
        { key: "key", label: "Nhóm", render: (r) => groupLabel(dimension, r.key) },
        { key: "trades", label: "Lệnh", align: "right" },
        { key: "winrate", label: "Thắng", align: "right", render: (r) => pct(r.winrate) },
        { key: "ci", label: "Khoảng tin cậy 95%", align: "right", render: (r) => `${pct(r.winrate_ci_low, 0)} – ${pct(r.winrate_ci_high, 0)}` },
        { key: "expectancy_r", label: "Expectancy", align: "right", render: (r) => <span className={r.expectancy_r > 0 ? "up" : "down"}>{signed(r.expectancy_r, 3)}R</span> },
        { key: "profit_factor", label: "PF", align: "right", render: (r) => fmt(r.profit_factor) },
        { key: "total_r", label: "Tổng R", align: "right", render: (r) => signed(r.total_r) },
        { key: "pnl", label: "Lãi/lỗ", align: "right", render: (r) => <span className={r.pnl > 0 ? "up" : "down"}>{signedMoney(r.pnl)}</span> },
        { key: "max_dd_r", label: "Max DD (R)", align: "right", render: (r) => fmt(r.max_dd_r) },
      ]} />
    </Card>
  );
}

function Rejections({ report }: { report: Report }) {
  const total = report.signals.total;
  const rows = Object.entries(report.signals.rejected).map(([reason, count]) => ({ reason, count }));
  return (
    <Card padding="sm">
      <Text size="sm" fw={600}>Tín hiệu bị bỏ qua — vì sao?</Text>
      <Text size="xs" c="dimmed" mb="xs">{total} tín hiệu · vào lệnh {report.signals.accepted} ({pct(total ? report.signals.accepted / total : 0)})</Text>
      <DataTable rows={rows} rowKey={(r) => r.reason} empty="Không có tín hiệu bị bỏ" columns={[
        { key: "reason", label: "Lý do", render: (r) => label(REJECT_LABEL, r.reason) },
        { key: "count", label: "Số lần", align: "right" },
        { key: "share", label: "Tỉ lệ", align: "right", render: (r) => pct(total ? r.count / total : 0) },
      ]} />
    </Card>
  );
}

export function StatsDashboard() {
  const { source } = useUi();
  const { data: report, error, isLoading } = useReport(source);
  const [showText, setShowText] = useState(false);

  return (
    <Stack gap="sm">
      <Group gap="sm">
        <Text size="sm" fw={600}>Nguồn</Text>
        <SourceSelect width={420} />
      </Group>
      {isLoading && <Text size="sm" c="dimmed">Đang tính thống kê…</Text>}
      {error && <Text size="sm" c="dimmed">{error.message}</Text>}
      {report && (
        <>
          <Verdict report={report} />
          {!report.summary || !report.money ? (
            <Text size="sm" c="dimmed">Chưa có lệnh nào ở nguồn này.</Text>
          ) : (
            <>
              <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="xs">
                <Kpi title="Lợi nhuận ròng" value={signedMoney(report.money.net_profit)} trend={report.money.net_profit}
                  sub={`${signed(report.money.return_pct, 1)}% vốn · ${signed(report.summary.total_r)}R`} />
                <Kpi title="Equity" value={money(report.money.final_equity)} sub={`Vốn ban đầu ${money(report.money.initial_equity)}`} />
                <Kpi title="Max drawdown" value={money(report.money.max_drawdown)}
                  sub={`${pctValue(report.money.max_drawdown_pct)} theo lệnh đóng${isNum(report.max_drawdown_floating_pct) ? ` · ${pctValue(report.max_drawdown_floating_pct)} gồm lệnh mở` : ""}`} />
                <Kpi title="Profit factor" value={fmt(report.money.profit_factor)}
                  sub={`Lãi gộp ${money(report.money.gross_profit)} · lỗ gộp ${money(report.money.gross_loss)}`} />
                <Kpi title="Số lệnh" value={report.summary.trades} sub={`Giữ lệnh TB ${fmt(report.money.avg_hold_hours, 1)} giờ`} />
                <Kpi title="Tỉ lệ thắng" value={pct(report.summary.winrate)}
                  sub={`95%: ${pct(report.summary.winrate_ci_low, 0)} – ${pct(report.summary.winrate_ci_high, 0)}`} />
                <Kpi title="Expectancy / lệnh" value={signedMoney(report.money.expectancy)} trend={report.money.expectancy}
                  sub={`${signed(report.summary.expectancy_r, 3)}R`} />
                <Kpi title="TB thắng / TB thua" value={`${money(report.money.avg_win)} / ${money(report.money.avg_loss)}`}
                  sub={`${fmt(report.summary.avg_win_r)}R / ${fmt(report.summary.avg_loss_r)}R`} />
                <Kpi title="Lệnh thắng lớn nhất" value={money(report.money.largest_win)} />
                <Kpi title="Lệnh thua lớn nhất" value={money(report.money.largest_loss)} />
                <Kpi title="Chuỗi thua dài nhất" value={`${report.summary.longest_losing_streak} lệnh`} sub={`Max DD ${fmt(report.summary.max_dd_r)}R`} />
                <Kpi title="Tổng R" value={signed(report.summary.total_r)} trend={report.summary.total_r} />
              </SimpleGrid>

              <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xs">
                <ChartCard title="Đường vốn (equity)" hint="Sau mỗi lệnh đóng, USD">
                  <EquityChart data={report.equity_curve} initial={report.money.initial_equity} />
                </ChartCard>
                <ChartCard title="Sụt giảm vốn (drawdown)" hint="% so với đỉnh vốn gần nhất">
                  <DrawdownChart data={report.equity_curve} />
                </ChartCard>
                <ChartCard title="Lãi/lỗ theo tháng" hint="USD, theo tháng đóng lệnh">
                  <MonthlyChart data={report.monthly} />
                </ChartCard>
                <ChartCard title="Phân bố kết quả (R)" hint="Số lệnh theo khoảng R-multiple">
                  <RHistogram data={report.r_histogram} />
                </ChartCard>
              </SimpleGrid>

              <Breakdown report={report} />
            </>
          )}
          <Rejections report={report} />
          <Card padding="sm">
            <Button size="xs" variant="subtle" onClick={() => setShowText((v) => !v)}>{showText ? "Ẩn" : "Xem"} báo cáo dạng chữ</Button>
            <Collapse in={showText}><pre className="pre" style={{ overflow: "auto", maxHeight: 400 }}>{report.text}</pre></Collapse>
          </Card>
        </>
      )}
    </Stack>
  );
}
