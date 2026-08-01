# M2 Stage 2D-E 验收：PetroChina 2021-2025 合并净利润 net_profit 官方事实与重列覆盖

- 状态：**PASS**
- 日期：2026-08-01
- 分支 / 起点：`feat/m2-value-assessment-mvp` @ `766a20d`
- 模块：价值评估（ROA 分子事实底座）
- Runner：`src/ashare_research/tools/official_net_profit_fact_foundation.py`（offline）
- 试验运行：`run_id=stage2de_trial`（status=passed, transaction_committed=true,
  offline=true, network/pdf/cache=false, downloaded=0）

## 1. 目标与边界

补齐 5 个年度 duration Concept `net_profit`（合并净利润，含归母与非控股股东损益）
的 2021-2025 官方事实与重列覆盖，解除 Stage 2D-C 冻结的 "ROA numerator fact
coverage" 阻塞。

- 正式值只取自经审计合并利润表"净利润"**直接披露行**；
- 归母+少数股东损益加总仅作交叉校验，**不**生成正式 Fact；
- 不使用归母净利润、扣非净利润、营业利润、利润总额、母公司单体净利润；
- 不新增 Context（复用既有 11 个）；不手写 reconciled Fact；
- 不修改 Rule 001-004 语义/输出/身份、Stage 2D-C 方法论 JSON、既有 evidence；
- **不计算 ROA/ROIC/评分**；不进入 ROA Metric。

## 2. 证据：PDF 文本层核验（证据准备阶段，非 runner；gitignored 辅助脚本）

辅助脚本 `output/verify_and_extract_net_profit.py`（仅文本层，无 OCR、无 PNG、
无下载）。缓存 `D:\量化分析-cache\official-pdfs\<sha256>.pdf` 9 份 PDF 全部在位，
头（`%PDF-`）/大小/页数/SHA-256 与 annual bundle 登记逐项一致：36/36 OK，
`cache_miss=0`。

- 2021 公司 audited statements `badab8f2…`（95 页）p10 文本层 chars=0（扫描影像，
  实测复核与 Stage 2D-B 判定一致）→ 公司来源改用已登记的 2021 业绩公告
  `555a24ed…`（44 页，文本层完好，p42 完整复现经审计合并及公司利润表），
  共享 `company_ir:601857.SH:2021:annual:zh-cn` source_id，不改变版本链稳定身份。

### 2.1 原值（当年年报当期合并列，直接"净利润"行）

| FY | 净利润（百万元） | 万元 | 公司来源页（PDF/印刷） | 交易所来源页（PDF/印刷） |
|---|---:|---:|---|---|
| 2021 | 114,687 | 11,468,700 | 555a24ed p42/p42 | 939de04e p114/p112 |
| 2022 | 163,977 | 16,397,700 | fea19e90 p113/p111 | da64c67d p113/p111 |
| 2023 | 180,291 | 18,029,100 | b845502e p114/p112 | b845502e p114/p112（同字节） |
| 2024 | 183,747 | 18,374,700 | 15a2de01 p115/p113 | 15a2de01 p115/p113（同字节） |
| 2025 | 172,005 | 17,205,000 | 0eba96bd p109/p107 | 840b15aa p109/p107 |

双来源精确相等：2021 年 555a24ed p42 与 939de04e p114 四列逐值一致；2022
fea19e90 与 da64c67d p113 逐值一致；2023/2024 公司与交易所为同一 SHA PDF；
2025 两源 p109 逐值一致。

### 2.2 比较值（下一年报比较列，2021-2024 reviewed）

| target FY | 原值（百万元） | 比较值（百万元） | 比较页 | changed | 披露原因 |
|---|---:|---:|---|---|---|
| 2021 | 114,687 | 114,687 | 2022 年报 p113/p111 | 否 | none |
| 2022 | 163,977 | 163,343 | 2023 年报 p114/p112 | **是** | Interpretation 16 / IAS 12 revisions |
| 2023 | 180,291 | 180,561 | 2024 年报 p115/p113 | **是** | Common-control business combination (中油电能) |
| 2024 | 183,747 | 183,747 | 2025 年报 p109/p107 | 否 | none |
| 2025 | 172,005 | — | — | not_yet_reviewable | — |

**R = 2**（FY2022、FY2023），与 Stage 2D-B 分母、Stage 2D-D 归母净利润的重列
格局完全一致（同一重述事件同时影响利润表与资产负债表）。

### 2.3 桥接校验（归母 + 少数股东损益 = 净利润；仅交叉校验）

| FY | 归母 | 少数股东损益 | 加总 | 净利润直接行 | tie |
|---|---:|---:|---:|---:|---|
| 2021 | 92,161 | 22,526 | 114,687 | 114,687 | ✓（另：利润总额−所得税 158,194−43,507=114,687 ✓） |
| 2022 | 149,375 | 14,602 | 163,977 | 163,977 | ✓；比较列 148,738+14,605=163,343 ✓ |
| 2023 | 161,144 | 19,147 | 180,291 | 180,291 | ✓（237,458−57,167=180,291 ✓）；比较列 161,414+19,147=180,561 ✓ |
| 2024 | 164,676 | 19,071 | 183,747 | 183,747 | ✓（241,502−57,755=183,747 ✓）；比较列同原值 ✓ |
| 2025 | 157,302 | 14,703 | 172,005 | 172,005 | ✓ |

