# _archive —— 已废弃/已合并的脚本（不参与运行）

保留原因：记录当时的分析口径，便于回溯；**不要直接运行**。

| 脚本 | 去向 |
|---|---|
| `bench_step.py` | 一次性性能测试，结论已进 README |
| `smoke_replay.py` | 已由 `scripts/build_dataset.py --limited` 覆盖 |
| `train_v0.py` | 已由 `scripts/train_wf.py` 取代 |
| `label_probe.py` | 标签探针结论已写入 `reports/feature_effectiveness.md` |
| `feature_health.py` | 合并进 `scripts/analyze_features.py` |
| `feature_selection.py` | 合并进 `scripts/analyze_features.py` |
| `exit_grid.py` | 合并进 `scripts/baseline.py` |
| `confirm_eval.py` | 合并进 `scripts/baseline.py` |
| `baseline_report.py` | 合并进 `scripts/baseline.py` |

## ⚠️ 禁用：`fetch_universe.py` / `fetch_parallel.py`

baostock 官方（2026-06-16）明确：**禁止多连接（多线程或多进程）访问**，后续会严格限制。
这两个脚本用进程池并发登录，实测会导致会话互相踢掉（返回空数据 `short=0`），
现仅留档，**不得再运行**。抓数统一用 `scripts/fetch.py`（单进程 + 锁文件 + 限速）。
