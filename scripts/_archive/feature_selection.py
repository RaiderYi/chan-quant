"""特征有效性评估：单变量稳定性 + 多变量贡献 + 冗余聚类 + 分组消融。

输出:
  reports/feature_selection.csv    每列特征的完整指标
  reports/feature_selection.md     结论表
"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import numpy as np
import pandas as pd
import xgboost as xgb

from chan_quant.features import schema
from chan_quant.models import train

SPLIT = "2023-06-30"
GROUPS = {"pa": "价格行为", "pt": "形态", "ch": "缠论", "mkt": "市场"}


def auc(y, s):
    return train.auc(y, s)


def auc_ci(y, s, n_boot=200, seed=0):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    s = np.asarray(s)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].sum() in (0, len(idx)):
            continue
        vals.append(auc(y[idx], s[idx]))
    if not vals:
        return np.nan, np.nan
    return float(np.percentile(vals, 5)), float(np.percentile(vals, 95))


def main(name="events_v2"):
    df = train.load(name)
    df = df[(df.is_buy == 1) & (df.conf_ok == 1)].copy()
    df["t"] = pd.to_datetime(df["event_time"])
    cols = [c for c in schema.load() if c in df.columns]
    X = df[cols].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_pos = (df["c_pol_dir_ret"] > 0).astype(int).to_numpy()
    y_big = (df["c_pol_dir_ret"] > 0.02).astype(int).to_numpy()
    year = df["t"].dt.year

    tr = df["t"] <= pd.Timestamp(SPLIT)
    te = ~tr
    Xtr, Xte = X[tr], X[te]

    # ---- 多变量模型 ----
    keep = [c for c in cols if Xtr[c].nunique() > 1]
    bst = train.fit_xgb(Xtr[keep], y_pos[tr], Xte[keep], y_pos[te], rounds=150)
    base_auc = auc(y_pos[te], bst.predict(xgb.DMatrix(Xte[keep])))
    gain = bst.get_score(importance_type="gain")
    gain = {keep[int(k[1:])]: v for k, v in gain.items() if k.startswith("f")}
    total_gain = sum(gain.values()) or 1.0
    bst_big = train.fit_xgb(Xtr[keep], y_big[tr], Xte[keep], y_big[te], rounds=150)
    base_auc_big = auc(y_big[te], bst_big.predict(xgb.DMatrix(Xte[keep])))
    gain_big = bst_big.get_score(importance_type="gain")
    gain_big = {keep[int(k[1:])]: v for k, v in gain_big.items() if k.startswith("f")}
    total_gain_big = sum(gain_big.values()) or 1.0

    # ---- 排列重要性（正收益标签）----
    rng = np.random.default_rng(1)
    perm = {}
    for c in keep:
        Xp = Xte[keep].copy()
        Xp[c] = rng.permutation(Xp[c].to_numpy())
        perm[c] = base_auc - auc(y_pos[te], bst.predict(xgb.DMatrix(Xp)))

    # ---- 单变量 + 年度稳定性 ----
    rows = []
    for c in cols:
        s = X[c].to_numpy()
        a_pos = auc(y_pos, s)
        a_big = auc(y_big, s)
        lo, hi = auc_ci(y_pos, s, n_boot=80)
        by_year = {}
        for yr in sorted(year.unique()):
            m = (year == yr).to_numpy()
            if m.sum() >= 80:
                by_year[yr] = auc(y_pos[m], s[m])
        vals = [v for v in by_year.values() if v == v]
        sign_stable = 0.0
        if len(vals) >= 3:
            same = sum(1 for v in vals if (v - 0.5) * (a_pos - 0.5) > 0)
            sign_stable = same / len(vals)
        rows.append({
            "feature": c, "group": c.split("_")[0],
            "auc_pos": a_pos, "ci_lo": lo, "ci_hi": hi,
            "auc_big": a_big,
            "sign_stable": sign_stable,
            "perm_imp": perm.get(c, np.nan),
            "gain_pos": gain.get(c, 0.0) / total_gain,
            "gain_big": gain_big.get(c, 0.0) / total_gain_big,
            "std": float(s.std()),
        })
    out = pd.DataFrame(rows)

    # ---- 冗余聚类（Spearman |rho|>=0.8，保留单变量更强的一列）----
    corr = X[keep].corr(method="spearman").abs()
    out["redundant_with"] = ""
    kept = []
    for c in out.sort_values("auc_big", key=lambda s: (s - 0.5).abs(), ascending=False)["feature"]:
        if c not in keep:
            continue
        dup = next((k for k in kept if corr.loc[c, k] >= 0.8), None)
        if dup:
            out.loc[out.feature == c, "redundant_with"] = dup
        else:
            kept.append(c)
    out["kept_after_cluster"] = ~out["redundant_with"].astype(bool)

    # ---- 分组消融 ----
    abl = []
    for g in GROUPS:
        sub = [c for c in keep if not c.startswith(g + "_")]
        b = train.fit_xgb(Xtr[sub], y_big[tr], Xte[sub], y_big[te], rounds=150)
        abl.append({"removed": g, "auc_big": auc(y_big[te], b.predict(xgb.DMatrix(Xte[sub])))})
    abl.append({"removed": "none", "auc_big": base_auc_big})
    abl_df = pd.DataFrame(abl)

    out.to_csv(r"D:\工作\chan_quant\reports\feature_selection.csv", index=False, encoding="utf-8-sig")

    # ---- 结论表 ----
    eff = out[(out["perm_imp"] > 0.002) & (out["sign_stable"] >= 0.6)].sort_values("perm_imp", ascending=False)
    print(f"events={len(df)} features={len(cols)} base_auc_pos={base_auc:.4f} base_auc_big={base_auc_big:.4f}")
    print("\n## 分组消融（大波标签 AUC）")
    print(abl_df.round(4).to_string(index=False))
    print("\n## 多变量有效特征（perm_imp>0.002 且年度方向一致≥60%）")
    print(eff[["feature", "auc_pos", "auc_big", "sign_stable", "perm_imp", "gain_big"]].head(40).round(3).to_string(index=False))
    print("\n## 单变量最强 Top15（大波标签）")
    top = out.assign(edge=(out["auc_big"] - 0.5).abs()).sort_values("edge", ascending=False).head(15)
    print(top[["feature", "auc_big", "sign_stable", "redundant_with"]].round(3).to_string(index=False))
    print(f"\n聚类后保留：{int(out['kept_after_cluster'].sum())} / {len(cols)}")
    return out


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["events_v2"]))
