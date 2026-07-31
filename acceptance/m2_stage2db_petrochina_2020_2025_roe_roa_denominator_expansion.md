# M2 Stage 2D-B：中国石油 2020-2025 ROE/ROA 平均余额分母官方事实

## 结论

**PASS。** 本阶段把 Stage 2D-A 的 2024-2025 双年窗口扩展为 2020-2025 六年，
新增 2020 期初开仓基线与 2021/2022/2023 当期 instant 分母证据、三份比较列重述证据
（2021<-2022、2022<-2023、2023<-2024），并补建 2022/2023 两项被追溯重述的 v2 版本链
（R = 4）。共新增 8 个 Concept-Date × 3 角色 v1（24 Fact）+ R×3 = 12 个 v2 Fact，
输出 2021-2025 五年×两概念共 10 个平均余额输入配对。没有计算平均余额、ROE、ROA、ROIC 或评分。

- run_id：`roe_roa_denominator_601857_SH_2020_2025_20260731_201740_244689`（离线 runner 以已提交证据实跑产出，2026-07-31；`run_manifest.json` 位于 gitignored `output/`，未进 Git）
- contract：`roe_roa_denominator_official_facts_v1` / `roe_roa_denominator_2020_2025_foundation_v1`
- offline / network / PDF / cache：`true / false / false / false`
- downloaded：`0`
- Metric computation：`not_performed`
- scoring：`not_implemented`

## 原始值（经审计合并资产负债表，人民币百万元，×100 = 万元）

| Concept | 2020（2021 年报比较列） | 2021 | 2022 v1 / v2（2023 年报比较列） | 2023 v1 / v2（2024 年报比较列） | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| `total_assets` | 2,488,400 | 2,502,533 | 2,673,751 / 2,670,666 | 2,752,710 / 2,759,237 | 2,753,007 | 2,828,017 |
| `equity_attributable_to_parent` | 1,215,421 | 1,263,815 | 1,369,576 / 1,365,866 | 1,446,410 / 1,451,333 | 1,515,371 | 1,586,061 |

页码（PDF page / printed page）：

- 2020/2021（取自 2021 年报）：公司=业绩公告 `555a24ed` p40(资产总计)/p41(归母)，交易所=`939de04e` p112/p110、p113/p111；
- 2022 年报（公司 `fea19e90` / 交易所 `da64c67d`）：p111/p109、p112/p110；
- 2023 年报（`b845502e`）：p112/p110、p113/p111；
- 2024/2025 年报沿用 Stage 2D-A。
- v2 比较列页：2022 v2 在 2023 年报 p112/p113；2023 v2 在 2024 年报 p113/p114。

`R = 4`：2022 两项 + 2023 两项被后续年报比较列追溯重述；2021、2024 未变（R 贡献 0）。

会计恒等式交叉验证（合并列）：流动资产合计 + 非流动资产合计 = 资产总计；
归属于母公司股东权益合计 + 少数股东权益 = 股东权益合计；
负债合计 + 股东权益合计 = 负债及股东权益总计 = 资产总计。2020-2025 各年当期列与 2022/2023 比较列均精确成立。

## 证据

七份 PDF 来自共享缓存 `D:\量化分析-cache\official-pdfs\<sha256>.pdf`，全部 `cache_miss=0`、
`downloaded=0`、`hash_verified`（PDF 头、大小、页数、SHA-256 与 annual bundle 一致）：

- 2021 业绩公告 `555a24ed…4786`，1,195,800 bytes，44 页（文本层）；
- 2021 公司经审计财务报表 `badab8f2…d7a99`，4,714,421 bytes，95 页（扫描影像，无文本层，不作为分母来源）；
- 2021 交易所 `939de04e…841f`，5,115,948 bytes，282 页；
- 2022 公司 `fea19e90…15c1` / 交易所 `da64c67d…d861`，285 页；
- 2023 公司/交易所（字节相同）`b845502e…6692`，293 页；
- 2024 公司/交易所 `15a2de01…9bba`，280 页。

