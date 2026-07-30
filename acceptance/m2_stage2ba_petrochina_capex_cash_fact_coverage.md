# M2 Stage 2B-A：中国石油资本开支现金事实覆盖正式验收报告

## 验收结论

> **M2 Stage 2B-A：PASS**
>
> **Capex cash official facts：TRUSTED**
>
> **Free cash flow metric extension：ALLOWED**
>
> **Scoring：NOT YET**

- Branch：`feat/m2-value-assessment-mvp`
- 起始提交：`5a3f9006b19781d1a42db6df09d5d718111f9c76`
- 最终真实 run：
  `capex_cash_foundation_601857_SH_2021_2025_20260730_132125_166207`
- Fact Schema：`2.1`
- supplemental rule：`RECON_OFFICIAL_NUMERIC_002` version `1`
- upstream Stage 1D-B：`passed`
- transaction committed：`true`
- offline：`true`

本阶段仅补齐 `cash_paid_for_fixed_assets` 的双官方原始事实、核验事实和
重列版本链，没有新增自由现金流指标、评分或投资结论。

## 五年官方事实证据

两份来源均直接核对经审计合并现金流量表。正式行标签为
“购建固定资产、油气资产、无形资产和其他长期资产支付的现金”；原报表
括号表示现金流出，事实按现金支付金额的正数幅度保存。原始单位为人民币
百万元，按既有 `RMB_MILLION_TO_CNY_10K_X100` 规则规范化为万元。

| 年度 | 原报表值（人民币百万元） | 规范化值（万元） | Company 页面 | Exchange 页面 | 表名 / 合并列 |
|---:|---:|---:|---|---|---|
| 2021 | `(265,563)` | 26,556,300 | PDF 11 / 印刷 9 | PDF 115 / 印刷 113 | 2021年度合并及公司现金流量表 / 2021年度合并 |
| 2022 | `(243,752)` | 24,375,200 | PDF 114 / 印刷 112 | PDF 114 / 印刷 112 | 2022年度合并及公司现金流量表 / 2022年度合并 |
| 2023 | `(282,519)` | 28,251,900 | PDF 115 / 印刷 113 | PDF 115 / 印刷 113 | 2023年度合并及公司现金流量表 / 2023年度合并 |
| 2024 | `(302,651)` | 30,265,100 | PDF 116 / 印刷 114 | PDF 116 / 印刷 114 | 2024年度合并及公司现金流量表 / 2024年度合并 |
| 2025 | `(292,789)` | 29,278,900 | PDF 110 / 印刷 108 | PDF 110 / 印刷 108 | 2025年度合并及公司现金流量表 / 2025年度合并 |

每个年度、每个来源均完成两遍目视核对。两来源在各年度的规范化值完全
一致，五组 v1 reconciliation 均为 `matched`，绝对差额为零。

## 官方 PDF 共享缓存

按照修正后的获取策略，先由已提交 annual bundle 读取 URL、SHA-256 和
content_length，再使用仓库外共享缓存
`D:\量化分析-cache\official-pdfs\<sha256>.pdf`。所有引用均重新验证
`%PDF-` 文件头、文件大小和 SHA-256。

| 项目 | 数量 |
|---|---:|
| cache_hit | 2 |
| cache_miss | 8 |
| populated_from_existing_local | 8 |
| downloaded | 0 |
| hash_verified | 10 |

任务启动时共享缓存尚不存在；八个唯一 PDF 已在 Git 忽略目录中存在且
与登记值完全一致，因此经验证后写入共享缓存。两组 byte-identical 文档
随后命中相同缓存对象。正式流程没有联网下载；早期的临时网络定位文件不
作为证据，未进入 Git，也没有删除共享 PDF 缓存。

## 五组 v1 Fact ID

| 年度 | Company Fact ID | Exchange Fact ID | Reconciled Fact ID |
|---:|---|---|---|
| 2021 | `be03e3890d1152222d6337dde2272a2ecf42a092f7cca124612e8b336f7ffe18` | `4dcb9929d2a0ab660b3c16942fe3deefd8c2fb4add0439cd1445c7d1c82ee8ac` | `8fc1ab550cae3ec8ad73de2a0328dcc730bb76ee9d1abe89c04eeb884b8cb0dd` |
| 2022 | `27ca44497ab45434b68ded0db9776d68118e6b42c289bf1fbcb19617d4700560` | `eaf7d6b68c9170543352543bacdaa85c4ab2066e40c45553be2600cc41b40cfd` | `3ca12114806d0fc07bedfa0e78ee5c9b8c086d7d377aa27c2dfdb1d998bbd0e9` |
| 2023 | `eb5d6c0a33462a44a0cfd02cd0fb909249d524ba839d5d0aef205145ee138f12` | `7cb76142c08a06ef3d1f857606c9a705860a418900eed9dd937ba54d56e6efbd` | `5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55` |
| 2024 | `d162bc0b0ec4577d162c511e9fd9b1bec5b8f96e2b0e582d804103fcf3b3f77c` | `7df9a97b3bbcc33b27a91cf4ddfbe00b0510bf8fc45d08c7cadb3030c894f3ae` | `c1f4119d6a60dd2e7d093e0d7f33c56603dcea3ea6cd3f9ea32bef6dc342db21` |
| 2025 | `44236d796798f83cd6725e642bcc5c67128f5f1f723c86ab42d9e31bb7b8213e` | `695c76b401a0b9e7373c9e8344b3f82fbf89f0c9b624ceae239e6962bc433982` | `5dc4c375138e6cac5a26866d2120fc9d6bc68b69a19dabd56902ae0a6660b34f` |

