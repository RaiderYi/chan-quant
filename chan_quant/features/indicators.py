"""因果指标预计算：整条序列一次算完，第 i 个值只用 0..i 的数据。"""
import numpy as np
import pandas as pd


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def precompute(df: pd.DataFrame) -> dict:
    close = df["close"].astype(float).to_numpy()
    high = df["high"].astype(float).to_numpy()
    low = df["low"].astype(float).to_numpy()
    open_ = df["open"].astype(float).to_numpy()
    vol = df["volume"].astype(float).to_numpy()

    cs, hs, ls = pd.Series(close), pd.Series(high), pd.Series(low)
    prev_close = cs.shift(1)

    # ATR / 波动
    tr = pd.concat([hs - ls, (hs - prev_close).abs(), (ls - prev_close).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()

    # MACD
    dif = _ema(cs, 12) - _ema(cs, 26)
    dea = _ema(dif, 9)
    macd_bar = 2 * (dif - dea)

    # RSI (Wilder)
    delta = cs.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi14 = 100 - 100 / (1 + up / dn.replace(0, np.nan))

    # BOLL
    ma20 = cs.rolling(20).mean()
    std20 = cs.rolling(20).std(ddof=0)
    boll_up, boll_dn = ma20 + 2 * std20, ma20 - 2 * std20

    # 均线
    ma5, ma10, ma60 = cs.rolling(5).mean(), cs.rolling(10).mean(), cs.rolling(60).mean()

    # 区间（不含当前 bar）
    hh20 = hs.shift(1).rolling(20).max()
    ll20 = ls.shift(1).rolling(20).min()
    hh50 = hs.shift(1).rolling(50).max()
    ll50 = ls.shift(1).rolling(50).min()

    # 20 bar 线性回归（斜率、R²），窗口末端为当前 bar
    n = 20
    x = np.arange(n, dtype=float)
    sx, sxx = x.sum(), (x ** 2).sum()
    conv_k = x[::-1].copy()
    sxy = pd.Series(np.convolve(close, conv_k, mode="full")[: len(close)])
    sy = cs.rolling(n).sum()
    syy = (cs ** 2).rolling(n).sum()
    slope = (n * sxy - sx * sy) / (n * sxx - sx ** 2)
    cov = n * sxy - sx * sy
    varx = n * sxx - sx ** 2
    vary = n * syy - sy ** 2
    r2 = (cov ** 2) / (varx * vary.replace(0, np.nan))

    # 成交量
    vma5, vma20 = pd.Series(vol).rolling(5).mean(), pd.Series(vol).rolling(20).mean()

    def arr(s):
        return s.to_numpy(dtype=float)

    return {
        "close": close, "open": open_, "high": high, "low": low, "vol": vol,
        "atr14": arr(atr14), "tr": arr(tr),
        "dif": arr(dif), "dea": arr(dea), "macd_bar": arr(macd_bar),
        "rsi14": arr(rsi14),
        "ma5": arr(ma5), "ma10": arr(ma10), "ma20": arr(ma20), "ma60": arr(ma60),
        "std20": arr(std20), "boll_up": arr(boll_up), "boll_dn": arr(boll_dn),
        "hh20": arr(hh20), "ll20": arr(ll20), "hh50": arr(hh50), "ll50": arr(ll50),
        "slope20": arr(slope), "r2_20": arr(r2),
        "vma5": arr(vma5), "vma20": arr(vma20),
        "range20": arr((hh20 - ll20) / cs),
    }
