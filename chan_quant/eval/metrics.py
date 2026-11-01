"""评估指标：AUC、bootstrap 区间、分位 lift、分组汇总。"""
import numpy as np
import pandas as pd


def auc(y, s) -> float:
    """Mann-Whitney 形式 AUC（不依赖 sklearn）。"""
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=float)
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    ranks = pd.Series(s).rank().to_numpy()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def auc_ci(y, s, n_boot: int = 200, alpha: float = 0.10, seed: int = 0):
    """bootstrap 置信区间（默认 90%）。"""
    rng = np.random.default_rng(seed)
    y, s = np.asarray(y), np.asarray(s)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].sum() in (0, len(idx)):
            continue
        vals.append(auc(y[idx], s[idx]))
    if not vals:
        return float("nan"), float("nan")
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def quantile_lift(df: pd.DataFrame, score, label: str, q: float = 0.2) -> dict:
    """分数前 q / 后 q 分位的标签均值与胜率。"""
    s = pd.Series(np.asarray(score), index=df.index)
    hi = s >= s.quantile(1 - q)
    lo = s <= s.quantile(q)
    return {
        "n_top": int(hi.sum()), "n_bot": int(lo.sum()),
        "top_mean_bp": float(df.loc[hi, label].mean() * 1e4),
        "bot_mean_bp": float(df.loc[lo, label].mean() * 1e4),
        "top_win": float((df.loc[hi, label] > 0).mean()),
        "bot_win": float((df.loc[lo, label] > 0).mean()),
    }


def summarize(df: pd.DataFrame, label: str, group_col: str = "bsp_type") -> pd.DataFrame:
    """按分组统计均值 / 胜率 / t 值。"""
    rows = []
    for key, sub in df.groupby(group_col):
        s = sub[label].dropna()
        if len(s) < 20:
            continue
        se = s.std(ddof=1) / np.sqrt(len(s))
        rows.append({"group": key, "n": len(s), "mean_bp": s.mean() * 1e4,
                     "median_bp": s.median() * 1e4, "win": (s > 0).mean(),
                     "t": s.mean() / se if se > 0 else np.nan})
    return pd.DataFrame(rows).sort_values("n", ascending=False)
