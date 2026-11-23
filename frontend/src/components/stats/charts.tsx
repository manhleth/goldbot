import type { ReactNode } from "react";
import { Card, Text } from "@mantine/core";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
  type TooltipProps,
} from "recharts";
import type { Report } from "../../api/types";
import { dateShort, money, pctValue, signedMoney } from "../../lib/format";
import { CHART } from "../../theme";

const AXIS = { stroke: CHART.grid, tick: { fill: CHART.axis, fontSize: 11 }, tickLine: false } as const;
const compactMoney = (v: number) => (Math.abs(v) >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`);

export function ChartCard({ title, hint, children, height = 220 }: { title: string; hint?: string; children: ReactNode; height?: number }) {
  return (
    <Card padding="sm">
      <Text size="sm" fw={600}>{title}</Text>
      {hint && <Text size="xs" c="dimmed">{hint}</Text>}
      <div style={{ height, marginTop: 8 }}>{children}</div>
    </Card>
  );
}

function TooltipBox({ lines }: { lines: [string, string][] }) {
  return (
    <div style={{ background: "#20232b", border: "1px solid #363b47", borderRadius: 6, padding: "6px 10px", fontSize: 12 }}>
      {lines.map(([k, v]) => (
        <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
          <span style={{ color: CHART.axis }}>{k}</span><span className="num" style={{ color: "#c9ccd3" }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

type Tip = TooltipProps<number, string>;

export function EquityChart({ data, initial }: { data: Report["equity_curve"]; initial: number }) {
  const points = [{ time: data.length ? data[0].time - 1 : 0, equity: initial }, ...data];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART.positive} stopOpacity={0.25} />
            <stop offset="100%" stopColor={CHART.positive} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} scale="time" tickFormatter={dateShort} minTickGap={40} {...AXIS} />
        <YAxis tickFormatter={compactMoney} width={56} domain={["auto", "auto"]} {...AXIS} />
        <ReferenceLine y={initial} stroke={CHART.axis} strokeDasharray="4 4" label={{ value: "Vốn ban đầu", fill: CHART.axis, fontSize: 10, position: "insideTopLeft" }} />
        <Tooltip cursor={{ stroke: CHART.axis }} content={({ active, payload }: Tip) =>
          active && payload?.length ? <TooltipBox lines={[["Ngày", dateShort(payload[0].payload.time)], ["Equity", money(payload[0].payload.equity)]]} /> : null} />
        <Area type="monotone" dataKey="equity" stroke={CHART.positive} strokeWidth={2} fill="url(#eqFill)" isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function DrawdownChart({ data }: { data: Report["equity_curve"] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} scale="time" tickFormatter={dateShort} minTickGap={40} {...AXIS} />
        <YAxis tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={44} domain={["dataMin", 0]} {...AXIS} />
        <Tooltip cursor={{ stroke: CHART.axis }} content={({ active, payload }: Tip) =>
          active && payload?.length ? <TooltipBox lines={[["Ngày", dateShort(payload[0].payload.time)], ["Drawdown", pctValue(payload[0].payload.drawdown_pct)]]} /> : null} />
        <Area type="stepAfter" dataKey="drawdown_pct" stroke={CHART.negative} strokeWidth={2} fill={CHART.negative} fillOpacity={0.15} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function MonthlyChart({ data }: { data: Report["monthly"] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="month" minTickGap={16} {...AXIS} />
        <YAxis tickFormatter={compactMoney} width={56} {...AXIS} />
        <ReferenceLine y={0} stroke={CHART.axis} />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={({ active, payload }: Tip) => {
          if (!active || !payload?.length) return null;
          const m = payload[0].payload as Report["monthly"][number];
          return <TooltipBox lines={[["Tháng", m.month], ["Lãi/lỗ", signedMoney(m.pnl)], ["R", `${m.r > 0 ? "+" : ""}${m.r.toFixed(2)}`], ["Số lệnh", String(m.trades)], ["Thắng", `${(m.winrate * 100).toFixed(0)}%`]]} />;
        }} />
        <Bar dataKey="pnl" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {data.map((m) => <Cell key={m.month} fill={m.pnl >= 0 ? CHART.positive : CHART.negative} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RHistogram({ data }: { data: Report["r_histogram"] }) {
  const rows = data.map((b) => ({ ...b, label: b.from.toFixed(1) }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis allowDecimals={false} width={32} {...AXIS} />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={({ active, payload }: Tip) => {
          if (!active || !payload?.length) return null;
          const b = payload[0].payload as Report["r_histogram"][number];
          return <TooltipBox lines={[["Khoảng R", `${b.from.toFixed(1)} → ${b.to.toFixed(1)}`], ["Số lệnh", String(b.count)]]} />;
        }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {rows.map((b) => <Cell key={b.label} fill={b.to <= 0 ? CHART.negative : CHART.positive} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
