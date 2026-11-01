"""确认入场评估：信号后 N 根内收盘突破信号 bar 高/低才入场，比较期望收益。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import itertools
import numpy as np
import pandas as pd

from chan_quant.data import store
from chan_quant.models import train


def pol(b, i0, entry, is_buy, atr, H, stop_atr, cost=0.0013):
    n = len(b["close"])
    stop = entry - stop_atr * atr if is_buy else entry + stop_atr * atr
    end = min(i0 + H - 1, n - 1)
    for i in range(i0, end + 1):
        if is_buy and b["low"][i] <= stop:
            return stop / entry - 1 - cost
        if (not is_buy) and b["high"][i] >= stop:
            return stop / entry - 1 - cost
    return b["close"][end] / entry - 1 - cost


def main(name="events_v1"):
    df = train.load(name)
    bars = {c: {"open": store.load(c, "30m").open.to_numpy(),
                "high": store.load(c, "30m").high.to_numpy(),
                "low": store.load(c, "30m").low.to_numpy(),
                "close": store.load(c, "30m").close.to_numpy()} for c in df.code.unique()}

    rows = []
    for wait, H, stop in itertools.product((1, 2, 4), (24, 48), (1.5, 2.0)):
        rets, waits = [], []
        for r in df.itertuples():
            b = bars[r.code]
            i0 = int(r.entry_idx)
            if i0 >= len(b["open"]):
                continue
            ref = b["high"][i0 - 1] if r.is_buy else b["low"][i0 - 1]
            idx = None
            for i in range(i0, min(i0 + wait, len(b["close"]) - 1)):
                if r.is_buy and b["close"][i] > ref:
                    idx = i + 1
                    break
                if (not r.is_buy) and b["close"][i] < ref:
                    idx = i + 1
                    break
            if idx is None:
                continue
            rr = pol(b, idx, b["open"][idx], bool(r.is_buy), float(r.atr), H, stop)
            rets.append(rr if r.is_buy else -rr)
            waits.append(idx - i0 + 1)
        s = pd.Series(rets)
        se = s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan
        rows.append({"wait": wait, "H": H, "stop": stop, "n": len(s),
                     "cover": len(s) / len(df), "mean_bp": s.mean() * 1e4,
                     "win": (s > 0).mean(), "t": s.mean() / se if se else np.nan})
    g = pd.DataFrame(rows)
    print("## 确认入场（全部事件）")
    print(g.round(1).to_string(index=False))

    # 只看买点
    rows = []
    for wait, H, stop in itertools.product((1, 2, 4), (24, 48), (1.5, 2.0)):
        rets = []
        for r in df[df.is_buy == 1].itertuples():
            b = bars[r.code]
            i0 = int(r.entry_idx)
            ref = b["high"][i0 - 1]
            idx = None
            for i in range(i0, min(i0 + wait, len(b["close"]) - 1)):
                if b["close"][i] > ref:
                    idx = i + 1
                    break
            if idx is None:
                continue
            rets.append(pol(b, idx, b["open"][idx], True, float(r.atr), H, stop))
        s = pd.Series(rets)
        se = s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan
        rows.append({"wait": wait, "H": H, "stop": stop, "n": len(s),
                     "mean_bp": s.mean() * 1e4, "win": (s > 0).mean(),
                     "t": s.mean() / se if se else np.nan})
    print("\n## 确认入场（仅买点）")
    print(pd.DataFrame(rows).round(1).to_string(index=False))


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["events_v1"]))
