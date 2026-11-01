"""顺序抓取 30 分钟线，断点续跑。

⚠️ baostock 官方规则：禁止多连接（多线程/多进程）。本脚本因此：
   1. 只跑一个进程、一个会话；
   2. 用锁文件阻止同时启动第二个实例；
   3. 每只股票之间默认休眠 0.6 秒。
"""
import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
socket.setdefaulttimeout(30)

from chan_quant.data import fetch, store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "data" / "fetch.lock"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock():
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text().strip() or 0)
        except ValueError:
            pid = 0
        if pid and _alive(pid):
            raise SystemExit(f"已有抓取进程在运行 (pid={pid})；baostock 禁止多连接，请先等待其结束")
    LOCK.write_text(str(os.getpid()))


def release_lock():
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass


def universe() -> list[str]:
    p = ROOT / "data" / "universe" / "hs300.json"
    if p.exists():
        return json.loads(p.read_text())
    fetch.login()
    try:
        rs = fetch._bs().query_hs300_stocks()
        return [r[1] for r in fetch._drain(rs)]
    finally:
        fetch.logout()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--codes", default="")
    ap.add_argument("--sleep", type=float, default=0.6, help="每只股票之间的休眠秒数")
    args = ap.parse_args()

    acquire_lock()
    try:
        codes = args.codes.split(",") if args.codes else universe()
        todo = [c for c in codes if not store.has(c, "30m")]
        print(f"universe={len(codes)} todo={len(todo)}", flush=True)

        ok = fail = 0
        t0 = time.time()
        logged = False
        for i, code in enumerate(todo, 1):
            for attempt in range(2):
                try:
                    if not logged:
                        fetch.login()
                        logged = True
                    df = fetch.fetch_30m(code, args.start, args.end)
                    if len(df) < 500:
                        print(f"[{i}/{len(todo)}] {code} short={len(df)}", flush=True)
                        fail += 1
                        break
                    store.save(code, df, "30m")
                    ok += 1
                    print(f"[{i}/{len(todo)}] {code} {len(df)}", flush=True)
                    break
                except Exception as e:
                    logged = False
                    if attempt == 1:
                        fail += 1
                        print(f"[{i}/{len(todo)}] {code} FAIL {type(e).__name__}", flush=True)
                    else:
                        time.sleep(2)
            time.sleep(args.sleep)
            if i % 20 == 0:
                print(f"--- {i}/{len(todo)} ok={ok} fail={fail} {(time.time()-t0)/60:.1f}min",
                      flush=True)

        fetch.logout()
        print(f"DONE ok={ok} fail={fail} {(time.time()-t0)/60:.1f}min", flush=True)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