提取方式：PyMuPDF `get_text("words")` 坐标定位（4 列：当年合并 / 上年合并 / 当年公司 / 上年公司，
取“合并”列）+ `search_for` y 重叠行重建；中文写 UTF-8 结果文件规避控制台乱码。未使用总权益、
流动资产、分部或母公司单体数据。正式 runner 离线，不访问 PDF/cache/网络。

**2020/2021 公司来源处理（诚实性要点）**：2021 年报公司经审计财务报表 `badab8f2` 为扫描影像 PDF
（CCITTFaxDecode，95 页文本层为空），无法据文本层诚实确认“资产总计”“归属于母公司股东权益”。
改用已登记的 2021 年度业绩公告 `555a24ed`（含文本层，p40-41 完整复现经审计合并资产负债表）作为
2020/2021 公司来源；其数值与交易所版逐行精确一致，三重会计恒等式成立。`555a24ed` 与 `badab8f2`
共享同一 `company_ir:601857.SH:2021:annual:zh-cn` source_id，引用其不改变版本链稳定标识
（VersionChainValidator check C 通过）。2020 evidence 标记 `comparison_only_opening_baseline`，
`available_at` 取两份 2021 年报公告日较晚者 2022-04-01。

## Rule 004 与 v2 source_id 稳定

复用 Stage 2D-A 的 `RECON_OFFICIAL_NUMERIC_004` v1，未改 Rule 001-004 语义。
company/exchange 必须精确相等，raw verified/ineligible，reconciled eligible，精确换算万元，
无容差/平均/来源优先。reconciled 输出 source_id 为 `reconciled:{symbol}:company_exchange:{rule_id}:v{version}`，
仅由 symbol+rule 决定，天然跨版本稳定。

**v2 raw Fact source_id 稳定（修正 2D-A 隐性缺陷）**：2D-A runner v2 路径（`official_roe_roa_denominator_2025_acceptance.py`
lines 874-891）将 `source_id` 设为后一年报 bundle 的 source_id，违反 VersionChainValidator check C；
因 2D-A R=0 从未触发。本阶段 `_build_v2_raw_fact` 采 earnings-quality foundation v2 既有成功范式：
`copy.deepcopy(predecessor)` 后仅更新 value/source_document/source_hash/source_url/source_page/
available_at/fact_version/restatement_version/supersedes_fact_id，**不更新 source_id**，保持跨版本稳定。
本次 R=4 首次实跑该路径并通过。

## Fact IDs

十二个 v1 reconciled instant Fact（6 年 × 2 概念；2024/2025 沿用 2D-A）：

| Concept | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| `total_assets` | `48238f43…` | `5c7546d5…` | `207919be…` | `2110761e…` | `0d464352…` | `43dac63a…` |
| `equity_attributable_to_parent` | `70b27556…` | `4d50fd72…` | `32a6f087…` | `8d62e859…` | `efe1cc1b…` | `45a8911a…` |

四个 v2 reconciled instant Fact（仅 2022/2023 changed 概念）：

| Concept | 2022 v2 | 2023 v2 |
|---|---|---|
| `total_assets` | `b3f1889a…` | `c943fa4f…` |
| `equity_attributable_to_parent` | `4ec845de…` | `19e4884f…` |

二十四个 raw verified/ineligible instant Fact（company/exchange × 2 概念 × 6 年），均经 `build_fact_id` 校验。

## 重列链

`R = 4`：2022 两项 + 2023 两项被追溯重述，各建三角色（company raw、exchange raw、reconciled）v2，
`supersedes_fact_id` 指向 v1；version chain links 共 27 + 3×4 = 39。

| 目标年 | 概念 | v1 available_at | v2 available_at（重述年报） | disclosed_change_reason |
|---|---|---|---|---|
| 2022 | total_assets / equity | 2023-03-30 | 2024-03-26 | Interpretation 16 / IAS 12 revisions |
| 2023 | total_assets / equity | 2024-03-26 | 2025-03-31 | Common-control business combination（中油电能，2024-10-29 起合并） |

