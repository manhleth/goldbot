import schedule, time, logging, os
from datetime import datetime
from fetcher  import get_all_timeframes
from smc      import build_context
from analyst  import analyze
from notifier import send_analysis, send_alert
from dotenv   import load_dotenv

load_dotenv()
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def run():
    log.info("=== Bat dau phan tich XAU/USD ===")
    try:
        tfs    = get_all_timeframes()
        ctx    = build_context(tfs)
        log.info(f"Structure: W={ctx['structure']['weekly']} D={ctx['structure']['daily']} H4={ctx['structure']['h4']}")
        result = analyze(ctx, float(os.getenv("MIN_RR", 3.0)))
        log.info(f"Bias: {result['bias']['direction']} | Buy: {len(result.get('buy_zones',[]))} | Sell: {len(result.get('sell_zones',[]))}")
        send_analysis(result)
        log.info("=== Hoan thanh ===")
    except Exception as e:
        log.error(f"Loi: {e}", exc_info=True)
        send_alert(f"Bot loi luc {datetime.now().strftime('%H:%M')}: {e}")

# Chạy lúc 00:05 ICT (17:05 UTC) mỗi ngày
schedule.every().day.at("17:05").do(run)

if __name__ == "__main__":
    print("Gold Bot dang chay 24/7...")
    send_alert("Gold Bot da khoi dong tren server!")
    run()  # Chạy ngay lần đầu
    while True:
        schedule.run_pending()
        time.sleep(30)