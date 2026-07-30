# M2 Stage 2A 工作记录：最小透明指标底座

## 启动基线

- Branch：`feat/m2-value-assessment-mvp`
- HEAD：`5b79028e6cbfff2c9540dd852aa75b0b084ce4c2`
- Worktree：clean
- `stash@{0}` 保持不动。
- Stage 1D-B：PASS；57 facts、最终 PIT 15、重列版本链可信。
- 默认数据库启动 SHA-256：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## 开始前审查

- 仓库不存在 `AGENTS.md`。
- 既有 DerivationEngine 明确不实现 YoY、CAGR 或评分指标。
- 2022 归母净利润与 2023 三项 reconciled facts 存在 v2；2025 为
  `not_yet_reviewable`。
- 本阶段无需且不得修改 Fact Schema、FactIdentity、AsOfQuery、
  VersionChainValidator、Reconciliation、Derivation 或重列工具。

## 第一部分：独立 Metric 层

- 新建独立 `metrics` 包，包含版本化定义、Decimal-only 引擎、canonical
  SHA-256 身份和事务化 MetricRepository。
- 四个 canonical value 均以 ratio 表示，Decimal precision 28，
  量化 `0.000000000001`，ROUND_HALF_EVEN。
- Metric Schema 1.0 独立于 Fact Schema，value 使用
  `DECIMAL(38,12)`。
- Repository 支持 canonical 校验、语义冲突、幂等、严格版本链和批量
  事务回滚。

## 第二部分：PIT Metric 集成

- 新增 `official_fact_metric_foundation.py`，先调用未修改的 Stage 1D-B
  runner，再核验 upstream 57 facts / 最终 Fact PIT 15。
- 唯一 Fact `available_at` 只用于安排 snapshot；指标输入全部来自
  `AsOfQuery.get_latest_available()`，未直接挑选全版本事实。
- 全部结果在内存中完成后一次事务写入独立 `metrics.duckdb`；上游
  restatement DuckDB 读取前后 SHA-256 完全一致。
- 最终真实 run：
  `metric_foundation_601857_SH_2021_2025_20260730_120052_376281`。
- 实际计数：definitions 4、result versions 26、computed 23、
  insufficient history 3、version links 6、lineage 49；最终 latest
  20，其中 computed 17、insufficient history 3。
- Metric PIT：`0 / 4 / 8 / 12 / 16 / 20`；computed：
  `0 / 1 / 5 / 9 / 13 / 17`。
- 真实输入自然产生 2022 两条和 2023 四条 Metric v2；2024 三个 YoY
  首次出现即使用 2023 reconciled v2。
- 2025 四个指标均可计算，`revision_review_status` 为
  `not_yet_reviewable`。
