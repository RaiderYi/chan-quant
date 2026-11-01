"""标签：前向收益 / 最大有利不利偏移 / 止损命中，全部在入场后计算。

统一口径：
- 入场价 = 决策 bar 下一根的开盘价
- 持有 H 根，第 H 根收盘离场
- 成本 = 单边费率 × 2（默认 10bps + 印花税，按往返 13bps 计）
- dir_ret = 买点取多头收益，卖点取反向收益（信号一致性）
"""
import numpy as np

HORIZONS = (8, 24, 48)     # 30分钟：约 1 / 3 / 6 个交易日
FORWARD_KEYS = tuple(f"{k}_{h}" for h in HORIZONS for k in ("ret", "dir_ret", "mfe", "mae", "stop"))


def forward_labels(ind: dict, entry_idx: int, is_buy: int, atr: float,
                   horizons=HORIZONS, cost: float = 0.0013, stop_atr: float = 2.0) -> dict:
    n = len(ind["close"])
    out = {}
    if entry_idx >= n:
        return out
    entry = ind["open"][entry_idx]
    if entry <= 0:
        return out
    sign = 1.0 if is_buy else -1.0
    stop_dist = stop_atr * atr / entry if entry > 0 else 0.0

    for H in horizons:
        end = min(entry_idx + H - 1, n - 1)
        if end < entry_idx:
            out[f"ret_{H}"] = np.nan
            out[f"dir_ret_{H}"] = np.nan
            out[f"mfe_{H}"] = np.nan
            out[f"mae_{H}"] = np.nan
            out[f"stop_{H}"] = np.nan
            continue
        hi = ind["high"][entry_idx:end + 1].max()
        lo = ind["low"][entry_idx:end + 1].min()
        close = ind["close"][end]
        ret = close / entry - 1.0 - cost
        mfe = sign * (hi / entry - 1.0) if is_buy else sign * (1.0 - lo / entry)
        mae = sign * (lo / entry - 1.0) if is_buy else sign * (1.0 - hi / entry)
        hit = (lo <= entry * (1 - stop_dist)) if is_buy else (hi >= entry * (1 + stop_dist))
        out[f"ret_{H}"] = ret
        out[f"dir_ret_{H}"] = sign * ret
        out[f"mfe_{H}"] = mfe
        out[f"mae_{H}"] = mae
        out[f"stop_{H}"] = 1.0 if hit else 0.0
    return out
