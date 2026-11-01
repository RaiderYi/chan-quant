"""特征体检：覆盖率、方差、单变量 AUC（对正收益 / 对大波两个标签）。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import numpy as np
import pandas as pd

from chan_quant.features import schema
from chan_quant.models.train import load, auc


def main(name="events_v2"):
    df = load(name)
    cols = schema.load()
    X = df[cols].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y1 = (df["c_pol_dir_ret"] > 0).astype(int)
    y2 = (df["c_pol_dir_ret"] > 0.02).astype(int)
    rows = []
    for c in cols:
        s = X[c]
        sd = s.std()
        a1 = auc(y1, s) if sd > 0 else np.nan
        a2 = auc(y2, s) if sd > 0 else np.nan
        rows.append({"feature": c, "nonzero": float((s != 0).mean()), "std": float(sd),
                     "auc_pos": a1, "auc_big": a2})
    out = pd.DataFrame(rows)
    out["edge_pos"] = (out["auc_pos"] - 0.5).abs()
    out["edge_big"] = (out["auc_big"] - 0.5).abs()
    out = out.sort_values("edge_big", ascending=False)
    out.to_csv(r"D:\工作\chan_quant\reports\feature_health.csv", index=False, encoding="utf-8-sig")
    print("dead (std=0 or nonzero<1%):")
    dead = out[(out["std"] == 0) | (out["nonzero"] < 0.01)]
    print(dead[["feature", "nonzero", "std"]].to_string(index=False) if len(dead) else "  none")
    print("\ntop 15 by |AUC-0.5| on big-move label:")
    print(out.head(15)[["feature", "nonzero", "auc_pos", "auc_big"]].round(3).to_string(index=False))
    print("\ntop 15 by |AUC-0.5| on profitable label:")
    o2 = out.sort_values("edge_pos", ascending=False)
    print(o2.head(15)[["feature", "auc_pos", "auc_big"]].round(3).to_string(index=False))
    print(f"\nfeatures: {len(cols)}  |AUC-0.5|>0.03 on pos: {(out['edge_pos']>0.03).sum()}  on big: {(out['edge_big']>0.03).sum()}")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["events_v2"]))
