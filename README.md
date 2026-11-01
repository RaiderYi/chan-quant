# chan-quant

**缠论（chan.py）× Brooks 价格行为 × 机器学习的 A 股 30 分钟策略研究流水线。**

可复现的结构计算、因果特征、三层标签、按月 walk-forward 与逐 bar 组合回测——以及到目前为止
**全部为负或接近零的实验结果**。这个仓库的价值不在"策略能赚钱"，而在"每个结论都能被推翻并被证据记录"。

> 数据：HS300 成分股，30 分钟，2020-01 ~ 2026-10，前复权（baostock）
> 样本：240 股 / 34,149 个 BSP 事件 / 6,169 个确认买点 / 154 列固定特征
> 框架：chan.py `f8ca3b5`（2026-10-28）

## 当前结论（2026-11-01）

| 问题 | 答案 | 证据 |
|---|---|---|
| 裸 BSP 买点有 alpha 吗 | **没有** | 19,625 个买点，持有 24 bar，-6.0bp/笔，t=-2.5 |
| 裸 BSP 卖点有信息吗 | **有，方向性为正** | 14,524 个卖点，+14.8bp/笔，t=5.7（A股无法直接做空） |
| 确认入场（突破信号 bar 高点）能救吗 | **小样本能，全样本不能** | 110 股：+12.7%、夏普 0.24；240 股：**-10.3%、夏普 -0.03** |
| ML 能预测"这笔赚不赚"吗 | **不能** | 正收益标签 AUC 0.49–0.53 |
| ML 能预测"会不会有大波"吗 | **能，但不变现** | >2% 标签 OOF AUC 0.56；高分位组合仍不赚钱 |
| 特征该保留多少列 | **25 列足够** | 25 列 vs 131 列：AUC 0.6142 vs 0.6059（110 股口径） |

最近一轮（240 股、6,169 确认买点）的复核**推翻了 110 股时的乐观结论**：

| 口径 | 110 股 | 240 股 |
|---|---:|---:|
| 确认入场组合累计收益 | +12.73% | **-10.34%** |
| 夏普 | 0.24 | -0.03 |
| 单笔均值 | +5.7bp | -1.0bp |
| 大波标签 AUC | 0.60 | 0.569 |

样本翻倍后收益消失——说明此前那个 +20bp 是样本内运气，不是可复现的边际。

## 系统架构

```
baostock 30m ──► parquet 缓存 ──► chan.py 逐 bar 回放 ──► BSP 首次出现事件
                                                              │
                        ┌─────────────────────────────────────┤
                        ▼                                     ▼
              154 列特征（t 时点因果计算）            标签（t 之后，物理隔离）
              · pa_  价格行为 54                · ret/dir_ret/mfe/mae/stop（H=8/24/48）
              · pt_  形态 15                    · pol_* 策略一致性（止损+时间退出）
              · ch_  缠论 54                    · conf_* 确认入场口径
              · mkt_ 市场 8
              · sw_/rg_/bc_/bsw_/ff_/rf_/wg_   Brooks 结构 23
                        │
                        ▼
        按月 walk-forward 训练（训练集截止到月初-10天）
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
   AUC / 分位 lift   组合回测        特征体检
                  （逐 bar 盯市）   （消融/冗余/重要性）
```

## 目录

```
chan_quant/
  config.py                 路径与 chan.py 参数基线（贴官方默认）
  data/  store.py fetch.py  parquet 缓存 / baostock 抓取（单连接限速）
  core/  replay.py policy.py 逐 bar 回放 / 唯一一份退出规则模拟
  features/  indicators pa patterns brooks chan_ctx market build schema
  labels/  label.py confirm.py  前向标签 / 确认入场
  eval/  metrics.py bars.py     AUC·bootstrap CI·lift / 行情加载
  models/train.py            特征列与 XGBoost 训练
  backtest/portfolio.py      逐 bar 盯市组合回测
scripts/
  setup_framework.py         拉取 chan.py 固定版本并安装数据源适配器
  fetch.py                   抓 HS300 30m（断点续跑、单进程、限速）
  build_market.py            等权市场序列
  build_dataset.py           事件 + 特征 + 标签 -> parquet
  baseline.py                事件研究：类型/年份/退出网格/确认入场
  analyze_features.py        特征体检：消融/冗余/重要性/稳定性
  train_wf.py                月度 walk-forward
  run_backtest.py            组合回测（信号/确认/ML 过滤）
  test_prefix_invariance.py  泄漏检验
reports/                     研究报告与特征体检 CSV
vendor/LocalStore.py         chan.py 的本地 parquet 数据源适配器
```

## 快速开始

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
python scripts/setup_framework.py                          # 拉取 chan.py f8ca3b5

