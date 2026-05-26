import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM = "Ban la trader vang chuyen nghiep phan tich XAU/USD theo SMC + ICT. Tra ve JSON hop le, KHONG co text ben ngoai. Ngan gon, chi FVG quan trong, RR >= 3.0"

def analyze(smc_ctx: dict, min_rr: float = 3.0) -> dict:
    data_str = json.dumps(smc_ctx, indent=2, ensure_ascii=False)
    
    schema = json.dumps({
        "date": "YYYY-MM-DD",
        "bias": {
            "direction": "BULLISH|BEARISH|RANGING",
            "confidence": "HIGH|MEDIUM|LOW",
            "one_line": "1 cau tom tat",
            "invalidation": 0.0
        },
        "fvg_zones": [
            {
                "rank": 1,
                "direction": "BUY|SELL",
                "timeframe": "Daily|H4|H1",
                "zone_high": 0.0,
                "zone_low": 0.0,
                "confluence": "OB|Swing|Liquidity|EQ",
                "entry_trigger": "mo ta cach vao lenh",
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
        "avoid": "vung can tranh hom nay"
    }, indent=2, ensure_ascii=False)

    content = "Du lieu SMC XAU/USD:\n" + data_str + "\n\nTra ve JSON theo schema:\n" + schema + "\n\nChi 4 FVG quan trong nhat. RR toi thieu " + str(min_rr)

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2500,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}]
    )

    raw = msg.content[0].text.strip()

    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except Exception:
                continue

    return json.loads(raw)