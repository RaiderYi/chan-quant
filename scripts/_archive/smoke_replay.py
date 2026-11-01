"""冒烟测试：合成日线 -> 逐bar回放 -> BSP事件 -> 特征。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import pandas as pd

from chan_quant.core import replay
from DataAPI.LocalStore import put_bars

df = pd.read_csv(r"D:\工作\chan_compare\synth_daily.csv")
df["time"] = pd.to_datetime(df["time"])
put_bars("SYN1", "day", df)

events, elapsed = replay.replay("SYN1", "day", warmup=100, verbose=True, df=df)
print(f"events={len(events)} elapsed={elapsed:.2f}s")

if events:
    f0 = events[0].features
    print("feature count:", len(f0))
    print("delay bars:", sorted({e.delay_bars for e in events}))
    # schema 一致性
    keys = [set(e.features) for e in events]
    union, inter = set().union(*keys), set().intersection(*keys)
    print("union:", len(union), "inter:", len(inter), "diff:", sorted(union - inter)[:10])
    print("types:", pd.Series([e.bsp_type for e in events]).value_counts().to_dict())
    for k in ("pa_body_ratio", "pa_close_pos", "ch_bi_amp", "ch_zs_pos", "ch_bsp_div", "ch_bsp_T2"):
        print(f"  {k} = {f0.get(k)}")
