"""批量抓取 30 分钟线到本地 parquet。支持断点续跑。"""
import argparse
import sys
import time
import traceback

sys.path.insert(0, r"D:\工作\chan_quant")

from chan_quant.data import fetch, store


def hs300_codes() -> list[str]:
    fetch.login()
    try:
        bs = fetch._bs()
        rs = bs.query_hs300_stocks()
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        # 字段: updateDate, code, code_name
        return [r[1] for r in rows]
    finally:
        fetch.logout()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--codes", default="")
    args = ap.parse_args()

    codes = args.codes.split(",") if args.codes else hs300_codes()
    if args.limit:
        codes = codes[: args.limit]
    print(f"universe={len(codes)}", flush=True)

    fetch.login()
    ok = skip = fail = 0
    t0 = time.time()
    try:
        for i, code in enumerate(codes, 1):
            if store.has(code, "30m"):
                skip += 1
                continue
            try:
                df = fetch.fetch_30m(code, args.start, args.end)
                if len(df) < 500:
                    print(f"[{i}/{len(codes)}] {code} 数据不足 {len(df)}", flush=True)
                    fail += 1
                    continue
                store.save(code, df, "30m")
                ok += 1
                print(f"[{i}/{len(codes)}] {code} bars={len(df)}", flush=True)
            except Exception as e:
                fail += 1
                print(f"[{i}/{len(codes)}] {code} FAIL {type(e).__name__}: {e}", flush=True)
            if i % 50 == 0:
                el = time.time() - t0
                print(f"--- progress {i}/{len(codes)} ok={ok} skip={skip} fail={fail} {el/60:.1f}min", flush=True)
    finally:
        fetch.logout()
    print(f"DONE ok={ok} skip={skip} fail={fail} elapsed={(time.time()-t0)/60:.1f}min", flush=True)


if __name__ == "__main__":
    main()
