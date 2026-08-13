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

## 最终门禁

- Metric unit/repository/integration：`31 passed`。
- Stage 1D-B regression：`30 passed`。
- Multi-year regression：`19 passed`。
- Reconciliation regression：`92 passed`。
- Full pytest：`562 passed, 2 warnings`；warning 为既有 pandas 日期解析
  warning。
- Ruff 0.13.2、compileall、四模块 import、`git diff --check`：通过。

## 不变性

- 五个 annual bundle blob：
  `cb85f84c3a1459f3a909e36bd6482c8d8124d1a4`、
  `7076195f3532ead9f0278f97691fe552fdb2ff54`、
  `6612148ea91b2004605b98e0c8fe799a4d2686ea`、
  `03a2ec2813c31676aebed20e4df50042f42f140b`、
  `0ababb5262e6cbf1646e165ccfb3e7bfe2769670`。
- 四个 restatement evidence blob：
  `65e25075b91d3d1d15a7761571cca18e931a9f8b`、
  `e141a0c4b45994ee7d331d9af874ab0c1d8e20ac`、
  `62d8e20cc728b7def157e4fb781918cf12d09e21`、
  `8127b566849c811b04f69a180205d0be592738e6`。
- Stage 1D-B 基线和 Stage 2A upstream 的 57 Fact ID 集合逐一相等；
  排序集合 SHA-256：
  `e2afd5d39ae97f2488f5e9a713fda578174c38c5ea13e37d12e8844a8f29d829`。
- Fact、PIT、Reconciliation、Derivation、Stage 1D-A/1D-B 受保护源码和
  报告均无 diff。
- 默认数据库 SHA-256 保持
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- `stash@{0}` 未动；无 PDF、PNG、DuckDB、output 或 raw official
  artifact 进入 Git。

## 提交

- `ce51e0c feat: add deterministic metric foundation`
- `94df17a test: add PetroChina PIT metric integration`
- 正式报告和本记录定稿进入第三个独立提交。

## 最终结论

```text
M2 Stage 2A: PASS
Minimal transparent metrics: TRUSTED
Additional fact coverage: ALLOWED
Scoring: NOT YET
```
