import os, requests, time
from dotenv import load_dotenv

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send(text: str):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10
    )
    if not r.ok:
        print(f"Telegram loi: {r.text}")

def send_analysis(a: dict):
    b  = a["bias"]
    kl = a["key_levels"]
    sc = a["scenarios"]

    dir_e  = {"BULLISH":"📈","BEARISH":"📉","RANGING":"↔️"}.get(b["direction"],"❓")
    conf_e = {"HIGH":"🔴 CAO","MEDIUM":"🟡 TRUNG BINH","LOW":"🟢 THAP"}.get(b["confidence"],"⚪")
    lb_e   = {"BUY":"🟢 MUA","SELL":"🔴 BAN","NEUTRAL":"⚪ TRUNG TINH"}.get(b["london_bias"],"❓")
    ny_e   = {"BUY":"🟢 MUA","SELL":"🔴 BAN","NEUTRAL":"⚪ TRUNG TINH"}.get(b["ny_bias"],"❓")

    # Tin 1: Bias
    reasons = "".join(f"  • {r}\n" for r in b["reasons"])
    send(
        f"<b>══ XAU/USD {a['date']} ══</b>\n\n"
        f"{dir_e} <b>BIAS: {b['direction']}</b>  |  {conf_e}\n\n"
        f"{b['summary']}\n\n"
        f"<b>Ly do:</b>\n{reasons}\n"
        f"London: {lb_e}  |  NY: {ny_e}\n"
        f"Invalidate: <b>{b['invalidation']}</b>\n\n"
        f"<b>Key Levels:</b>\n"
        f"  R manh: {kl['major_resistance']}\n"
        f"  S manh: {kl['major_support']}\n"
        f"  EQ: {kl['equilibrium']}\n"
        f"  W.High: {kl['weekly_high']}  |  W.Low: {kl['weekly_low']}"
    )
    time.sleep(0.5)

    # Tin 2: Buy zones
    if a.get("buy_zones"):
        t = "🟢 <b>VUNG MUA TIEM NANG</b>\n\n"
        for z in a["buy_zones"][:3]:
            t += (f"<b>#{z['rank']} {z['type']}</b>\n"
                  f"Vung: {z['zone_low']} — {z['zone_high']}\n"
                  f"Vi sao: {z['why']}\n"
                  f"▶ Trigger: {z['trigger']}\n"
                  f"Entry: {z['entry']}  SL: {z['sl']}\n"
                  f"TP1: {z['tp1']}  TP2: {z['tp2']}\n"
                  f"RR: 1:{z['rr']:.1f}  |  {z.get('timeframe_confirmation','H1')}\n\n")
        send(t)
        time.sleep(0.5)

    # Tin 3: Sell zones
    if a.get("sell_zones"):
        t = "🔴 <b>VUNG BAN TIEM NANG</b>\n\n"
        for z in a["sell_zones"][:3]:
            t += (f"<b>#{z['rank']} {z['type']}</b>\n"
                  f"Vung: {z['zone_low']} — {z['zone_high']}\n"
                  f"Vi sao: {z['why']}\n"
                  f"▶ Trigger: {z['trigger']}\n"
                  f"Entry: {z['entry']}  SL: {z['sl']}\n"
                  f"TP1: {z['tp1']}  TP2: {z['tp2']}\n"
                  f"RR: 1:{z['rr']:.1f}  |  {z.get('timeframe_confirmation','H1')}\n\n")
        send(t)
        time.sleep(0.5)

    # Tin 4: Kịch bản
    t = (f"🎯 <b>KICH BAN</b>\n\n"
         f"<b>A [{sc['A']['probability']}]:</b>\n{sc['A']['description']}\n▶ {sc['A']['play']}\n\n"
         f"<b>B [{sc['B']['probability']}]:</b>\n{sc['B']['description']}\n▶ {sc['B']['play']}")
    if any(a.get("warnings",[])):
        t += "\n\n⚠️ <b>CANH BAO:</b>\n" + "".join(f"  ⚡ {w}\n" for w in a["warnings"] if w)
    if any(a.get("avoid_zones",[])):
        t += "\n🚫 <b>Vung can tranh:</b>\n" + "".join(f"  • {z}\n" for z in a["avoid_zones"] if z)
    send(t)
    print(f"Da gui 4 tin nhan Telegram")

def send_alert(text: str):
    send(f"⚠️ <b>Alert</b>\n{text}")