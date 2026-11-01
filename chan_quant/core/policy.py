"""统一的退出规则模拟。

标签、评估脚本、组合回测共用这一份实现，避免同一规则被复制多份后走样。
"""
from dataclasses import dataclass

DEFAULT_COST = 0.0013      # 往返成本（佣金+印花税+滑点粗估）
DEFAULT_HOLD = 24
DEFAULT_STOP_ATR = 2.0
POLICY_KEYS = ("pol_ret", "pol_dir_ret", "pol_bars", "pol_stop")


@dataclass(frozen=True)
class ExitResult:
    ret: float        # 原始收益（扣成本，未按信号方向取号）
    bars: int         # 实际持有 bar 数
    reason: str       # stop / time


def simulate_exit(ind: dict, entry_idx: int, is_buy: int, atr: float,
                  hold: int = DEFAULT_HOLD, stop_atr: float = DEFAULT_STOP_ATR,
                  trail_atr: float = 0.0, cost: float = DEFAULT_COST) -> ExitResult | None:
    """按「入场后先触止损则止损、否则第 hold 根收盘离场」模拟单笔交易。

    trail_atr > 0 时启用移动止损：用**已收 bar** 的极值更新止损，
    再在下一根检查是否触发（避免同一根内的未来信息）。
    """
    n = len(ind["close"])
    if entry_idx >= n or entry_idx < 0:
        return None
    entry = ind["open"][entry_idx]
    if entry <= 0:
        return None
    stop = entry - stop_atr * atr if is_buy else entry + stop_atr * atr
    peak = ind["high"][entry_idx] if is_buy else ind["low"][entry_idx]
    end = min(entry_idx + hold - 1, n - 1)
    for i in range(entry_idx, end + 1):
        if is_buy and ind["low"][i] <= stop:
            return ExitResult(stop / entry - 1 - cost, i - entry_idx + 1,
                              "trail" if trail_atr > 0 and stop > entry - stop_atr * atr else "stop")
        if (not is_buy) and ind["high"][i] >= stop:
            return ExitResult(stop / entry - 1 - cost, i - entry_idx + 1,
                              "trail" if trail_atr > 0 and stop < entry + stop_atr * atr else "stop")
        if trail_atr > 0:
            if is_buy:
                peak = max(peak, ind["high"][i])
                stop = max(stop, peak - trail_atr * atr)
            else:
                peak = min(peak, ind["low"][i])
                stop = min(stop, peak + trail_atr * atr)
    return ExitResult(ind["close"][end] / entry - 1 - cost, end - entry_idx + 1, "time")


def policy_labels(ind: dict, entry_idx: int, is_buy: int, atr: float, **kw) -> dict:
    """供数据集构建使用的标签字典（去掉 None 情况）。"""
    r = simulate_exit(ind, entry_idx, is_buy, atr, **kw)
    if r is None:
        return {}
    return {"pol_ret": r.ret, "pol_dir_ret": r.ret if is_buy else -r.ret,
            "pol_bars": float(r.bars), "pol_stop": 1.0 if r.reason == "stop" else 0.0}
