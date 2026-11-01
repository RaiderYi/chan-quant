"""v0 基线：全样本 + 分方向 + 分类型，24bar 标签，时间切分。"""
import sys
sys.path.insert(0, r"D:\工作\chan_quant")

import pandas as pd

from chan_quant.models import train

H = 24
df = train.load(sys.argv[1] if len(sys.argv) > 1 else "events_v0")
print("events", len(df), "span", df["event_time"].min(), "~", df["event_time"].max())
print("base dir_ret_24 mean %.4f  win %.3f" % (df["dir_ret_24"].mean(), (df["dir_ret_24"] > 0).mean()))

groups = [("ALL", df)]
for side, name in ((1, "BUY"), (0, "SELL")):
    groups.append((name, df[df["is_buy"] == side]))
for t in ("1", "2", "2s", "3a"):
    sub = df[df["bsp_type"].str.split(",").apply(lambda xs: t in xs)]
    if len(sub) >= 150:
        groups.append((f"BUY_{t}", sub[sub["is_buy"] == 1]))
        groups.append((f"SELL_{t}", sub[sub["is_buy"] == 0]))

rows = []
for tag, sub in groups:
    if len(sub) < 80:
        continue
    out, bst = train.run_group(sub, h=H, label_col="dir_ret", tag=tag)
    rows.append(out)
    print(f"{tag:10s} n={out['n']:5d} auc_val={out.get('auc_valid', float('nan')):.3f} "
          f"auc_test={out.get('auc_test', float('nan')):.3f} "
          f"type_only={out.get('auc_valid_type_only', float('nan')):.3f} "
          f"base={out.get('base_rate', float('nan')):.3f}")

print()
print(train.report(rows).to_string(index=False))
