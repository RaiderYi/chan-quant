# chan-quant

**缠论（chan.py）× Brooks 价格行为 × 机器学习的 A 股 30 分钟策略研究流水线。**

可复现的结构计算、因果特征、三层标签、样本内/样本外切分与逐 bar 组合回测。
这个仓库记录的是**证据链**：哪些假设被证伪、哪些被修正、哪些在样本外还站得住。

> 数据：HS300 成分股，30 分钟 2020-01 ~ 2026-10 + 日线 2010-01 ~ 2026-10，前复权（baostock）
> 样本：289 股 30m / 47,307 个 BSP 事件 / 8,646 个确认买点 / 188 列固定特征；297 股日线 / 15,422 事件
> 框架：chan.py `f8ca3b5`（2026-10-28）

## 最终结论（2026-11-01，研究线收尾）

**一句话：入场时刻，缠论结构能预测的只有结构本身（BSP 存活）；收益由外部资金流（妖股狂潮）决定，入场时无签名；策略账面正期望 100% 来自极少数尾部交易。**

| 问题 | 答案 | 证据 |
|---|---|---|
| 裸 BSP 买点有 alpha 吗 | **没有** | -6.0bp/笔，t=-2.5 |
| 加工后（确认+144bar/3ATR）有正期望吗 | **账面上有** | E=+42.6bp/笔，样本内夏普 0.63 / 样本外 0.80 |
| 这个期望可复制吗 | **不能——全在尾部** | 去 top1% 赢家 E 变 -9.5bp，去 top5% 变 -115bp；中位交易 -242bp；4 个狂潮月（2020-06/07、2024-09/10）= 4% 交易贡献 81% 盈亏 |
| ML 能预测"赚不赚"吗 | **不能（5 次独立阴性）** | 方向/大波/卖点/对齐收益/动力学增强，AUC ≤0.51-0.55，高低分位反序 |
| ML 能预测什么 | **BSP 存活（第 6 次，唯一阳性）** | 存活标签 AUC 买 0.658/卖 0.689，**67 个月 100% ≥0.55**；缠论结构特征驱动 41%——结构预测结构 |
| 存活过滤能赚钱吗 | **事件级能，组合级不能** | 事件级 top10% E 31.7→60.2bp 单调；但 10 仓位组合 +13.4%/夏普 0.21 反而低于基线 +46.8%/0.44——高分事件时间聚集，狂潮期仓位满被跳过的 484 笔 E=+75.1bp |
| 跨周期/regime 稳健吗 | **不死，但盈亏全看牛市年** | 日线 2010-2026：2015 股灾年 +47bp、2018 熊 -297bp 有界、2014 大牛 +4009bp；去 top5% 赢家 E 转负——尾部依赖跨周期不变 |

### 策略的真实面貌

确认买点全做 + 144bar/3ATR + 无信号离场，本质是**"BSP 发行彩票"**：
胜率 24%、盈亏比 3.70、平时持续小亏（中位 -242bp），收益来自妖股爆炸的罕见窗口（与大盘同期收益相关 -0.014，非 beta）。
唯一被验证有效的外部信号是 **regime 而非个股形态**：狂热指数（样本股日涨幅>9.5% 占比）≥中位时 E=85.5bp vs 低迷期 39.7bp。

### 历史记录：结论被推翻过三次

1. 110 股"确认入场 +12.73%/夏普 0.24" → 240 股复核变 -10.34%；
2. v2"样本内外夏普 0.63/0.80 站得住" → Phase A 去尾测试揭底：期望全在尾部，不可复制；
3. ML 路线 5 次阴性 → 第 6 次换成结构标签（存活）转阳性，但组合级验证再次否定其交易价值。

全部过程保留在 `reports/` 与 `reports/experiment_log.md`（18 条编号实验台账）。

## 系统架构

