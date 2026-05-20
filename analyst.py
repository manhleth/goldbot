import anthropic, os, json
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM = """Ban la chuyen gia phan tich XAU/USD theo Smart Money Concept (SMC) va ICT.
Quy tac bat buoc:
- Chi tra ve JSON hop le, KHONG co bat ky text nao ben ngoai JSON
- Dung so gia thuc te cu the, khong dung so 0.0 lam placeholder
- Chi de xuat setup co RR >= 3.0
- Phan tich bang tieng Viet"""

def analyze(smc_ctx: dict, min_rr: float = 3.0) -> dict:
    prompt = f"""
Du lieu SMC da tinh cho XAU/USD:
{json.dumps(smc_ctx, indent=2, ensure_ascii=False)}

Tra ve JSON theo dung schema nay (khong them text ngoai JSON):
{{
  "date": "YYYY-MM-DD",
  "bias": {{
    "direction": "BULLISH hoac BEARISH hoac RANGING",
    "confidence": "HIGH hoac MEDIUM hoac LOW",
    "summary": "1 cau tom tat ngan gon",
    "reasons": ["ly do 1 kem gia cu the", "ly do 2", "ly do 3"],
    "london_bias": "BUY hoac SELL hoac NEUTRAL",
    "ny_bias": "BUY hoac SELL hoac NEUTRAL",
    "invalidation": 0.0
  }},
  "key_levels": {{
    "major_resistance": 0.0,
    "major_support": 0.0,
    "equilibrium": 0.0,
    "weekly_high": 0.0,
    "weekly_low": 0.0
  }},
  "buy_zones": [
    {{
      "rank": 1,
      "type": "Bullish OB hoac FVG hoac Discount Zone",
      "zone_high": 0.0,
      "zone_low": 0.0,
      "why": "giai thich ngan kem gia cu the",
      "trigger": "dieu kien cu the de vao lenh mua",
      "entry": 0.0,
      "sl": 0.0,
      "tp1": 0.0,
      "tp2": 0.0,
      "rr": 0.0,
      "timeframe_confirmation": "H1 hoac M15"
    }}
  ],
  "sell_zones": [
    {{
      "rank": 1,
      "type": "Bearish OB hoac FVG hoac Premium Zone",
      "zone_high": 0.0,
      "zone_low": 0.0,
      "why": "giai thich ngan kem gia cu the",
      "trigger": "dieu kien cu the de vao lenh ban",
      "entry": 0.0,
      "sl": 0.0,
      "tp1": 0.0,
      "tp2": 0.0,
      "rr": 0.0,
      "timeframe_confirmation": "H1 hoac M15"
    }}
  ],
  "scenarios": {{
    "A": {{
      "probability": "HIGH hoac MEDIUM",
      "description": "kich ban A kem muc gia cu the",
      "play": "cach giao dich"
    }},
    "B": {{
      "probability": "MEDIUM hoac LOW",
      "description": "kich ban B kem muc gia cu the",
      "play": "cach giao dich"
    }}
  }},
  "warnings": [],
  "avoid_zones": []
}}

Chi dua vao buy_zones va sell_zones co RR >= {min_rr}. Toi da 3 zone moi loai.
"""
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