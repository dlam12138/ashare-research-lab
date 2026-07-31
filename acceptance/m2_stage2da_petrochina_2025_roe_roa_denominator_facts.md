# M2 Stage 2D-A：中国石油 2025 ROE/ROA 平均余额分母官方事实

## 结论

**PASS。** 本阶段为 ROE/ROA 平均余额分母建立四个经审计合并资产负债表 instant 官方事实，
新增 Rule 004 双源对账、两个 instant Context、2024/2025 分母证据与 2024 重列证据，
并输出 2025 平均余额输入配对。没有计算平均余额、ROE、ROA、ROIC 或评分。

- run_id：`roe_roa_denominator_601857_SH_2024_2025_<timestamp>`
- contract：`roe_roa_denominator_official_facts_v1` / `roe_roa_denominator_2025_acceptance_v1`
- offline / network / PDF / cache：`true / false / false / false`
- downloaded：`0`
- Metric computation：`not_performed`
- scoring：`not_implemented`

## 原始值（经审计合并资产负债表，人民币百万元，×100 = 万元）

| Concept | 2024 年报（2024-12-31 当期列） | 2025 年报比较列（2024-12-31） | 2025 年报（2025-12-31 当期列） |
|---|---:|---:|---:|
| `total_assets` | 2,753,007 | 2,753,007 | 2,828,017 |
| `equity_attributable_to_parent` | 1,515,371 | 1,515,371 | 1,586,061 |

页码（PDF page / printed page）：

- 2024 年报：`total_assets` p113 / p111；`equity_attributable_to_parent` p114 / p112；
- 2025 年报：`total_assets` p107 / p105；`equity_attributable_to_parent` p108 / p106。

`R = 0`：2025 年报比较列中 2024 两项与 2024 年报当期列完全相等，未发生重列。

会计恒等式交叉验证（合并列）：流动资产合计 + 非流动资产合计 = 资产总计；
归属于母公司股东权益合计 + 少数股东权益 = 股东权益合计；
负债合计 + 股东权益合计 = 负债及股东权益总计 = 资产总计。两项年度均精确成立。

## 证据

四份 PDF 来自共享缓存 `D:\量化分析-cache\official-pdfs\<sha256>.pdf`，全部 `cache_miss=0`、
`downloaded=0`、`hash_verified=4`（PDF 头、大小、页数、SHA-256 与 2024/2025 annual bundle 一致）：

- 2024 公司/交易所（字节相同）：`15a2de01…9bba`，11,167,845 bytes，280 页；
- 2025 公司：`0eba96bd…715f8d`，10,608,680 bytes，273 页；
- 2025 交易所：`840b15aa…6e65`，9,416,509 bytes，273 页。

提取方式：`pdftotext -enc UTF-8 -layout`（中文标签可读）+ PyMuPDF `get_text("words")` 坐标定位
（4 列：当年合并 / 上年合并 / 当年公司 / 上年公司，取“合并”列）。未使用总权益、流动资产、
分部或母公司单体数据。正式 runner 离线，不访问 PDF/cache/网络。

## Rule 004 与 FACT_INSTANT_001 微调

新增 `RECON_OFFICIAL_NUMERIC_004` v1（`NumericReconciliationRule`），仅支持
`total_assets` 与 `equity_attributable_to_parent`；company/exchange 必须精确相等，
raw verified/ineligible，reconciled eligible，精确换算万元，无容差/平均/来源优先。

为解除此前 `FACT_INSTANT_001`（禁止 instant 派生）与 `FACT_SOURCE_001` reconciled 分支
（要求 `is_derived=True`）对 instant Concept 的互斥，将 `FACT_INSTANT_001` 收窄为“仅拦截相减派生”
（`derivation_definition_id != official_dual_source_reconciliation`），放行双源对账 instant Fact。
此微调与 `rule_registry.py` 文档化本意（“不得通过相减生成”）一致，仅对单一白名单放行，
不影响 Rule 001/002/003 的身份、范围与输出。

## Fact IDs

四个 reconciled instant Fact（R=0，无 v2）：

| Concept | 2024-12-31 reconciled | 2025-12-31 reconciled |
|---|---|---|
| `total_assets` | `0d464352b3e788362d7c5864c50d9a18c136a43374910d952e22ededee94c30` | `43dac63a557127d59337a4f36380d892a79373c1f319bd8824d0f83300b68a31` |
| `equity_attributable_to_parent` | `efe1cc1b1d0cdb4b09b828dd5a658295585ff5d398d0a51621d651110f75b6d5` | `45a8911a4b1626157c179dc44880da947bde9dfda937d18f8464a9381606eb90` |