Rule 002 只接受 `cash_paid_for_fixed_assets`；原有 rule 001 的 ID、version、
三个 Concept 支持范围和默认行为不变。

## 后续比较列与版本链

| 目标年度 | 后续报告 | original | 后续比较值 | 结论 |
|---:|---:|---:|---:|---|
| 2021 | 2022 | 265,563 | 265,563 | reviewed_unchanged |
| 2022 | 2023 | 243,752 | 243,752 | reviewed_unchanged |
| 2023 | 2024 | 282,519 | 282,508 | reviewed_changed |
| 2024 | 2025 | 302,651 | 302,651 | reviewed_unchanged |
| 2025 | — | 292,789 | — | not_yet_reviewable |

因此 changed-year count `C = 1`。2023 的变化来自 2024 年同一控制下收购
中国石油集团电能有限公司后的比较数据重列，与已接受的年度重列证据一致。

2023 v2 完整版本链如下：

| 层级 | v1 Fact ID | v2 Fact ID | v2 available_at |
|---|---|---|---|
| company | `eb5d6c0a33462a44a0cfd02cd0fb909249d524ba839d5d0aef205145ee138f12` | `f044d3eaea1f6e766e1027a81bf1dd1b33c2210e42a68dcd1ef472056ea0911d` | 2025-03-30 |
| exchange | `7cb76142c08a06ef3d1f857606c9a705860a418900eed9dd937ba54d56e6efbd` | `98410a0206ff53b2291708b1a599ec6f121a398352bdbde592528589b8d337a9` | 2025-03-31 |
| reconciled | `5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55` | `b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510` | 2025-03-31 |

三个 v2 的 `supersedes_fact_id` 均严格指向对应 v1。2023 capex PIT 在
2025-03-30 仍返回 reconciled v1，于 2025-03-31 切换到 reconciled v2；
没有提前暴露交易所尚未公告的核验结果。

## 动态计数、Audit 与 Lineage

| 项目 | 实际 |
|---|---:|
| Fact contexts | 5 |
| Upstream financial facts | 57 |
| New company facts | 6 |
| New exchange facts | 6 |
| New reconciled facts | 6 |
| Company facts | 25 |
| Exchange facts | 25 |
| Raw facts | 50 |
| Reconciled facts | 25 |
| Financial facts | 75 |
| Eligible for metrics | 25 |
| Version-chain links | 15 |
| Audit rows | 75 |
| Lineage rows | 75 |
| Final Fact PIT（2026-03-30） | 20 |

Rule 002 的六组 reconciliation 各记录 company input、exchange input 和
reconciled output，共 18 条 lineage，均写入 rule 002 version 1。upstream
rule 001 的 57 条 lineage 保持 rule 001 version 1。

## 不变性与阶段边界

- upstream 57 个 Fact ID 集合逐一相等；排序集合摘要保持
  `e2afd5d39ae97f2488f5e9a713fda578174c38c5ea13e37d12e8844a8f29d829`。
- Stage 2A 的 26 个 Metric Result ID 集合独立重跑后一致；排序集合摘要
  `671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf`。
- Stage 2A 最终 20 个 Metric Result 和正式报告未修改。
- 五个 annual bundle、原有四个 restatement evidence、Stage 1D-A、
  Stage 1D-B 和 Stage 2A 的工具与报告均未修改。
- 默认 `data/research.duckdb` SHA-256 保持
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- PDF、PNG、DuckDB、output 和 `data/raw/official` 均未进入 Git；
  `stash@{0}` 未操作。
- Ruff 0.13.2、compileall、imports、新增 targeted 16 项、Stage 1D-B /
  Stage 2A / multi-year / Reconciliation 回归 160 项、全量 pytest
  578 项与 `git diff --check` 均通过。全量测试的两条 warning 来自既有
  quality date parsing 测试。

本阶段的证据只支持“购建固定资产等支付的现金”这一现金流量表项目。
它不自动等于完整经济意义上的资本开支，也未处理资产处置回收、租赁、
收购或其他投资性现金流。自由现金流的定义、输入选择和版本化结果必须在
后续独立阶段实现；当前不得据此生成评分或买卖建议。

## 最终状态

```text
M2 Stage 2B-A: PASS
Capex cash official facts: TRUSTED
Free cash flow metric extension: ALLOWED
Scoring: NOT YET
```
