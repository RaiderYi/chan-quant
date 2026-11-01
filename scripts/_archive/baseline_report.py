"""无模型基线：按类型/方向/年份统计 BSP 事件的前向收益与胜率。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import numpy as np
import pandas as pd

from chan_quant.models import train


def stat(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    se = s.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan
    return {"n": len(s), "mean": s.mean(), "median": s.median(), "win": (s > 0).mean(),
            "t": s.mean() / se if se and se > 0 else np.nan,
            "p25": s.quantile(0.25), "p75": s.quantile(0.75)}


def main(name="events_v0b", h=24):
    df = train.load(name)
    col = f"dir_ret_{h}"
    print(f"# 基线：{name}  n={len(df)}  H={h}  span={df.event_time.min()}~{df.event_time.max()}")
    print(f"\n全样本: mean={df[col].mean():.4f} win={(df[col]>0).mean():.3f}")

    rows = []
    for side, sd in ((1, "BUY"), (0, "SELL")):
        sub = df[df.is_buy == side]
        rows.append({"group": sd, **stat(sub[col])})
        for t in ("1", "1p", "2", "2s", "3a", "3b"):
            s2 = sub[sub.bsp_type.str.split(",").apply(lambda xs: t in xs)]
            if len(s2):
                rows.append({"group": f"{sd}_{t}", **stat(s2[col])})
    print("\n## 按类型")
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    df["year"] = pd.to_datetime(df.event_time).dt.year
    print("\n## 按年份（BUY）")
    print(df[df.is_buy == 1].groupby("year")[col].agg(["count", "mean", "median"]).round(4).to_string())

    print("\n## 按持有期（全样本 dir_ret）")
    out = []
    for hh in (8, 24, 48):
        out.append({"H": hh, **stat(df[f"dir_ret_{hh}"])})
    print(pd.DataFrame(out).round(4).to_string(index=False))

    print("\n## 止损命中率")
    for hh in (8, 24, 48):
        print(f"  H={hh}: buy={df[df.is_buy==1][f'stop_{hh}'].mean():.3f} "
              f"sell={df[df.is_buy==0][f'stop_{hh}'].mean():.3f}")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["events_v0b"]))
