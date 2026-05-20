import MetaTrader5 as mt5
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def connect():
    if not mt5.initialize(
        login=int(os.getenv("MT5_LOGIN")),
        password=os.getenv("MT5_PASSWORD"),
        server=os.getenv("MT5_SERVER")
    ):
        raise Exception(f"MT5 loi: {mt5.last_error()}")

def get_ohlcv(timeframe_str="1day", size=60):
    connect()
    tf_map = {
        "1week": mt5.TIMEFRAME_W1,
        "1day":  mt5.TIMEFRAME_D1,
        "4h":    mt5.TIMEFRAME_H4,
        "1h":    mt5.TIMEFRAME_H1,
    }
    tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_D1)
    rates = mt5.copy_rates_from_pos("XAUUSDm", tf, 0, size)
    mt5.shutdown()
    if rates is None:
        raise Exception(f"Khong lay duoc data: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    for col in ["open","high","low","close"]:
        df[col] = df[col].astype(float)
    return df[["datetime","open","high","low","close"]].sort_values("datetime").reset_index(drop=True)

def get_all_timeframes():
    print("Dang lay du lieu tu MT5...")
    data = {
        "weekly": get_ohlcv("1week", 20),
        "daily":  get_ohlcv("1day",  60),
        "h4":     get_ohlcv("4h",   100),
        "h1":     get_ohlcv("1h",   100),
    }
    total = sum(len(v) for v in data.values())
    print(f"OK - Da lay {total} nen")
    return data