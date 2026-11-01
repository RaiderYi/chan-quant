"""标签探针：同一批特征在不同标签定义下是否有区分度（时间切分，非 WF）。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import numpy as np
import pandas as pd
import xgboost as xgb

from chan_quant.features import schema
from chan_quant.models import train

BASE = "c_pol_dir_ret"


def probe(df, name, y, cols, split="2023-06-30"):
    t = pd.to_datetime(df["event_time"])
    tr = t <= pd.Timestamp(split)
    te = t > pd.Timestamp(split)
    if tr.sum() < 200 or te.sum() < 100:
        print(f"{name}: insufficient ({tr.sum()}/{te.sum()})")
        return
    X = df[cols].astype(float).replace([np.inf, -np.inf], np.nan)
    keep = [c for c in cols if X.loc[tr, c].nunique(dropna=True) > 1]
    bst = train.fit_xgb(X.loc[tr, keep], y[tr], X.loc[te, keep], y[te], rounds=150)
    p = bst.predict(xgb.DMatrix(X.loc[te, keep]))
    from chan_quant.models.train import auc
    print(f"{name:22s} n_tr={int(tr.sum()):5d} n_te={int(te.sum()):5d} base={y[tr].mean():.3f} "
          f"AUC_te={auc(y[te], p):.4f}")


def main(name="events_v2"):
    df = train.load(name)
    df = df[(df.is_buy == 1) & (df.conf_ok == 1)].copy()
    df[BASE] = df[BASE].astype(float)
    cols = [c for c in schema.load() if c in df.columns]
    print(f"events={len(df)}")
    probe(df, "正收益 (>0)", (df[BASE] > 0).astype(int), cols)
    probe(df, ">1%", (df[BASE] > 0.01).astype(int), cols)
    probe(df, ">2%", (df[BASE] > 0.02).astype(int), cols)
    probe(df, ">3%", (df[BASE] > 0.03).astype(int), cols)
    q = df[BASE].quantile(0.75)
    probe(df, "上四分位", (df[BASE] > q).astype(int), cols)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["events_v2"]))
