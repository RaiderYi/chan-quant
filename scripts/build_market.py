"""构建等权市场指数序列（用全部个股 30m 收盘价的中位数归一化），用于市场环境特征。"""
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from chan_quant.data import store


def build_market(freq: str = "30m", min_stocks: int = 30, out_code: str = "_MARKET") -> pd.DataFrame:
    codes = [c for c in store.list_codes(freq) if not c.startswith("_")]
    frames = []
    for c in codes:
        df = store.load(c, freq)[["time", "close"]].copy()
        df = df.rename(columns={"close": c})
        frames.append(df.set_index("time"))
    px = pd.concat(frames, axis=1).sort_index()
    px = px.ffill(limit=8)
    norm = px / px.bfill().iloc[0]
    level = norm.median(axis=1)
    cnt = px.notna().sum(axis=1)
    level = level[cnt >= min_stocks]
    ret = level.pct_change().fillna(0)
    close = 1000 * (1 + ret).cumprod()
    df = pd.DataFrame({
        "time": close.index,
        "open": close.shift(1).fillna(close.iloc[0]).values,
        "high": close.values * (1 + ret.abs().rolling(3).mean().fillna(0).values * 0.3),
        "low": close.values * (1 - ret.abs().rolling(3).mean().fillna(0).values * 0.3),
        "close": close.values,
        "volume": 0.0,
    })
    store.save(out_code, df, freq)
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", default="30m")
    args = ap.parse_args()
    df = build_market(args.freq)
    print(f"market bars[{args.freq}]", len(df), df["time"].min(), df["time"].max())
