# 一次性冒烟：bg_ 背景特征（执行后可删）
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'D:\工作\chan_quant\scripts')
import _path  # noqa
from chan_quant.core import replay
import numpy as np

events, el = replay.replay('sh.600000')
print(f'events={len(events)} elapsed={el:.1f}s')
bg_keys = sorted(k for k in events[0].features if k.startswith('bg_'))
print(f'bg keys ({len(bg_keys)}):', ' '.join(bg_keys))
arr = {k: np.array([e.features[k] for e in events]) for k in bg_keys}
for k in bg_keys:
    v = arr[k]
    print(f'  {k:16s} min={v.min():8.3f} med={np.median(v):8.3f} max={v.max():8.3f} nonzero={np.mean(v != 0):.2f}')