八个 raw verified/ineligible instant Fact（company/exchange × 2 concepts × 2 years）：

```
253bc5ca592e2a093aa38048decad0479e5d2c44f24693fa9fed47be6c1ca00d
6dad055df25facf992e442853becd6da27988deac1e1a87e27028e1d37dbf73e
7680fdcf8c6563284812bc2d28e9df06fb5bee086045f2ce7291d64ce7899f18
a52be201040a2483d256186ee68a03db4ab4384cb86f4038bc8538bdcd91b295
bdb4c3c916cf678b30360aabd2a3e0d12e10d4aa08c096d1671a7cd49acf3065
cda7ab5648cca346322244fb08dde5e82cc97c890079eb3d8bc242330995c8cc
df64788c0dba7ce5b91395db3f54e12c5f9074d475efacfab890926124359aa3
fad693f1b402398df12fe42e57ca53f4abc2d55b4f5e0bf71dc49a9ea9f91825
```

## 重列链

`R = 0`：2024 两项 instant Concept 在 2025 年报比较列中未变化，不建 v2 版本链。
`v2_reconciled_fact_ids = []`，`restatement_transitions = []`。
2025 两项标记 `not_yet_reviewable`；2024 两项 `reviewed_unchanged`。

## 动态计数（R=0）

| 计数项 | 实际 | 预期 |
|---|---:|---:|
| contexts | 7 | 7 |
| financial_facts | 144 | 144 |
| raw_ineligible_facts | 96 | 96 |
| reconciled_eligible_facts | 48 | 48 |
| version_chain_links | 27 | 27 |
| audit | 144 | 144 |
| lineage | 144 | 144 |

Rule 004 lineage = 12（4 组对账 × 3 角色）。Rule 001/002/003 lineage 保持 57 / 18 / 57 不变。

## PIT

- 2024 年报可用（2025-03-31）：30（28 duration + 2 instant 2024）；
- 2025 年报可用（2026-03-30）：39（35 duration + 4 instant）；
- final latest Fact PIT = 39。

PIT 通过 `AsOfQuery.get_latest_available()` 取每个 fact key 的最新版本。
`changed` 的 2024 事实在 2025 公告日前为 v1、公告日切 v2--因 R=0，无切换；
`compare_versions()` 未检测到变化。

## 平均余额输入（2025 候选，不计算平均值）

| Concept | beginning (2024) | ending (2025) | ready |
|---|---|---|---|
| `total_assets` | 275,300,700 万元 (`0d464352…`) | 282,801,700 万元 (`43dac63a…`) | true |
| `equity_attributable_to_parent` | 151,537,100 万元 (`efe1cc1b…`) | 158,606,100 万元 (`45a8911a…`) | true |

两对 `consolidation_scope` 与 `unit` 均一致，`ready_for_average=true`。未计算平均值。

## 不变性

- 原 132 Fact ID 集合 SHA-256：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`（不变）；
- 原 38 Metric Result ID 集合 SHA-256：`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`（不变）；
- 63 Metric Result ID 集合 SHA-256：`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`（不变）；
- Stage 2C-B / 2C-C.1 / 2C-D 正式报告 blob 不变；
- Rule 001/002/003 身份、范围、输出 Fact ID 不变；
- upstream DuckDB 前后 SHA-256 一致；
- 默认 `data/research.duckdb` 前后 SHA-256 均为：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；
- Fact Schema、FactIdentity、AsOfQuery、VersionChainValidator、Metric 代码未修改；
- output / PDF / PNG / DuckDB / `data/raw/official` 未进入 Git。

## 工程门禁

- Ruff `0.13.2`、compileall、imports：通过；
- targeted pytest（Rule 004 / Evidence / Context / Integration）：`33 passed`（12 + 10 + 11）；
- full pytest：`711 passed, 2 warnings`（2 warnings 为与本阶段无关的既有 dateutil 回退）；
- 回归（reconciliation + validator + version_chain + m2_facts + earnings_quality_2025_acceptance）：`177 passed`；
- `git diff --check`：通过；
- 污染检查：未发现缓存、密钥、PNG、DuckDB 进入 Git。

## 最终状态

```text
M2 Stage 2D-A: PASS
2025 ROE/ROA denominator official facts: TRUSTED
2020-2025 instant balance-sheet expansion: ALLOWED
ROE/ROA metric computation: NOT YET
ROIC fact foundation: NOT YET
Scoring: STILL NOT YET
```