python scripts/fetch.py                                    # 抓数（首次约 2 小时，可断点续跑）
python scripts/build_market.py                             # 等权市场序列
python scripts/build_dataset.py --name events_v3           # 事件 + 特征 + 标签
python scripts/baseline.py --name events_v3                # 无模型基线
python scripts/analyze_features.py events_v3               # 特征体检
python scripts/train_wf.py events_v3 wf_v3 c_pol_dir_ret conf_buy 1200 0.02
python scripts/run_backtest.py --name events_v3 --mode confirm --stop 1.5 --hold 48
```

数据与第三方代码不进仓库：`data/`、`framework/`、`refs/` 均在 `.gitignore` 中。

## 数据源规则（必须遵守）

baostock 官方（2026-06-16）明确**禁止多连接（多线程/多进程）访问**。仓库的做法：

1. `scripts/fetch.py` 单进程单会话，进程内哨兵防止重复登录；
2. 启动写 `data/fetch.lock`，第二个实例直接拒绝；
3. 每股间隔 0.6s，每 100 页暂停 0.05s。

并发抓取实测会导致会话互踢、返回空数据；本仓库已不提供任何并发抓取脚本。

## 设计约定

1. **因果优先**：特征只在 bar `t` 现场计算；BSP 只记首次出现；`test_prefix_invariance.py`
   把序列截断到 3k/6k/9k 根重跑，`t` 之前事件的特征必须逐位一致（当前 0 mismatch）。
2. **固定 schema**：`features/schema.py` 首跑落盘列名，之后增删列直接报错，禁止出现
   按价格动态生成的特征列。
3. **标签与特征物理分离**：标签可以用未来数据，特征不行；两套入场口径（信号次 bar / 确认后次 bar）
   各自独立成列。
4. **单一事实源**：退出规则只有 `core/policy.simulate_exit` 一份；指标只有 `eval/metrics`；
   数据加载只有 `data/store` 与 `eval/bars`。
5. **组合级回测**：逐 bar 盯市，单笔 10% 仓位、最多 10 仓；禁止用事件级收益连乘代替。

## 实验设计与结果

### 基线（34,149 事件，信号次 bar 开盘入场，24 bar）

| 分组 | n | 均值 | t |
|---|---:|---:|---:|
| BUY 全部 | 19,625 | -6.0bp | -2.5 |
| BUY T1 | 5,412 | -11.8bp | -2.7 |
| BUY T1p | 2,235 | +3.8bp | 0.6 |
| SELL 全部 | 14,524 | +14.8bp | 5.7 |

### 退出网格（全体事件）

| 持有 | 止损 | 均值 | t |
|---:|---:|---:|---:|
| 24 | 1.5×ATR | +4.4bp | 2.7 |
| 8 | 1.0×ATR | +1.6bp | 1.7 |
| 24 | 3.0×ATR | +1.0bp | 0.5 |

低胜率（24–30%）+ 高盈亏比（约 3:1）的结构；正的均值主要来自卖点方向。

### 机器学习

| 实验 | 子集 | 标签 | OOF AUC |
|---|---|---|---:|
| WF-1 | 全部事件 | 策略一致性收益 > 0 | 0.49（买） |
| WF-2 | 确认买点 | 策略一致性收益 > 0 | 0.50 |
| WF-3 | 确认买点 | 策略一致性收益 > 2% | **0.561** |
| WF-4 | 确认买点 | `pa_atr_pct` 等波动特征 | 单变量 0.59 |

能识别"大波"，不能识别"盈利"；且大波评分前 20% 组合仍为负。

## 报告

- [策略结果 v1](reports/strategy_v1_report.md)（110 股口径，结论已被 240 股复核部分推翻，文首有说明）
- [特征与标签目录](reports/feature_label_catalog.md)（154 个特征 / 32 个标签的完整定义）
- [特征有效性](reports/feature_effectiveness.md)（消融、冗余、重要性、稳定性）

## 限制

- 股票池是**当前** HS300 成分，存在幸存者偏差；退市与调出成分股不在样本内。
- 30 分钟数据起点 2020-01（baostock 覆盖限制），不含 2015–2019。
- 前复权未做逐区间 point-in-time 校验。
- 成本统一按往返 13bp，未区分冲击成本；停牌按下一可交易 bar 成交。
- 结论对小样本敏感：110 股与 240 股给出了相反的确认入场结果，仓库保留两次记录。

## 路线图

1. 300 股全量重跑，锁定样本外 2026 年。
2. 标签改造：对市场超额收益 / R 倍数，替代绝对收益。
3. 决策改造：把 ML 从"二分类过滤"改成"仓位映射"+"横截面排序"。
4. 供给端特征：相对强弱、板块排名、日内时段、事件密度。
5. 实盘层：三层资格框架（bar counting → 资格 → 可执行性）与 regime 滞后标签。

## 许可与致谢

- 本项目：MIT（见 `LICENSE`）。
- 结构引擎：[Vespa314/chan.py](https://github.com/Vespa314/chan.py)（MIT, Memos 2022），
  按固定 commit 拉取、不随仓库分发。
- Brooks 结构实现参考：[RaiderYi/price-action-lab](https://github.com/RaiderYi/price-action-lab)（MIT）。
- 数据：[baostock](http://baostock.com)。

详见 `ATTRIBUTION.md`。
