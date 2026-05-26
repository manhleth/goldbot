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

    dir_e  = {"BULLISH":"📈","BEARISH":"📉","RANGING":"↔️"}.get(b["direction"],"❓")
    conf_e = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(b["confidence"],"⚪")

    # Tin 1: Bias + Key Levels (ngắn gọn)
    send(
        f"<b>XAU/USD {a['date']}</b>\n"
        f"{dir_e} {b['direction']} {conf_e}  —  {b['one_line']}\n\n"
        f"R: <b>{kl['resistance']}</b>  |  S: <b>{kl['support']}</b>  |  EQ: <b>{kl['eq']}</b>\n"
        f"Invalidate: {b['invalidation']}\n\n"
        f"🚫 Tránh: {a['avoid']}"
    )
    time.sleep(0.3)

    # Tin 2: FVG Zones
    if a.get("fvg_zones"):
        t = "📍 <b>FVG QUAN TRONG</b>\n\n"
        for z in a["fvg_zones"][:4]:
            icon = "🟢" if z["direction"] == "BUY" else "🔴"
            t += (
                f"{icon} <b>{z['direction']} — {z['timeframe']}</b>\n"
                f"Vung: {z['zone_low']} — {z['zone_high']}\n"
                f"Confluence: {z['confluence']}\n"
                f"▶ {z['entry_trigger']}\n"
                f"SL: {z['sl']}  TP1: {z['tp1']}  TP2: {z['tp2']}  RR: 1:{z['rr']:.1f}\n\n"
            )
        send(t)

    print("Da gui Telegram")

def send_alert(text: str):
    send(f"⚠️ <b>Alert</b>\n{text}")