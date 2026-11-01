"""并行抓取 30 分钟线（多进程，每进程独立 baostock 会话）。"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, r"D:\工作\chan_quant")


def _init():
    from chan_quant.data import fetch
    fetch.login()


def _work(code, start, end):
    from chan_quant.data import fetch, store
    if store.has(code, "30m"):
        return code, 0, "skip"
    try:
        df = fetch.fetch_30m(code, start, end)
        if len(df) < 500:
            return code, len(df), "short"
        store.save(code, df, "30m")
        return code, len(df), "ok"
    except Exception as e:
        return code, 0, f"fail:{type(e).__name__}:{e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--codes", default="")
    args = ap.parse_args()

    from chan_quant.data import fetch
    if args.codes:
        codes = args.codes.split(",")
    else:
        fetch.login()
        try:
            bs = fetch._bs()
            rs = bs.query_hs300_stocks()
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            codes = [r[1] for r in rows]
        finally:
            fetch.logout()
    print(f"universe={len(codes)} workers={args.workers}", flush=True)

    t0 = time.time()
    ok = skip = fail = 0
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as ex:
        futs = {ex.submit(_work, c, args.start, args.end): c for c in codes}
        for i, fut in enumerate(as_completed(futs), 1):
            code, n, st = fut.result()
            if st == "ok":
                ok += 1
            elif st == "skip":
                skip += 1
            else:
                fail += 1
                print(f"  {code} {st} n={n}", flush=True)
            if i % 25 == 0:
                print(f"--- {i}/{len(codes)} ok={ok} skip={skip} fail={fail} "
                      f"{(time.time()-t0)/60:.1f}min", flush=True)
    print(f"DONE ok={ok} skip={skip} fail={fail} elapsed={(time.time()-t0)/60:.1f}min", flush=True)


if __name__ == "__main__":
    main()
