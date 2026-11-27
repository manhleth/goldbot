import { useEffect, useState } from "react";
import { ActionIcon, Badge, Button, Group, NumberInput, Popover, Progress, Stack, Text, Tooltip } from "@mantine/core";
import { IconAdjustments, IconPlayerPlay, IconPlayerStop } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { actions, useAction } from "../../api/hooks";
import type { BotSummary, RiskCaps } from "../../api/types";
import { RiskCapsInput } from "../common/RiskCapsInput";
import { isoLocal, signed, signedMoney } from "../../lib/format";
import { BOT_LABEL, REJECT_LABEL, kindLabel, label } from "../../lib/labels";
import { DirBadge } from "../common/badges";

const STALE_MINUTES = 20;

function Kpi({ label: name, value, tone, hint }: { label: string; value: string; tone?: number; hint?: string }) {
  const cls = tone === undefined || tone === 0 ? "" : tone > 0 ? " up" : " down";
  return (
    <Tooltip label={hint} disabled={!hint}>
      <div className="kpi">
        <span className="kpi-label">{name}</span>
        <span className={`kpi-value num${cls}`}>{value}</span>
      </div>
    </Tooltip>
  );
}

function statusOf(bot: BotSummary): { color: string; text: string } {
  if (!bot.running) return { color: "gray", text: "Đang dừng" };
  const age = bot.heartbeat ? (Date.now() - Date.parse(bot.heartbeat)) / 60000 : Infinity;
  return age > STALE_MINUTES ? { color: "yellow", text: "Không phản hồi" } : { color: "teal", text: "Đang chạy" };
}

