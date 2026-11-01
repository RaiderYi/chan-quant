"""组合回测：基线 / 确认入场 / ML 过滤，三种口径对比。"""
import argparse
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import pandas as pd

from chan_quant.backtest import portfolio
from chan_quant.config import DATA
from chan_quant.eval.bars import load_frames
from chan_quant.eval.metrics import expectancy
from chan_quant.models import train


def show(tag, res, save_as: str | None = None):
    m = res["metrics"]
    print(f"\n== {tag} ==")
    print(f"  区间: {res['equity'].index.min()} ~ {res['equity'].index.max()}  bars={m.get('bars')}")
    print(f"  累计 {m.get('total_ret', 0)*100:.2f}%  年化 {m.get('cagr', 0)*100:.2f}%  "
          f"夏普 {m.get('sharpe', 0):.2f}  最大回撤 {m.get('mdd', 0)*100:.2f}%")
    print(f"  交易 {m.get('n_trades')} 笔  胜率 {m.get('win_rate', 0)*100:.1f}%  "
          f"均值 {m.get('avg_ret', 0)*1e4:.1f}bp  盈亏比 "
          f"{abs(m.get('avg_win', 0)/m.get('avg_loss', 1e-9)):.2f}  平均持仓 {m.get('avg_bars', 0):.1f} bar")
    tr = res["trades"]
    if not tr.empty:
        print(tr.groupby("reason")["ret"].agg(["count", "mean"]).round(4).to_string())
        e = expectancy(tr["ret"])
        print(f"  期望 {e['expectancy_bp']:.1f}bp/笔  盈亏平衡 R*={e['breakeven_R']:.2f}  "
              f"实际 R={e['payoff_R']:.2f}  Kelly={e['kelly']*100:.2f}%  "
              f"前5%交易占总盈利 {e['top5pct_profit_share']*100:.0f}%")
    if save_as:
        d = DATA / "bt"
        d.mkdir(parents=True, exist_ok=True)
        res["trades"].to_parquet(d / f"{save_as}_trades.parquet", index=False)
        res["equity"].to_parquet(d / f"{save_as}_equity.parquet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="events_v2")
    ap.add_argument("--mode", default="signal", choices=["signal", "confirm"])
    ap.add_argument("--pos", type=float, default=0.10)
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--stop", type=float, default=1.5)
    ap.add_argument("--hold", type=int, default=48)
    ap.add_argument("--score", default="", help="wf parquet，提供 score 列")
    ap.add_argument("--quantile", type=float, default=0.0, help="只交易分数前 q 分位")
    ap.add_argument("--tag", default="")
    ap.add_argument("--no-signal-exit", action="store_true")
    args = ap.parse_args()

    df = train.load(args.name)
    if args.score:
        sc = pd.read_parquet(args.score)
        sc = sc.rename(columns={"event_time": "event_time"})
        df = df.merge(sc[["code", "event_time", "score"]], on=["code", "event_time"], how="inner")
        if args.quantile > 0:
            thr = df.groupby("is_buy")["score"].transform(lambda s: s.quantile(1 - args.quantile))
            df = df[df["score"] >= thr]
        print(f"after score filter: {len(df)} events")
    bars = load_frames(df.code.unique())
    p = portfolio.BtParams(pos_pct=args.pos, max_pos=args.max, stop_atr=args.stop, hold_bars=args.hold,
                           signal_exit=not args.no_signal_exit)
    res = portfolio.run(df, bars, p, entry_mode=args.mode)
    tag = args.tag or f"{args.name}/{args.mode}/stop{args.stop}/hold{args.hold}"
    show(tag, res, save_as=tag.replace("/", "_").replace(" ", "_"))


if __name__ == "__main__":
    main()
