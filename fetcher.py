import requests, os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("TWELVE_DATA_API_KEY")

def get_ohlcv(interval="1day", size=60):
    r = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": size,
        "apikey": KEY,
        "format": "JSON"
    }, timeout=15)
    data = r.json()
    if "values" not in data:
        raise Exception(f"Twelve Data loi: {data.get('message', data)}")
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["open","high","low","close"]:
        df[col] = df[col].astype(float)
    return df.sort_values("datetime").reset_index(drop=True)

def get_all_timeframes():
    print("Dang lay du lieu...")
    data = {
        "weekly": get_ohlcv("1week", 20),
        "daily":  get_ohlcv("1day",  60),
        "h4":     get_ohlcv("4h",   100),
        "h1":     get_ohlcv("1h",   100),
    }
    print(f"OK - Da lay {sum(len(v) for v in data.values())} nen")
    return data