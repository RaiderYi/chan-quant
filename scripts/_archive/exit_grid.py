"""退出规则网格 + 事件子集筛选：在 17k 个 BSP 事件上测哪种组合有正期望。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import itertools
import numpy as np
import pandas as pd

from chan_quant.data import store
from chan_quant.models import train


def policy_ret(entry, bars, i0, is_buy, atr, H, stop_atr, cost=0.0013):
    n = len(bars["close"])
    stop = entry - stop_atr * atr if is_buy else entry + stop_atr * atr
    end = min(i0 + H - 1, n - 1)
    for i in range(i0, end + 1):
        if is_buy and bars["low"][i] <= stop:
            return stop / entry - 1 - cost
        if (not is_buy) and bars["high"][i] >= stop:
            return stop / entry - 1 - cost
    return bars["close"][end] / entry - 1 - cost


def main(name="events_v1"):
    df = train.load(name)
    codes = df.code.unique()
    data = {}
    for c in codes:
        b = store.load(c, "30m")
        data[c] = {"open": b.open.to_numpy(), "high": b.high.to_numpy(),
                   "low": b.low.to_numpy(), "close": b.close.to_numpy()}

    rows = []
    for H, stop in itertools.product((8, 24, 48), (1.0, 1.5, 2.0, 3.0)):
        rets = []
        for r in df.itertuples():
            b = data[r.code]
            i0 = int(r.entry_idx)
            if i0 >= len(b["open"]):
                continue
            rr = policy_ret(b["open"][i0], b, i0, bool(r.is_buy), float(r.atr), H, stop)
            rets.append(rr if r.is_buy else -rr)
        s = pd.Series(rets)
        rows.append({"H": H, "stop_atr": stop, "n": len(s), "mean_bp": s.mean() * 1e4,
                     "win": (s > 0).mean(), "sharpe_like": s.mean() / s.std() * np.sqrt(252)})
    grid = pd.DataFrame(rows)
    print("## 退出规则网格（dir_ret, bp）")
    print(grid.round(2).to_string(index=False))

    # 事件子集筛选（固定最优退出组合）
    best = grid.loc[grid["mean_bp"].idxmax()]
    H, stop = int(best["H"]), float(best["stop_atr"])
    print(f"\n# 用 H={H} stop={stop} 做子集筛选")
    subs = {
        "all": df,
        "buy_only": df[df.is_buy == 1],
        "buy_fresh": df[(df.is_buy == 1) & (df.delay_bars == 0)],
        "buy_t2": df[(df.is_buy == 1) & df.bsp_type.str.contains("2")],
        "buy_t1p": df[(df.is_buy == 1) & df.bsp_type.str.contains("1p")],
        "buy_zs2+": df[(df.is_buy == 1) & (df.ch_bsp_zs_cnt >= 2)],
        "buy_div<.9": df[(df.is_buy == 1) & (df.ch_bsp_div < 0.9)],
        "buy_mkt_up": df[(df.is_buy == 1) & (df.mkt_above_ma20 == 1)],
        "buy_mkt_60up": df[(df.is_buy == 1) & (df.mkt_above_ma60 == 1)],
        "buy_trend": df[(df.is_buy == 1) & (df.pa_trend_dir == 1)],
        "buy_breakout": df[(df.is_buy == 1) & (df.pa_breakout_up == 1)],
        "buy_lowvol": df[(df.is_buy == 1) & (df.pa_atr_pct < df.pa_atr_pct.median())],
    }
    out = []
    for k, sub in subs.items():
        rets = []
        for r in sub.itertuples():
            b = data[r.code]
            i0 = int(r.entry_idx)
            rr = policy_ret(b["open"][i0], b, i0, bool(r.is_buy), float(r.atr), H, stop)
            rets.append(rr if r.is_buy else -rr)
        s = pd.Series(rets)
        se = s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan
        out.append({"subset": k, "n": len(s), "mean_bp": s.mean() * 1e4,
                    "win": (s > 0).mean(), "t": s.mean() / se if se and se > 0 else np.nan})
    print(pd.DataFrame(out).round(2).to_string(index=False))


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["events_v1"]))
