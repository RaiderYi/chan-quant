"""给 events_v6 追加真实交易标签 pol144_ret（144bar/3ATR，conf_entry_idx 起算）。

用法：python scripts/make_v6_label.py [events_v6]
逻辑与 make_v5_label.py 一致，参数化输入版本。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from chan_quant.core.policy import simulate_exit
from chan_quant.eval.bars import for_policy, load_many
from chan_quant.models import train

HOLD, STOP = 144, 3.0
NAME = sys.argv[1] if len(sys.argv) > 1 else "events_v6"
FREQ = sys.argv[2] if len(sys.argv) > 2 else "30m"
# 成本：A股 13bp（默认）；加密 taker 往返 10bp+滑点 2bp=12bp，用第三参数传入
COST = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0013

df = train.load(NAME)
arrays = {c: for_policy(a) for c, a in load_many(df.code.unique(), FREQ).items()}

rets = []
for r in df.itertuples():
    if r.is_buy == 1 and r.conf_ok == 1:
        res = simulate_exit(arrays[r.code], int(r.conf_entry_idx), 1, float(r.atr),
                            hold=HOLD, stop_atr=STOP, trail_atr=0.0, cost=COST)
        rets.append(res.ret if res is not None else np.nan)
    else:
        rets.append(np.nan)
df["pol144_ret"] = rets

out = Path(__file__).resolve().parents[1] / "data" / "events" / f"{NAME}.parquet"
df.to_parquet(out, index=False)
ok = df.dropna(subset=["pol144_ret"])
print(f"saved {out} rows={len(df)}; labeled conf_buy={len(ok)} "
      f"mean={ok['pol144_ret'].mean()*1e4:.1f}bp win={(ok['pol144_ret']>0).mean()*100:.1f}%")
