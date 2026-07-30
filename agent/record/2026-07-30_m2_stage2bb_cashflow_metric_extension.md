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

真实运行、ID、PIT、计数、不变性、门禁和提交证据将在后续定稿。
