import anthropic, os, json
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM = """Ban la trader vang chuyen nghiep phan tich XAU/USD theo SMC + ICT.
Phong cach: cho phan ung gia tai FVG de vao lenh.
Quy tac:
- Tra ve JSON hop le, KHONG co text ben ngoai
- Ngan gon, suc tich, thuc te
- Chi neu vung FVG quan trong nhat, bo qua vung yeu
- Uu tien FVG chua duoc fill, co confluence voi OB
- Chi de xuat setup co RR >= 3.0"""

def analyze(smc_ctx: dict, min_rr: float = 3.0) -> dict:
    prompt = (
        "Du lieu SMC XAU/USD:\n"
        + json.dumps(smc_ctx, indent=2, ensure_ascii=False)
        + """

Tra ve JSON ngan gon theo schema sau:
{
  "date": "YYYY-MM-DD",
  "bias": {
    "direction": "BULLISH|BEARISH|RANGING",
    "confidence": "HIGH|MEDIUM|LOW",
    "one_line": "1 cau tom tat don gian nhat",
    "invalidation": 0.0
  },
  "fvg_zones": [
    {
      "rank": 1,
      "direction": "BUY|SELL",
      "timeframe": "Daily|H4|H1",
      "zone_high": 0.0,
      "zone_low": 0.0,
      "confluence": "OB|Swing Low|Liquidity|EQ",
      "entry_trigger": "Mo lenh khi gia cham vung va xuat hien [ten nen] tren [TF]",
      "sl": 0.0,
      "tp1": 0.0,
      "tp2": 0.0,
      "rr": 0.0
    }
  ],
  "key_levels": {
    "resistance": 0.0,
    "support": 0.0,
    "eq": 0.0
  },
  "avoid": "Mo ta ngan vung/dieu kien can tranh hom nay"
}

Chi dua toi da 4 FVG quan trong nhat (2 buy + 2 sell), bo qua FVG yeu. RR toi thieu """
        + str(min_rr)
        + "."
    )

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2500,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                return json.loads(part)
            except:
                continue
    return json.loads(raw)