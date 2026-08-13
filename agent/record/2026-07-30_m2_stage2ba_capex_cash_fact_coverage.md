# M2 Stage 2B-A 工作记录：资本开支现金事实覆盖

## 启动基线

- Branch：`feat/m2-value-assessment-mvp`
- HEAD：`5a3f9006b19781d1a42db6df09d5d718111f9c76`
- Worktree：clean
- `stash@{0}` 保持不动。
- Stage 1D-B：57 facts、最终 Fact PIT 15。
- Stage 2A：Metric Schema 1.0，26 个结果版本、20 个最终结果；全部
  Metric Result ID 作为冻结不变量。
- 默认数据库启动 SHA-256：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## 官方 PDF 缓存策略

- 共享缓存：`D:\量化分析-cache\official-pdfs`。
- 每份文档先由已提交 annual bundle 取得 SHA-256、content_length 和
  URL，再验证缓存文件 `%PDF-` 文件头、大小和 SHA-256。
- 启动时共享缓存目录不存在。八个唯一 PDF 从任务开始前已存在且与
  bundle 完全匹配的 Git 忽略本地副本写入缓存；两组 byte-identical
  文档随后命中同一缓存对象。
- 正式统计：cache_hit 2、cache_miss 8、downloaded 0、
  hash_verified 10、populated_from_existing_local 8。
- 临时渲染和定位文件不进入 Git；共享 PDF 缓存不删除。

## 事实核验结果

- 经审计合并现金流量表的正式行标签为
  “购建固定资产、油气资产、无形资产和其他长期资产支付的现金”，与
  `cash_paid_for_fixed_assets` 语义一致；Concept ID、version、category、
  canonical unit 和 duration 语义不变，只补充正式中文 alias。
- 五个 original 合并列及后续比较列已完成两遍目视复核。当前确认
  2024 年报把 2023 比较值由 282,519 重列为 282,508（人民币百万元）；
  其余三个后续比较值不变，因此预期 `C = 1`。

五年 original 原值依次为 265,563、243,752、282,519、302,651、
292,789（人民币百万元），规范化为万元后两来源逐年完全一致。2024 年报
将 2023 比较值由 282,519 重列为 282,508；其余可复核年度比较值不变，
所以 `C = 1`，2025 为 `not_yet_reviewable`。

## 最小实现

- 保留 `RECON_OFFICIAL_NUMERIC_001` version 1 和默认 Engine 行为；
  新增冻结的 `NumericReconciliationRule` 配置及仅支持
  `cash_paid_for_fixed_assets` 的 `RECON_OFFICIAL_NUMERIC_002`
  version 1。
- Service lineage 使用实际 reconciliation result 的 rule ID/version；
  既有静态 builder 默认仍为 rule 001，保持兼容。
- Concept ID、version、category、canonical unit 和 duration 语义不变，
  只补充正式报表行标签 alias。
- 五个 supplemental bundle 仅绑定已提交 annual bundle；四个 capex
  review evidence 分别复核下一年度比较列。
- `official_capex_cash_fact_foundation` 在写入前完成全部 evidence
  preflight，复用 Stage 1D-B 57 facts，在同一 run-scoped DuckDB 中写入
  capex v1 和实际发生变化的 2023 v2。

## 真实离线验收

- run：
  `capex_cash_foundation_601857_SH_2021_2025_20260730_132125_166207`
- status / committed / offline：`passed / true / true`
- Fact Schema：`2.1`
- rule：`RECON_OFFICIAL_NUMERIC_002` version `1`
- upstream facts / upstream PIT：`57 / 15`
- final facts / final PIT：`75 / 20`
- company / exchange / reconciled：`25 / 25 / 25`
- raw / eligible：`50 / 25`
- version links / Audit / Lineage：`15 / 75 / 75`
- 新增 company / exchange / reconciled：`6 / 6 / 6`

2023 reconciled v1
`5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55`
在 2025-03-30 仍为 PIT 最新版本；2025-03-31 切换到 v2
`b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510`。
v2 严格 supersede v1。

## 冻结不变量

- upstream 57 Fact ID 集合摘要：
  `e2afd5d39ae97f2488f5e9a713fda578174c38c5ea13e37d12e8844a8f29d829`
- Stage 2A 26 Metric Result ID 集合摘要：
  `671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf`
- 默认数据库 SHA-256 保持：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`
- annual bundle、既有 restatement evidence、Stage 1D-A/1D-B/2A
  工具与报告的保护 blob 测试通过。
- PDF、PNG、DuckDB、output、raw official artifact 均不进入 Git；
  `stash@{0}` 未操作。

## 提交计划与门禁

已完成两个独立提交：

1. `cdb99e0` `feat: add supplemental official numeric reconciliation`
2. `96a6b97` `test: register PetroChina capex cash facts`

正式报告和本记录定稿由第三个文档证据提交提交。最终门禁：

- Ruff 0.13.2：`All checks passed!`
- compileall：通过
- 新 rule 与新 tool imports：通过
- 新增 targeted：`16 passed`
- Stage 1D-B、Stage 2A、multi-year 与 Reconciliation 回归：
  `160 passed`
- 全量 pytest：`578 passed, 2 warnings`
- `git diff --check`：通过

两条 warning 均来自既有 quality date parsing 测试，不是本阶段新增代码。
追踪文件审计确认没有 PDF、PNG、DuckDB、output 或
`data/raw/official` artifact；默认数据库和所有保护 blob 均保持不变。
