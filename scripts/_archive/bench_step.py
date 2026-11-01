"""基准测试：chan.py step_load 逐bar回放的耗时（合成3000根日线）。"""
import sys, os, time
repo = r"D:\工作\chan_quant\framework"
sys.path.insert(0, repo); os.chdir(repo)
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

code = "SYN1"
src = r"D:\工作\chan_compare\fork\SYN1_day.csv"
dst = os.path.join(repo, f"{code}_day.csv")
with open(src) as f, open(dst, "w") as g:
    g.write(f.read())

conf = CChanConfig({"trigger_step": True, "print_warning": False, "bi_strict": True,
                    "bs_type": "1,2,3a,1p,2s,3b"})
t0 = time.time()
chan = CChan(code=code, data_src=DATA_SRC.CSV, lv_list=[KL_TYPE.K_DAY], config=conf, autype=AUTYPE.QFQ)
n = 0; nb = 0
for snap in chan.step_load():
    n += 1
    lv = snap[0]
    nb = len(lv.bi_list)
t1 = time.time()
print(f"bars={n} last_bi={nb} elapsed={t1-t0:.2f}s  per_bar={(t1-t0)/max(n,1)*1000:.1f}ms")
