import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from chan_quant.models import train
from train_wf import evaluate, run

# 稀有阳性标签（1.9%）：解除 min_child_weight=20 瘫痪 + 类别加权
train.XGB_PARAMS.update({"min_child_weight": 2, "scale_pos_weight": 52.0})

d = run("events_v8_tail", "wf_tail30", "tail_30", "conf_buy",
        min_train=500, min_pos=0.005, thr=0.0, window_months=12)
if d is not None:
    evaluate(d, "tail_30", 0.0)