/** Lớp học: loại mẫu hình được phép vào lệnh khi có ≥ 5 lệnh nháp và trung bình dương (xấp xỉ quy tắc 20 lệnh gần nhất). */
function Experience({ items }: { items: Record<string, [number, number]> }) {
  const rows = Object.entries(items).sort((a, b) => b[1][1] - a[1][1]);
  if (!rows.length) return <Text size="xs" c="dimmed">Chưa có kinh nghiệm (bot chưa chạy chu kỳ đầu)</Text>;
  return (
    <div className="exp-grid">
      {rows.map(([kind, [n, e]]) => {
        const on = n >= 5 && e > 0;
        return (
          <Tooltip key={kind} label={`${n} lệnh nháp · trung bình ${signed(e)}R · ${on ? "được vào lệnh" : "đang bị chặn"}`}>
            <div className={`exp-item${on ? " on" : ""}`}>
              <span>{kindLabel(kind)}</span>
              <span className={`num ${e > 0 ? "up" : "down"}`}>{signed(e)}R</span>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
}

const money = (v: number) => v.toLocaleString("vi-VN", { maximumFractionDigits: 0 });

const AUTOSAVE_MS = 1000;
type Num = number | "";

interface Draft { capital: Num; risk: Num; maxLot: Num; caps: RiskCaps }

const draftOf = (bot: BotSummary): Draft => ({
  capital: bot.capital_custom ? Math.round(bot.capital) : "",
  risk: bot.risk_custom && bot.risk_pct != null ? bot.risk_pct : "",
  maxLot: bot.max_lot ?? "",
  caps: bot.risk_caps ?? [],
});

/** Giá trị hợp lệ để lưu (ô trống = mặc định); sai → thông báo lỗi. */
function problemOf(d: Draft): string | null {
  if (d.capital !== "" && d.capital < 10) return "Vốn phải ≥ 10$";
  if (d.risk !== "" && !(d.risk > 0 && d.risk <= 50)) return "Rủi ro phải trong (0, 50]%";
  if (d.maxLot !== "" && !(d.maxLot > 0)) return "Lot tối đa phải > 0";
  if (d.caps.some(([v, p]) => !(v > 0 && p > 0 && p <= 50))) return "Mốc rủi ro: vốn > 0 và % trong (0, 50]";
  return null;
}

/** Chỉnh vốn, % rủi ro, lot tối đa, mốc chặn rủi ro của bot live — tự lưu sau khi ngừng gõ; bot dùng từ lệnh kế tiếp. */
function SettingsEditor({ bot }: { bot: BotSummary }) {
  const qc = useQueryClient();
  const [opened, setOpened] = useState(false);
  const [draft, setDraft] = useState<Draft>(() => draftOf(bot));
  const [dirty, setDirty] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: actions.saveBotSettings,
    onSuccess: async () => {
      setSavedAt(new Date().toLocaleTimeString("vi-VN"));
      await qc.invalidateQueries({ queryKey: ["bots"] });  // lấy lại số liệu server ngay sau khi lưu
    },
  });
  // Đồng bộ ô nhập theo số liệu server khi không có thay đổi chờ lưu (tránh mở lại thấy giá trị cũ / lưu đè giá trị cũ).
  const serverKey = JSON.stringify(draftOf(bot));
  useEffect(() => {
    if (!dirty && !save.isPending) setDraft(draftOf(bot));
  }, [serverKey]);  // eslint-disable-line react-hooks/exhaustive-deps
  const open = (next: boolean) => {
    if (next) setSavedAt(null);
    setOpened(next);
  };
  const edit = (patch: Partial<Draft>) => { setDraft((d) => ({ ...d, ...patch })); setDirty(true); };
  const problem = problemOf(draft);
  useEffect(() => {
    if (!dirty || problem) return;
    const id = setTimeout(() => {
      setDirty(false);
      save.mutate({ name: bot.name, capital: draft.capital === "" ? null : draft.capital,
        risk_pct: draft.risk === "" ? null : draft.risk, max_lot: draft.maxLot === "" ? null : draft.maxLot,
        risk_caps: draft.caps });  // [] = không chặn; "Về mặc định" mới gửi null
    }, AUTOSAVE_MS);
    return () => clearTimeout(id);
  }, [draft, dirty, problem]);  // eslint-disable-line react-hooks/exhaustive-deps
  const reset = () => save.mutate({ name: bot.name, capital: null, risk_pct: null, max_lot: null, risk_caps: null },
    { onSuccess: () => setOpened(false) });
  const status = problem ? { c: "red", t: `Chưa lưu: ${problem}` }
    : save.isError ? { c: "red", t: `Lỗi khi lưu: ${(save.error as Error)?.message ?? ""}` }
      : dirty || save.isPending ? { c: "yellow", t: "Đang lưu…" }
        : savedAt ? { c: "teal", t: `Đã lưu lúc ${savedAt}` } : { c: "dimmed", t: "Sửa xong tự lưu sau 1 giây" };
  const num = (v: string | number): Num => (v === "" ? "" : Number(v));
  return (
    <Popover opened={opened} onChange={open} position="bottom-end" shadow="md" withArrow>
      <Popover.Target>
        <Tooltip label="Chỉnh vốn và % rủi ro">
          <ActionIcon variant="default" size="md" onClick={() => open(!opened)} aria-label="Chỉnh vốn và rủi ro">
            <IconAdjustments size={16} />
          </ActionIcon>
        </Tooltip>
      </Popover.Target>
      <Popover.Dropdown>
        <Stack gap="xs" w={320}>
          <NumberInput size="xs" label="Vốn của bot ($)" placeholder={`Mặc định: ${money(bot.capital)}`} min={10} step={100}
            thousandSeparator="," description="Để trống = equity ban đầu × phần vốn + lãi/lỗ của bot"
            value={draft.capital} onChange={(v) => edit({ capital: num(v) })} />
          <NumberInput size="xs" label="Rủi ro mỗi lệnh (% vốn bot)" placeholder={`Mặc định: ${bot.risk_default ?? "—"}%`}
            min={0.1} max={50} step={0.5} decimalScale={2} description="Để trống = theo playbook.yaml"
            value={draft.risk} onChange={(v) => edit({ risk: num(v) })} />
          <NumberInput size="xs" label="Lot tối đa mỗi lệnh" placeholder="không giới hạn" min={0.01} step={1} decimalScale={2}
            value={draft.maxLot} onChange={(v) => edit({ maxLot: num(v) })} />
          <RiskCapsInput value={draft.caps} onChange={(caps) => edit({ caps })} />
          <Text size="xs" c="dimmed">Mốc tính theo vốn hiện tại của bot ({money(bot.capital)}$). Áp dụng từ lệnh mới tiếp
            theo, không cần khởi động lại bot; lệnh đang mở giữ nguyên.</Text>
          <Group gap="xs" justify="space-between" wrap="nowrap">
            <Text size="xs" c={status.c}>{status.t}</Text>
            <Button size="xs" variant="default" onClick={reset} loading={save.isPending}>Về mặc định</Button>
          </Group>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}

/** Mốc chặn rủi ro đang có hiệu lực (mốc vốn cao nhất đã đạt), nếu nó làm giảm % rủi ro. */
function activeCap(bot: BotSummary): [number, number] | null {
  const reached = (bot.risk_caps ?? []).filter(([v]) => bot.capital >= v).sort((a, b) => b[0] - a[0])[0];
  return reached && bot.risk_pct != null && reached[1] < bot.risk_pct ? reached : null;
}

function Fact({ label: name, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="fact">
      <span className="fact-label">{name}</span>
      <span className="fact-value num">{value}</span>
      {note && <span className="fact-note">{note}</span>}
    </div>
  );
}

/** Vốn, rủi ro đang áp dụng (và vì sao bị chặn), lot tối đa, giới hạn số lệnh — đủ chữ, không cắt. */
function RiskLine({ bot }: { bot: BotSummary }) {
  const cap = activeCap(bot);
  const pct = bot.risk_now ?? bot.risk_pct;
  return (
    <div className="fact-row">
      <Fact label="Vốn bot" value={`${money(bot.capital)}$`} note={bot.capital_custom ? "đặt tay" : "mặc định"} />
      {pct != null && (
        <Fact label="Rủi ro/lệnh" value={`${pct}% ≈ ${money(bot.capital * pct / 100)}$`}
          note={cap ? `đặt ${bot.risk_pct}%, chặn còn ${cap[1]}% vì vốn ≥ ${money(cap[0])}$` : bot.risk_custom ? "đặt tay" : "theo cấu hình"} />
      )}
      <Fact label="Lot tối đa" value={bot.max_lot ? `${bot.max_lot}` : "không giới hạn"} />
      <Fact label="Giới hạn lệnh" value={`${bot.max_positions ?? "—"} mở cùng lúc`}
        note={bot.max_per_day != null ? `${bot.max_per_day} lệnh/ngày` : undefined} />
    </div>
  );
}

export function BotCard({ bot }: { bot: BotSummary }) {
  const name = label(BOT_LABEL, bot.name);
  const start = useAction(actions.startNamedBot, { success: () => `Đã khởi động ${name}`, invalidate: [["bots"], ["status"]] });
  const stop = useAction(actions.stopNamedBot, { success: () => `Đã dừng ${name}`, invalidate: [["bots"], ["status"]] });
  const st = statusOf(bot);
  const winrate = bot.trades ? (bot.wins / bot.trades) * 100 : null;
  const sig = bot.last_signal;
  return (
    <div className="card bot-card">
      <Group justify="space-between" wrap="nowrap" align="flex-start">
        <div style={{ minWidth: 0 }}>
          <Group gap={8} wrap="nowrap">
            <span className={`dot dot-${st.color}`} />
            <Text fw={700}>{name}</Text>
            <Badge size="xs" variant="light" color={st.color}>{st.text}</Badge>
          </Group>
          <Text size="xs" c="dimmed">magic {bot.magic}</Text>
        </div>
        <Group gap={6} wrap="nowrap">
        <SettingsEditor bot={bot} />
        <Button size="xs" variant={bot.running ? "light" : "filled"} color={bot.running ? "red" : "blue"}
          loading={start.isPending || stop.isPending}
          leftSection={bot.running ? <IconPlayerStop size={14} /> : <IconPlayerPlay size={14} />}
          onClick={() => (bot.running ? stop.mutate(bot.name) : start.mutate(bot.name))}>
          {bot.running ? "Dừng" : "Chạy"}
        </Button>
        </Group>
      </Group>

      <RiskLine bot={bot} />

      <div className="kpi-grid">
        <Kpi label="Hôm nay" value={signedMoney(bot.pnl_today)} tone={bot.pnl_today} />
        <Kpi label="Tổng đã chốt" value={signedMoney(bot.pnl_total)} tone={bot.pnl_total} hint={`${signed(bot.r_total)}R`} />
        <Kpi label="Thả nổi" value={signedMoney(bot.floating)} tone={bot.floating} />
        <Kpi label="Lệnh mở" value={`${bot.open}${bot.max_positions ? ` / ${bot.max_positions}` : ""}`} />
        <Kpi label="Đã đóng" value={String(bot.trades)} />
        <Kpi label="Tỉ lệ thắng" value={winrate == null ? "—" : `${winrate.toFixed(0)}%`} />
      </div>
      {bot.max_positions ? (
        <Tooltip label="Số lệnh đang mở so với giới hạn">
          <Progress size={4} radius="xl" value={(bot.open / bot.max_positions) * 100} color={bot.open >= bot.max_positions ? "orange" : "blue"} />
        </Tooltip>
      ) : null}

      <Stack gap={4}>
        <Text size="xs" c="dimmed" fw={600}>TÍN HIỆU GẦN NHẤT</Text>
        {sig ? (
          <Group gap={6} wrap="nowrap">
            <DirBadge dir={sig.direction} size="xs" />
            <Text size="xs" truncate style={{ flex: 1 }}>{kindLabel(sig.setup_key)} · {isoLocal(sig.time)}</Text>
            <Badge size="xs" variant="light" color={sig.accepted ? "teal" : "gray"}>
              {sig.accepted ? "Vào lệnh" : label(REJECT_LABEL, sig.reject_reason ?? "")}
            </Badge>
          </Group>
        ) : <Text size="xs" c="dimmed">Chưa có tín hiệu</Text>}
      </Stack>

      <Stack gap={4}>
        <Text size="xs" c="dimmed" fw={600}>KINH NGHIỆM (TRADE NHÁP)</Text>
        <Experience items={bot.experience} />
      </Stack>
      <Text size="xs" c="dimmed">Nhịp gần nhất: {isoLocal(bot.heartbeat)}</Text>
    </div>
  );
}
