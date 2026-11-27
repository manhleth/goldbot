import { useState } from "react";
import { Alert, Text } from "@mantine/core";
import { usePositions } from "../../api/hooks";
import type { Leg } from "../../api/types";
import { fmt, isoLocal, signedMoney } from "../../lib/format";
import { BOT_LABEL, kindLabel, label } from "../../lib/labels";
import { DataTable } from "../common/DataTable";
import { DirBadge } from "../common/badges";
import { TradeDrawer, levelBoxes, reasonsOf, contextOf, reviewRef, type TradeDetail } from "../trades/TradeDrawer";

const modeOf = (bot: string) => (bot === "live" ? "live" : `bot:${bot}`);

function detailOf(leg: Leg): TradeDetail {
  const b = leg.broker;
  return {
    title: `${label(BOT_LABEL, leg.bot)} · ${kindLabel(leg.setup_key)} · #${leg.ticket}`,
    chartUrl: leg.chart ? `/api/leg-charts/${encodeURIComponent(modeOf(leg.bot))}/${leg.ticket}` : null,
    liveChartUrl: `/api/leg-charts/${encodeURIComponent(modeOf(leg.bot))}/${leg.ticket}/now`,
    reasons: reasonsOf(leg.reasons),
    context: contextOf(leg.meta),
    levels: levelBoxes(leg.levels, true),
    review: reviewRef({ kind: "leg", mode: modeOf(leg.bot), key: leg.ticket }, null, leg.setup_key),
    rows: [
      ["Chiều", <DirBadge dir={leg.direction > 0 ? "BUY" : "SELL"} size="xs" />],
      ["Mở lúc", isoLocal(leg.opened_at)],
      ["Khối lượng", `${fmt(leg.volume)} lot`],
      ["Giá vào", fmt(b?.price_open ?? leg.entry)],
      ["Giá hiện tại", fmt(b?.price_current)],
      ["Lãi/lỗ thả nổi", signedMoney(b ? b.profit + (b.swap ?? 0) : null)],
      ["Đóng trong ngày lúc", leg.exit_at ? isoLocal(leg.exit_at) : "Không (swing, gồng theo đỉnh/đáy)"],
    ],
  };
}

/** Lệnh đang mở của mọi bot, kiểu tab "Giao dịch" của MT5: lãi/lỗ thả nổi theo thời gian thực. */
export function PositionsTable() {
  const { data } = usePositions();
  const [detail, setDetail] = useState<TradeDetail | null>(null);
  if (!data) return <Text c="dimmed" size="sm">Đang tải…</Text>;
  const total = data.legs.reduce((sum, l) => sum + (l.broker ? l.broker.profit + (l.broker.swap ?? 0) : 0), 0);
  return (
    <>
      <DataTable<Leg> rows={data.legs} rowKey={(r) => r.ticket} empty="Không có lệnh đang mở"
        onRowClick={(leg) => setDetail(detailOf(leg))} columns={[
          { key: "bot", label: "Bot", render: (r) => label(BOT_LABEL, r.bot) },
          { key: "setup", label: "Mẫu hình", render: (r) => kindLabel(r.setup_key) },
          { key: "ticket", label: "Ticket" },
          { key: "opened_at", label: "Mở lúc", render: (r) => isoLocal(r.opened_at) },
          { key: "direction", label: "Loại", render: (r) => <DirBadge dir={r.direction > 0 ? "BUY" : "SELL"} size="xs" /> },
          { key: "volume", label: "Lot", align: "right", render: (r) => fmt(r.volume) },
          { key: "entry", label: "Giá vào", align: "right", render: (r) => fmt(r.broker?.price_open ?? r.entry) },
          { key: "sl", label: "SL", align: "right", render: (r) => fmt(r.broker?.sl ?? r.sl) },
          { key: "cur", label: "Giá hiện tại", align: "right", render: (r) => fmt(r.broker?.price_current) },
          { key: "swap", label: "Swap", align: "right", render: (r) => fmt(r.broker?.swap) },
          { key: "profit", label: "Lãi/lỗ", align: "right", render: (r) => {
            const p = r.broker ? r.broker.profit + (r.broker.swap ?? 0) : null;
            return <b className={p == null ? "" : p >= 0 ? "up" : "down"}>{signedMoney(p)}</b>;
          } },
        ]} />
      {data.legs.length > 0 && (
        <div className="table-total num">
          Tổng thả nổi: <b className={total >= 0 ? "up" : "down"}>{signedMoney(total)}</b>
        </div>
      )}
      {data.unmanaged.length > 0 && (
        <Alert color="yellow" variant="light" mt="sm" title="Lệnh của bot trên MT5 nhưng không có trong journal">
          {data.unmanaged.map((u) => (
            <Text key={u.ticket} size="xs">{label(BOT_LABEL, u.bot)} · #{u.ticket} {u.buy ? "BUY" : "SELL"} {fmt(u.volume)} lot · {signedMoney(u.profit)}</Text>
          ))}
        </Alert>
      )}
      <TradeDrawer detail={detail} onClose={() => setDetail(null)} />
    </>
  );
}