2021、2024 比较复核 R=0（`reviewed_unchanged`），不建 v2。2025 维持 `not_yet_reviewable`。
v2 reconciled 的 `available_at` = company/exchange 公告日较晚者（2024-03-26 / 2025-03-31）。

## 动态计数（R=4）

| 计数项 | 实际 | 预期 |
|---|---:|---:|
| contexts | 11 | 11 |
| financial_facts | 180 | 180 |
| raw_ineligible_facts | 120 | 120 |
| reconciled_eligible_facts | 60 | 60 |
| version_chain_links | 39 | 39 |
| audit | 180 | 180 |
| lineage | 180 | 180 |

Rule 004 lineage = 48（12 v1 对账 × 3 + 4 v2 对账 × 3）。Rule 001/002/003 lineage 保持 57 / 18 / 57 不变。

## PIT

年度 latest Fact PIT（`AsOfQuery.get_latest_available()`，上游 7/14/21/28/35 + 累计 instant）：

| 年报可用日 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| PIT | 11 | 20 | 29 | 38 | 47 |

- final latest Fact PIT = 47（2025 年报可用 2026-03-30）。
- changed 概念在重述年报公告日前为 v1、公告日切 v2：2022 概念 2024-03-26 切换，2023 概念 2025-03-31 切换；
  `compare_versions()` 对目标年 period_end 条目检测到 `changed=True`。

## 平均余额输入（2021-2025 候选，不计算平均值）

十对（5 年 × 2 概念），`ready_for_average=true`，`consolidation_scope=consolidated`、`unit=万元`、相邻 12-31：

| Concept | FY2021 (2020→2021) | FY2022 (2021→2022) | FY2023 (2022→2023) | FY2024 (2023→2024) | FY2025 (2024→2025) |
|---|---|---|---|---|---|
| `total_assets`（万元） | 248,840,000→250,253,300 | 250,253,300→267,066,600 | 267,066,600→275,923,700 | 275,923,700→275,300,700 | 275,300,700→282,801,700 |
| `equity_attributable_to_parent`（万元） | 121,542,100→126,381,500 | 126,381,500→136,586,600 | 136,586,600→145,133,300 | 145,133,300→151,537,100 | 151,537,100→158,606,100 |

FY2021 起点用 2020 期初开仓基线；FY2022/FY2023 起点用 v2 重述值（2022/2023 最新可得版本）。未计算平均值。

## 不变性

- 原 132 Fact ID 集合 SHA-256：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`（不变）；
- 原 38 Metric Result ID 集合 SHA-256：`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`（不变）；
- 63 Metric Result ID 集合 SHA-256：`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`（不变）；
- Stage 2C-B / 2C-C.1 / 2C-D / 2D-A 正式报告与 runner blob 不变；2024/2025 evidence 与 2024 reviewed-by-2025 不变；
- Rule 001/002/003/004 身份、范围、输出不变；engine.py / service.py / identity.py / as_of.py / version_chain.py / validator.py 未修改；
- upstream DuckDB 前后 SHA-256 一致；
- 默认 `data/research.duckdb` 前后 SHA-256 均为：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；
- output / PDF / PNG / DuckDB / `data/raw/official` 未进入 Git。

## 工程门禁

- `python -m ruff check src tests`（ruff 0.12.0）退出码 0；
- `python -m compileall -q src tests` 退出码 0；
- targeted pytest（Rule 004 / Evidence / Restatement / Context / Integration）通过；
- full pytest 通过；
- `git diff --check` 通过；
- 污染检查：未发现缓存、密钥、PNG、DuckDB 进入 Git。

## 最终状态

```text
M2 Stage 2D-B: PASS
2020-2025 instant denominator facts: TRUSTED
ROE/ROA methodology and metric computation: ALLOWED
ROIC: NOT YET
Scoring: STILL NOT YET
```
