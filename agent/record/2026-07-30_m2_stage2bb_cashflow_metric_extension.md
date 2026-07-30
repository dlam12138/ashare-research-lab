# M2 Stage 2B-B 工作记录：现金流指标扩展

## 启动基线

- Branch：`feat/m2-value-assessment-mvp`
- Base HEAD：`a07c0d0b34062e28693f9edd66785e78ed4eabbd`
- Worktree：clean
- `stash@{0}` 保持不动。
- Stage 2B-A：75 facts、最终 Fact PIT 20。
- Fact Schema：2.1；Metric Schema / Definition Schema：1.0 / 1.0。
- Stage 2A：26 个 Metric Result versions；冻结 ID 集合摘要
  `671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf`。
- 默认数据库启动 SHA-256：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## 硬性离线边界

- `network_access = false`
- `pdf_access = false`
- `cache_access = false`
- `downloaded = 0`

本阶段只使用已提交 JSON evidence 和离线整合工具，不访问网络、PDF 或
`D:\量化分析-cache\official-pdfs`。

## 第一阶段实现

- 新增独立 `CashFlowMetricDefinitionRegistry`，只包含
  `cash_based_free_cash_flow_proxy` 与
  `cash_paid_for_fixed_assets_to_revenue`。
- Stage 2A `MetricDefinitionRegistry.DEFINITIONS` 保持四项不变。
- Metric Engine 新增明确的 Decimal 减法和 cash/revenue 除法分支；
  precision 28、quantum `0.000000000001`、`ROUND_HALF_EVEN`。
- 负代理值仍为 computed；零收入为
  `undefined_zero_denominator`；负收入为
  `not_comparable_negative_revenue`。
- 不修改 Metric Schema、Identity 或 Repository。

## 离线扩展与真实运行

- 新工具显式调用 Stage 2B-A runner，重建 75-fact run-scoped upstream。
- 输入只通过 `AsOfQuery.get_latest_available()` 取得 eligible
  `reconciled_derived` facts。
- 既有四指标由已接受的 `build_metric_versions()` 构造；两个新指标独立
  PIT 回放后，与原四项显式组合为六定义。
- revision review status 从原 restatement evidence 与 capex review
  evidence 逐 Concept 推导，不以年份硬编码 changed/unchanged。
- 只有 value、status 或 input Fact IDs 改变时才产生新版本。

真实 run：

`cashflow_metric_extension_601857_SH_2021_2025_20260730_135559_837294`

- status / committed / offline：`passed / true / true`
- network / PDF / cache access：`false / false / false`
- downloaded：`0`
- upstream facts / Fact PIT / eligible：`75 / 20 / 25`
- definitions / result versions：`6 / 38`
- computed / insufficient-history versions：`35 / 3`
- version links / lineage：`8 / 73`
- final latest / computed / insufficient history：`30 / 27 / 3`
- Metric PIT：`0 / 6 / 12 / 18 / 24 / 30`
- computed PIT：`0 / 3 / 9 / 15 / 21 / 27`
- insufficient-history PIT：`0 / 3 / 3 / 3 / 3 / 3`
- upstream DuckDB before / after：
  `24e4b142a39c04ba02e59016e0a7990a1a7f57ae4ed16d95765351dd97bdc6e3`
  / `24e4b142a39c04ba02e59016e0a7990a1a7f57ae4ed16d95765351dd97bdc6e3`

Stage 2A 26 个 Metric Result ID 摘要保持
`671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf`；
Stage 2B-A 75 个 Fact ID 摘要保持
`7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1`。

两个新指标共 12 个 result versions，只有 2023 各自产生一条 v1→v2
链；2025 均为 `not_yet_reviewable`。正式 ID、五年值、最终门禁和提交
证据见
`acceptance/m2_stage2bb_petrochina_cashflow_metric_extension.md`。

## 不变性与最终门禁

- Stage 2A 原四指标：26 versions、六条链、ID / value / status /
  input Fact IDs 全部不变。
- Stage 2B-A：75 Fact IDs 与最终 Fact PIT 20 不变。
- Stage 2A runner / 报告、Stage 2B-A runner / evidence / 报告、
  annual bundles 和全部 restatement evidence 的冻结 blob 测试通过。
- 默认数据库 SHA-256 保持
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- Ruff 0.13.2：`All checks passed!`
- compileall / 三模块 import：通过
- 新定义、Engine 与新集成 targeted：`25 passed`
- Stage 2A、Stage 2B-A、Stage 1D-B、multi-year 与
  Reconciliation 回归：`171 passed`
- 全量 pytest：`603 passed, 2 warnings`
- `git diff --check`：通过
- PDF、PNG、DuckDB、output、`data/raw/official` 均未进入 Git。

两条 warning 均来自既有 quality date parsing 测试。本阶段未创建 score
表或 score 输出，不包含评分或投资建议。

## 提交

1. `60bec96e98f3c6c2a09852c868f548d2ef7eed51`
   `feat: add cashflow metric definitions`
2. `9d154a0dab93892ee1046723d404af2c72a5d86c`
   `test: add PetroChina cashflow metric extension`
3. `docs: finalize PetroChina cashflow metric extension`
   （正式报告与本记录定稿）