```
baostock 30m/d ──► parquet 缓存 ──► chan.py 逐 bar 回放 ──► BSP 首次出现事件
                                                              │
                        ┌─────────────────────────────────────┤
                        ▼                                     ▼  存活追踪（clear_bar）
               188 列特征（t 时点因果计算）            标签（t 之后，物理隔离）
              · pa_  价格行为 54                · ret/dir_ret/mfe/mae/stop（H=8/24/48）
              · pt_  形态 15                    · pol_* 策略一致性（止损+时间退出）
               · ch_  缠论 54                    · conf_* 确认入场口径
               · dy_  动力学 34（MACD 6 算法/RSI/   · survive_144 BSP 存活
                      量能/中枢突破/特征序列）
               · mkt_ 市场 8
               · sw_/rg_/bc_/bsw_/ff_/rf_/wg_   Brooks 结构 23
                        │
                        ▼
        按月 walk-forward 训练（扩张/滑动窗口，训练集截止月初-10天）
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
  core/  replay.py policy.py 逐 bar 回放（含 BSP 存活追踪）/ 唯一一份退出规则模拟
  features/  indicators pa patterns brooks chan_ctx dynamics market build schema
  labels/  label.py confirm.py  前向标签 / 确认入场
  eval/  metrics.py bars.py     AUC·bootstrap CI·lift·期望值 / 行情加载
  models/train.py            特征列与 XGBoost 训练
  backtest/portfolio.py      逐 bar 盯市组合回测
scripts/
  setup_framework.py         拉取 chan.py 固定版本并安装数据源适配器
  fetch.py                   抓 HS300（断点续跑、单进程、限速；--freq d 日线）
  build_market.py            等权市场序列（--freq 任意周期）
  build_dataset.py           事件 + 特征 + 标签 -> parquet
  make_v6_label.py           pol144 真实交易标签（参数化版本/周期）
  make_v7_survival.py        BSP 存活标签（clear_bar → survive_144，删失处理）
  tail_test.py tail_analysis.py tail_regime.py frenzy_gate.py  Phase A 去尾与 regime 检验
  daily_regime.py            日线分年度/regime 压力测试
  survival_money.py          存活模型的钱验证（事件级 + 组合级）
  train_wf.py                月度 walk-forward（扩张/滑动窗口）
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

### 机器学习（6 次 walk-forward，12 个月滑动窗口）

| 实验 | 子集 | 标签 | OOF AUC | 结论 |
|---|---|---|---:|---|
| WF-1/2 | 全部/确认买点 | 方向 | 0.49–0.51 | 阴性 |
| WF-3 | 确认买点 | 24bar 大波 >2% | 0.55–0.57 | 阴性（与 144bar 收益反相关） |
| WF-4 | 卖点 | 大跌/方向 | 0.50–0.57 | 阴性 |
| WF-5 | 确认买点 | 对齐真实交易收益（pol144） | 0.507–0.509 | 阴性（+34 动力学特征后仍 0.5073） |
| **WF-6** | **全部事件** | **BSP 存活 144bar** | **0.658（买）/0.689（卖）** | **唯一阳性：67 个月 100% ≥0.55** |

规律：**概率可学、赔率不可学**；同构标签（结构→结构）可学，外生标签（结构→资金流）不可学。
存活过滤在事件级单调有效（top10% E 31.7→60.2bp），但在 10 仓位组合回测中反而降低收益
（狂潮期仓位满，被跳过事件的期望是被采纳者的 2 倍）。

## 报告

- [实验台账](reports/experiment_log.md) ← **18 条编号实验的完整证据链（先读这个）**
- [Phase A 去尾测试](reports/phase_a_tail_report.md)（期望的尾部结构、狂潮月、regime 门控）
- [策略 v2：出场规则才是主要矛盾](reports/strategy_v2_report.md)（后被 Phase A 修正解读）
- [策略结果 v1](reports/strategy_v1_report.md)（110 股口径，已被推翻，文首有说明）
- [特征与标签目录](reports/feature_label_catalog.md)（特征 / 标签的完整定义）
- [特征有效性](reports/feature_effectiveness.md)（消融、冗余、重要性、稳定性）

## 限制

- 股票池是**当前** HS300 成分，存在幸存者偏差；退市与调出成分股不在样本内。
- 30 分钟数据起点 2020-01（baostock 覆盖限制）；日线已覆盖 2010-01 起（297 股），
  16 年 regime 压力测试见台账实验 #16。
- 前复权未做逐区间 point-in-time 校验。
- 成本统一按往返 13bp，未区分冲击成本；停牌按下一可交易 bar 成交。
- 结论对小样本敏感：110 股与 240 股曾给出相反的确认入场结果，仓库保留两次记录。

## 路线图（研究线已收尾，剩余开放项）

1. ~~300 股全量重跑~~（已完成 v4/v7）；~~滑动窗口训练~~（12m 已定为生产口径）。
2. ~~ML 信号生成~~（5 次阴性证伪）；~~存活模型~~（阳性但组合级无效，见台账 #17/#18）。
3. 开放：frenzy regime 门控的组合级验证（低迷期关机/狂潮期满仓，与"暴露最大化"发现自洽）。
4. 开放：ML 用作仓位映射/横截面排序而非二分类过滤（尚未试）。
5. 开放：供给端特征（相对强弱、板块排名、事件密度）——但按台账证据，入场端信息的
   预期边际收益已很低。

## 许可与致谢

- 本项目：MIT（见 `LICENSE`）。
- 结构引擎：[Vespa314/chan.py](https://github.com/Vespa314/chan.py)（MIT, Memos 2022），
  按固定 commit 拉取、不随仓库分发。
- Brooks 结构实现参考：[RaiderYi/price-action-lab](https://github.com/RaiderYi/price-action-lab)（MIT）。
- 数据：[baostock](http://baostock.com)。

详见 `ATTRIBUTION.md`。
