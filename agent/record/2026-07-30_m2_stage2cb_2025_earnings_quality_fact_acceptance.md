# M2 Stage 2C-B 工作记录：2025 盈利质量最小官方事实验收

日期：2026-07-30

起点：`feat/m2-value-assessment-mvp@9d73a41d93b6dcf625a718c64f686b8e760c0f11`

状态：正式验收定稿

## 阶段边界

仅处理中国石油 2025 年 `net_profit_excluding_non_recurring`、`operating_cost`、`operating_profit` 三个 Concept。不扩展 2021—2024，不创建模糊非经常性损益 Fact，不计算指标、利润率、ROE、估值或评分。

## 基线

- worktree 开始时 clean；
- `stash@{0}`：`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`，未操作；
- `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；
- upstream facts / final PIT / Metric Result versions：75 / 20 / 38；
- 75 Fact ID 集合 SHA-256：`7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1`；
- 38 Metric Result ID 集合 SHA-256：`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`。

Concept Registry 已有三个目标 Concept，不存在足够精确的 `non_recurring_gain_loss` Concept。Fact Schema、Metric Schema、FactIdentity、VersionChainValidator 和 AsOfQuery 均无需修改。

## PDF 缓存与视觉预检

从 2025 annual bundle 读取并验证两份缓存：

- company：`0eba96bd...715f8d.pdf`，10,608,680 bytes，273 页；
- exchange：`840b15aa...6e65.pdf`，9,416,509 bytes，273 页。

两份均以 `%PDF-` 开头，大小和 SHA-256 与 bundle 完全一致：

```text
cache_hit = 2
cache_miss = 0
downloaded = 0
hash_verified = 2
```

分别渲染并视觉核验 PDF 8 / 9 / 109 / 191 页；两个发布路径的对应页面视觉内容一致。确认：

- PDF 8 / 印刷 6：扣非归母净利润 161,671 百万元；
- PDF 9 / 印刷 7：非经常性损益小计 -5,051、所得税影响 766、少数股东损益影响 -84、合计 -4,369 百万元；
- PDF 109 / 印刷 107、经审计合并利润表：营业成本显示 `(2,246,121)`，按成本金额正值登记 2,246,121 百万元；营业利润 234,579 百万元；
- PDF 191 / 印刷 189：管理层补充资料再次披露同一非经常性损益桥。

桥接精确成立：`157,302 - 161,671 = -4,369 = -5,051 + 766 - 84`。未发现证据语义冲突或双来源数值差异。

## Rule 003

新增 `RECON_OFFICIAL_NUMERIC_003` v1，复用 `NumericReconciliationRule` 与共享 Decimal 精确逻辑，只支持三个目标 Concept。Rule 001 和 Rule 002 的常量、支持范围与结果身份不作修改；兼容测试冻结其既有输出 Fact ID。

第一提交前门禁：Ruff 0.13.2 通过；Rule 003、Rule 001/002 和 reconciliation targeted regression 共 `83 passed`；`git diff --check` 通过。

## 提交与真实运行

1. `98ab0a1` — `feat: add earnings quality reconciliation rule`，已独立推送；
2. `a7fdb04` — `test: register PetroChina 2025 earnings quality evidence`，已独立推送。

真实离线 run：

```text
run_id = earnings_quality_601857_SH_2025_20260730_145900
status = passed
transaction_committed = true
facts / eligible / PIT / Audit / Lineage = 84 / 28 / 23 / 84 / 84
bridge_status = reconciled
```

六个 raw Fact ID：

- company adjusted NP `466e5df9f080d6ab4a04027accaaa6d526408347083cdf094270360ef4fd22a6`
- exchange adjusted NP `501c9be93d1adf72b20f51f67629be409804bd66bd0e300dff888ff35811ec81`
- company operating cost `5e9d6710fbd703ac4d2e405fbbd108569cbed3ee0f368aca8933aa57bd4f52f0`
- exchange operating cost `e9d0c5718d11592a955a8a411ef089f6be2c514c2a7cc5cf8ff9ece419dc463c`
- company operating profit `af27da38cd6915d0b4bc7a2fb148b12b3335e7afa5058c6e8e01120d37d7f0c8`
- exchange operating profit `d6bac004cd48573d5609453e4bfc0d12a2a80bc82e171c32e0bf83a0611fbed5`

三个 reconciled Fact ID：

- adjusted NP `06f703c7e956f3d78e341be57478b9a9c1c67214f1da942645f77d8f41dc8077`
- operating cost `be615c237d0c328a531cc420fe1e7c9a96d7b748d07539ea3540c704f8f896a5`
- operating profit `2a98f29f9c371c6d52fed66efdcd9bb5a0bf6acec95752d699cfea135c3b469c`

## 最终门禁

- Ruff 0.13.2：通过；
- compileall / import：通过；
- required targeted regression：`137 passed`；
- full pytest：`642 passed, 2 warnings`；
- `git diff --check`：通过；
- 原 75 Fact ID 与 38 Metric Result ID 集合摘要不变；
- Rule 001 / 002、既有 runners/reports、Stage 2C-A 产物不变；
- 默认数据库 SHA-256 不变；
- 禁止产物未进入 Git；
- `stash@{0}` 未动。

最终结论：Stage 2C-B PASS；2025 盈利质量官方事实 TRUSTED；多年扩展 ALLOWED；新盈利质量指标与评分仍 NOT YET。