所有桥接 `exact_tie_out=true`，证据中 `bridge_status=cross_check_only_not_a_fact_input`、
`fact_creation=net_profit_taken_from_direct_disclosure_line_only`。

## 3. Rule 005（`RECON_OFFICIAL_NUMERIC_005` v1）

`src/ashare_research/reconciliation/engine.py` 纯新增常量与规则对象
（blob `459adfc7…`→`828d7051…`；4 处 protected-blob 引用跨阶段同步）：

- `supported_concepts = frozenset({"net_profit"})` —— 仅 net_profit；
  显式拒绝 `net_profit_attributable_to_parent`、`net_profit_excluding_non_recurring`、
  `operating_profit`、`profit_before_tax` 等（单元测试参数化覆盖）；
- 复用引擎门禁 1-8：company/exchange 精确相等、统一万元（Decimal，无 float
  中介）、整数且 ≤2^53−1、无容差、无平均、无来源优先；
- raw 输入 `verified` + `ineligible`；reconciled 输出 `eligible`；
- reconciled `source_id = reconciled:601857.SH:company_exchange:RECON_OFFICIAL_NUMERIC_005:v1`
  （symbol+rule 决定，跨版本稳定，与 Rule 001-004 互不冲突）；
- Rule 001-004 的 rule_id/version/supported_concepts/输出身份逐字不变
  （`test_net_profit_reconciliation_rule.py::test_rules_001_to_004_identities_are_unchanged`）。

## 4. Committed evidence（9 个新文件，既有 evidence 零修改）

- `acceptance/fixtures/official_facts/601857.SH/supplemental/2021_net_profit.json`
  … `2025_net_profit.json`（contract `net_profit_official_facts_v1`，绑定 Rule 005、
  duration 期间、base_bundle SHA/git blob、行标签"净利润"、页码、单位、
  income_statement_bridge、revision_review_status）；
- `acceptance/fixtures/restatements/601857.SH/net_profit_2021_reviewed_by_2022.json`
  … `net_profit_2024_reviewed_by_2025.json`（contract `net_profit_restatement_evidence_v1`，
  original/later 比较值、changed 标志、比较列桥接）；
- 2021 evidence 含 documents override（company=555a24ed，source_id 稳定）；
  2022-2025 无 override；
- 既有 annual / earnings-quality / denominator / capex_cash evidence Git blob 冻结
  （`test_registered_net_profit_evidence.py::test_no_existing_evidence_modified`）。

## 5. Fact 与版本链

每个 Concept-Year：company raw v1 + exchange raw v1 + reconciled v1（service
持久化，不手写 reconciled）；changed 年度建三角色 v2 并完整 supersedes；
unchanged 不建假版本。

### 5.1 Reconciled Fact IDs（canonical，跨运行确定）

| FY | v1 reconciled fact_id | latest | v2 reconciled fact_id | available_at |
|---|---|---|---|---|
| 2021 | `17cf2d11318c121b63b12cb10a5ffc347ca83d17113080e3b72ac934b68e0e78` | v1 | —（reviewed_unchanged） | 2022-04-01 |
| 2022 | `e6c913a21faa144fe4fb9fd79c4fde326a54117d397c7914219af18c878b3fb3` | v2 | `53926108e9e414cd20e7b2470b0f7babf03a79abc45977dea7f682d7a8aa8fdb` | v1 2023-03-30 → v2 2024-03-26 |
| 2023 | `34c221bb18deaa2d422544c50a4e35b43bca1297847760f95df40f50bc4a12e9` | v2 | `e52e6045f0115a78d0d9a8b037a9e869d27e9c0a74a36f29c86d12170a982ab2` | v1 2024-03-26 → v2 2025-03-31 |
| 2024 | `ef526e99d7e1e27714b2520e5af13de2afcf1da5b2068d42d8ceb3e621fdc7bc` | v1 | —（reviewed_unchanged） | 2025-03-31 |
| 2025 | `58ef51871b74f4bbd8379782bd5cfea49cf79de8f1f7a6f21c85907a58ddef6f` | v1 | —（not_yet_reviewable） | 2026-03-30 |

- v2 raw 事实 deepcopy v1 前驱、**不更新 source_id**（VersionChainValidator
  check C 稳定身份），仅更新 value/源文档元数据/available_at/版本字段；
- v2 reconciled 经 `output_supersedes_fact_id` 绑定 v1 reconciled ID 后重建
  canonical fact_id；
- 版本链：2022 v1@2023-03-30 → v2@2024-03-26；2023 v1@2024-03-26 → v2@2025-03-31；
  三角色（company raw / exchange raw / reconciled）各自完整 supersedes。

