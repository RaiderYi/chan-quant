"""Yearly returns of a backtest equity curve vs the equal-weight market."""
import sys
from pathlib import Path

import _path  # noqa: F401
import pandas as pd

from chan_quant.config import DATA
from chan_quant.data import store
from chan_quant.features import indicators


def main(name: str = "h144_no_signal_exit"):
    eq = pd.read_parquet(DATA / "bt" / f"{name}_equity.parquet")
    eq = eq["equity"] if "time" not in eq.columns else eq.set_index("time")["equity"]
    yearly = eq.resample("YE").last() / eq.resample("YE").first() - 1

    mdf = store.load("_MARKET", "30m")
    ind = indicators.precompute(mdf)
    ser = pd.Series(ind["close"], index=pd.to_datetime(mdf["time"]))
    mkt = ser.resample("YE").last() / ser.resample("YE").first() - 1

    out = pd.DataFrame({"strategy": yearly.values, "market": mkt.values},
                       index=[d.year for d in yearly.index])
    out["excess"] = out["strategy"] - out["market"]
    print(out.round(3).to_string())
    print(f"\ncum strategy {eq.iloc[-1]/eq.iloc[0]-1:.1%}  market {ser.iloc[-1]/ser.iloc[0]-1:.1%}")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["h144_no_signal_exit"]))
