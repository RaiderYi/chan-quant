# 第三方组件与数据来源

本项目在以下开源工作之上构建，谨致谢意。

## chan.py（缠论结构引擎）

- 仓库：https://github.com/Vespa314/chan.py
- 版本：`f8ca3b5e44d7166e2abd756a8e7fa816c79faebe`（2026-10-28）
- 许可：MIT License, Copyright (c) 2022 Memos
- 使用方式：**不随本仓库分发**。`scripts/setup_framework.py` 按固定 commit 拉取到 `framework/`，
  再把本仓库的 `vendor/LocalStore.py`（本地 parquet 数据源适配器）复制进去。
- 本项目对 chan.py 的使用：调用其 `CChan` / `step_load` / `CChanConfig` 等公开接口，
  未修改其算法逻辑；唯一新增文件是 `DataAPI/LocalStore.py`。

## price-action-lab（Brooks 结构实现与知识库）

- 仓库：https://github.com/RaiderYi/price-action-lab
- 许可：MIT License, Copyright (c) 2026 RaiderYi
- 使用方式：**不随本仓库分发**。`chan_quant/features/brooks.py` 参考其
  `pal/context/swings.py`（右侧确认摆动点）、`pal/context/regime.py`（环境标签）、
  `bar_counting_detector.py`（H1/H2 计数）、`pal/signals/breakout.py`（突破强度）的实现思路，
  改写为 numpy 数组上的纯函数（不引入其数据模型与依赖）。
  其 `knowledge/concepts/` 下的 241 个 Brooks 概念页是后续特征设计的参考资料。

## 行情数据

- 来源：**baostock**（http://baostock.com），30 分钟线，前复权（adjustflag=2）。
- 约束：baostock 官方明确**禁止多连接（多线程/多进程）访问**。本仓库的数据抓取脚本
  `scripts/fetch.py` 实现了单进程 + 锁文件 + 限速，请勿改写为并发。
- 数据本身不随仓库分发，首次使用需自行抓取（见 README 快速开始）。