## 6. PIT 语义（AsOfQuery.get_latest_available / compare_versions）

- 年报可用时 latest Fact PIT：2021=12 / 2022=22 / 2023=32 / 2024=42 / 2025=52；
  final（2026-03-30）latest PIT = **52**；
- changed 年度在下一年报公告日前返回 v1、公告日切 v2：
  2022 net_profit 于 2024-03-25→v1、2024-03-26→v2；
  2023 net_profit 于 2025-03-30→v1、2025-03-31→v2；
- `compare_versions` 精确检测 2 个 changed 年度（changed=True），2021/2024
  unchanged（changed=False）；
- 无 PIT 提前暴露：v2 的 `available_at` 为下一年报公告日（max 双路径），
  VersionChainValidator check D（available_at/announcement_date 不降）通过。

## 7. ROA 分子就绪登记（不计算 ROA）

`net_profit_input_readiness.json`（contract `net_profit_input_readiness_v1`）：
2021-2025 latest reconciled Fact ID、value、available_at、review 状态、
`scope=consolidated`、`unit=万元`、`ready_for_roa_numerator=true`；
`all_years_ready=true`、`roa_numerator_fact_coverage_blocker_cleared=true`；
`roa_computation=not_performed`、`roic_computation=not_performed`、
`scoring=not_implemented`。

**"ROA numerator fact coverage" 阻塞解除**；Stage 2D-C 方法论 JSON
（blob `4eb22db4…`）保持冻结不修改；状态推进仅记录于本报告与 roadmap
（append-only，blob `04d323dd…`→`a9fa3da1…`，历史文本不变）。

## 8. 动态计数（R=2，实测自 trial run）

| 指标 | 公式 | 实测 |
|---|---|---:|
| contexts | 11（复用） | 11 |
| financial_facts | 195+3R | 201 |
| raw/ineligible | 130+2R | 134 |
| reconciled/eligible | 65+R | 67 |
| version links | 39+3R | 45 |
| audit | 195+3R | 201 |
| lineage | 195+3R | 201 |
| final latest PIT | — | 52 |

Rule lineage 分布：Rule 001=57、Rule 002=18、Rule 003=57（上游不变）、
Rule 004=48（(12 v1+4 v2)×3，分母重列不变）、Rule 005=21（(5 v1+2 v2)×3，新增）。

## 9. 基线重建与不变性（runner 内验证 + 测试断言）

runner 每次运行在临时目录重建上游并逐项断言：

- Stage 2D-B 180 Fact：counts 180/60/47/39，ID 集合 SHA=`2bd5b2d2…` 不变；
- Stage 2D-D 70 Metric Result：combined_counts={definitions:11, results:70,
  computed:66, insufficient_history:4, version_links:15, lineage:143,
  final_latest:55, final_computed:51}；ROE 7 版本（result_versions=7,
  computed=7, version_links=2, lineage_rows=21, final_latest=5）；
- 70 Result ID 集合 SHA（`sha256("\n".join(sorted))`）=`bdd9d4fee977…` 不变；
- 旧 63 ID 集=`34edbbc3…`、语义=`e988394f…` 不变；
- 上游 132 Fact ID 集=`1e5267022b…` 不变；
- 上游 fact DB 与 metrics DB 读取前后 SHA 不变（只读）；
- 默认 `data/research.duckdb` SHA=`4a71d3c7…` before==after 不变；
- `stash@{0}` 未动；
- protected Git blob（24 项）冻结：Stage 2D-B/2D-C/2D-D 产物、Rule 001-004 +
  Fact/Metric 代码、Concept Registry、docs（engine.py 与 roadmap 为 2D-E
  合法推进，其余逐字不变）；
- 无 .duckdb/.wal/.pdf/.png 入库（运行产物仅在 gitignored `output/` 与 pytest tmp）。

## 10. 门禁（实际执行）

1. `ruff check src tests`：exit 0；
2. `compileall -q src tests` + 模块 import：exit 0；
3. targeted pytest（net_profit rule 28 + evidence 48 + foundation 15 +
   4 处同步的 protected-blob 套件 63）：全过；
4. full pytest：（见工作记录"验证"节）；
5. `git diff --check`：exit 0；
6. 污染检查：无 DB/PDF/PNG 入库；默认 DB SHA 不变；stash 未动。

## 11. 结果

- 2021-2025 consolidated `net_profit` 官方事实与重列覆盖落地，R=2；
- 全部计数/PIT/版本链/桥接/不变性断言通过；
- ROA 分子事实覆盖阻塞解除；ROA 透明计算在下一阶段允许；
- 未计算 ROA/ROIC/评分；未进入 ROA Metric；未 merge main；未建 Tag/Release。

## 12. 结论

```text
M2 Stage 2D-E: PASS
2021—2025 consolidated net_profit facts: TRUSTED
ROA numerator: READY
ROA transparent metric computation: ALLOWED
ROIC: NOT YET
Scoring: STILL NOT YET
```
