import { Badge } from "@mantine/core";
import type { SignalRow } from "../../api/types";
import { fmt, isoLocal } from "../../lib/format";
import { BOT_LABEL, REJECT_LABEL, SETUP_LABEL, kindLabel, label } from "../../lib/labels";
import { DirBadge } from "../common/badges";
import { reasonsOf, contextOf, reviewRef, type TradeDetail } from "../trades/TradeDrawer";

const nameOf = (s: SignalRow) => (s.setup_key?.includes("@") ? kindLabel(s.setup_key) : label(SETUP_LABEL, s.setup));

/** Chi tiết một tín hiệu: lý do vào lệnh, kết quả (vào lệnh / bị bỏ vì sao), chart lý do. */
export function signalDetail(s: SignalRow, mode: string, bot?: string): TradeDetail {
  const rows: TradeDetail["rows"] = [
    ["Kết quả", <Badge size="sm" variant="light" color={s.accepted ? "teal" : "gray"}>
      {s.accepted ? "Đã vào lệnh" : `Bị bỏ: ${label(REJECT_LABEL, s.reject_reason ?? "")}`}</Badge>],
    ["Thời gian", isoLocal(s.time)],
    ["Chiều", <DirBadge dir={s.direction} size="xs" />],
  ];
  if (bot) rows.unshift(["Bot", label(BOT_LABEL, bot)]);
  if (s.entry != null) rows.push(["Giá đặt", fmt(s.entry)]);
  if (s.sl != null) rows.push(["SL", fmt(s.sl)]);
  if (s.tp1 != null) rows.push(["TP", fmt(s.tp1)]);
  return {
    title: `Tín hiệu · ${nameOf(s)} · ${s.direction}`,
    chartUrl: `/api/signal-charts/${encodeURIComponent(mode)}/${s.id}`,
    reasons: reasonsOf(s.reasons),
    context: contextOf(s.meta),
    review: reviewRef({ kind: "signal", mode, key: s.id }, s.run_id, s.setup_key),
    rows,
  };
}
