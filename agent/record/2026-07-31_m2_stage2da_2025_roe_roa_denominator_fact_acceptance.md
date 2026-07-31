# 工作记录：M2 Stage 2D-A 2025 ROE/ROA 平均余额分母事实最小验收

## 基本信息

- 日期：2026-07-31
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`d19b2c1de8d4b3488da74829e3493cfa6c4389f0`
- 任务来源：`/goal` 指令（恢复前一会话被 `FACT_INSTANT_001` 阻塞的任务）
- 对应模块：价值评估（ROE/ROA 分母事实底座）

## 任务目标

为中国石油 601857.SH 2025 ROE/ROA 的平均余额分母建立可信官方 instant 事实：
新增 `total_assets`、`equity_attributable_to_parent` 两个 instant Concept-Date（2024-12-31、2025-12-31），
通过新增 Rule 004 完成双官方精确对账，建立 2024 重列版本链（如 2025 年报比较列发生变化），
输出平均余额输入配对，不计算平均余额、ROE、ROA、ROIC 或评分。

## 范围

- 新增 `RECON_OFFICIAL_NUMERIC_004` v1（仅支持两个资产负债表 instant Concept）
- 微调 `FACT_INSTANT_001`（见决策记录），放行双源对账 instant Fact
- 新增 2024/2025 denominator evidence 与 2024 reviewed-by-2025 重列 evidence
- 新增两个 instant Context
- 新增离线 runner `official_roe_roa_denominator_2025_acceptance.py`
- 新增 Rule 004 / Context / Evidence / Integration 测试
- 新增正式验收报告

## 非目标

- 不计算平均余额、ROE、ROA、ROIC、财务安全、估值或评分
- 不扩展到 2020-2023
- 不修改 Rule 001/002/003、Fact Schema、FactIdentity、AsOfQuery、VersionChainValidator、Metric 代码或既有事实/指标
- 不 merge main，不创建 Tag/Release

## 开始前状态

- worktree clean（仅本记录为未跟踪文件）；
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，未操作；
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（与基线一致）；
- HEAD：`d19b2c1de8d4b3488da74829e3493cfa6c4389f0`；
- 上游 Stage 2C-D 冻结基线：132 Fact / 44 eligible / Fact PIT 35 / links 27；
  - 132 Fact ID 集合 SHA-256：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`；
  - 原 38 Metric Result ID 集合 SHA-256：`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`；
  - 原 38 Metric Result 完整语义 SHA-256：`f665e33775c40a1b8e092c1345978f5f8fd5650cec90c5a87a931dfba2726890`；
  - 63 Metric Result ID 集合 SHA-256：待 runner 重建后计算并记录。

## 开始前代码审查

已阅读：项目北极星文档（`docs/value_evaluation_methodology_v1.md`、`docs/value_fact_coverage_roadmap.md`、
`docs/value_scoring_readiness_gates.md`、`docs/value_evaluation_methodology_earnings_quality_v1.md`）、
`agent/agent.md`、Stage 2C-D 与 2C-C.1 工作记录与正式报告、`facts/concepts.py`、`facts/models.py`、
`facts/contexts.py`、`facts/identity.py`、`facts/as_of.py`、`reconciliation/engine.py`、`reconciliation/service.py`、
`validation/version_chain.py`、`validation/validator.py`、`validation/fact_schema.py`、`validation/rule_registry.py`、
`derivations/engine.py`、Stage 2B-A/2C-B/2C-C.1/2C-D runner、2024/2025 annual bundle。

仓库中不存在 `AGENTS.md`（与 Stage 1D-B 记录一致）；北极星以 `docs/value_*.md` 与项目指令为准。

审查确认：

1. `total_assets`（`concepts.py:263`）与 `equity_attributable_to_parent`（`concepts.py:305`）**已注册**于 `ConceptRegistry`，
   均为 `balance_sheet` / `instant` / `CNY`。目标假设需“新增两个 Concept”，实际已存在；按“以实际代码为准”不重复新增。
2. `INSTANT_CONCEPTS`（`fact_schema.py:41`）已正确包含两个目标 Concept；Fact Schema 无需升级。
3. `build_context_id` 形式为 `SYMBOL|FY|PERIOD_TYPE|SCOPE`；`compute_period_dates` 对 `PeriodType.instant` 返回 `(YYYY-12-31, YYYY-12-31)`。
4. Engine 为 symbol-agnostic、rule-driven；Rule 004 只需新建 `NumericReconciliationRule(supported_concepts={total_assets, equity_attributable_to_parent})`。
5. Rule 001/002/003 身份与支持范围冻结，兼容测试冻结其输出 Fact ID。

## 决策记录：解除 FACT_INSTANT_001 阻塞（方案 A）

### 阻塞内容（前一会话已定位，本会话已逐行复核确认）

`FACT_INSTANT_001`（`validator.py:265-274`）：

```python
if fact.get("is_derived") and cid in INSTANT_CONCEPTS:
    # error: Instant concepts must not be derived
```

`INSTANT_CONCEPTS`（`fact_schema.py:41`）包含 `total_assets` 与 `equity_attributable_to_parent`。
Reconciliation Engine 对 reconciled Fact 无条件设置 `is_derived=True`（`engine.py:469`）且
`derivation_definition_id="official_dual_source_reconciliation"`（`engine.py:471`）；
`FACT_SOURCE_001` reconciled 分支（`validator.py:_check_reconciled_source`，`is_derived` 检查在 `:653-657`）
**要求** `is_derived=True`。二者对 instant Concept 互斥：reconciled instant Fact 无法同时满足两条规则，
Service（`service.py:196` 校验输出 Fact，`:213` 抛错）零写入。代码库此前从未对账过 instant Concept。

`rule_registry.py:75` 对 `FACT_INSTANT_001` 的描述为“时点字段（资产负债表）不得通过**相减**生成”——
规则本意是禁止“相减派生”，并非禁止“双源对账派生”。`DerivationEngine`（`derivations/engine.py`）的相减派生
（单季度还原、自由现金流）使用 `single_quarter_*` / `free_cash_flow` 等 `derivation_definition_id`，
均不等于 `official_dual_source_reconciliation`。

全仓 grep 确认：无任何测试直接断言 `FACT_INSTANT_001` 或 `INSTANT_CONCEPTS` 的触发行为
（仅命中 `fact_schema.py`、`validator.py`、`rule_registry.py` 源码与本记录）。

### 决策：方案 A——最小化微调 `FACT_INSTANT_001`

将 `FACT_INSTANT_001` 的拦截条件收窄为“相减派生”：仅当 `is_derived=True`、concept 属于 `INSTANT_CONCEPTS`、
且 `derivation_definition_id != "official_dual_source_reconciliation"` 时才报错。双源对账 instant Fact 放行。

### 采用原因

- 与 `rule_registry.py:75` 文档化本意（“不得通过相减生成”）一致；
- 纯收窄（permissive）：只对 `official_dual_source_reconciliation` 放行，所有相减/求和派生 instant Fact 仍被拦截，无回归；
- 无既有测试断言该规则，不破坏任何测试；
- `FactValidator` 不在目标“不得修改”清单（Fact Schema、Identity、AsOfQuery、VersionChainValidator、Metric 代码、既有事实/指标、upstream、默认DB）内，
  也不在目标硬停止清单（需改 Schema/Identity/PIT、原 Fact/Metric ID 变化）内；
- 目标断言“Fact Schema 2.1 无需升级”仍然成立——`fact_schema.py` 不动，仅微调 validator 规则。

### 考虑过的替代方案

- 方案 B：视为硬阻塞，保留证据安全停止。未采用：与“持续到通过并 push”的指令冲突，且方案 A 在范围内、可审查、无回归。
- 让 reconciled instant Fact 不设 `is_derived`：不可行，`FACT_SOURCE_001` reconciled 分支强制要求 `is_derived=True`。
- 把目标 Concept 移出 `INSTANT_CONCEPTS`：不可行，会修改 Fact Schema（`fact_schema.py`）且语义错误（二者确为时点概念）。

### 潜在风险

- 放宽了 instant 派生门禁的语义边界。缓解：仅对 `official_dual_source_reconciliation` 单一白名单放行，
  任何新派生类型若需对账 instant Concept 必须显式扩展白名单（可审查的故意决策）；新增测试覆盖“相减派生仍被拦截”与“双源对账放行”两条路径。

## PDF 缓存核验（证据准备阶段，非 runner）

共享缓存 `D:\量化分析-cache\official-pdfs` 中四份文档（三个物理文件，2024 公司/交易所字节相同）全部通过：

- 2024 公司/交易所：`15a2de01...9bba.pdf`，11167845 bytes，280 页，SHA-256 一致，`%PDF-` 头；
- 2025 公司：`0eba96bd...715f8d.pdf`，10608680 bytes，273 页，SHA-256 一致，`%PDF-` 头；
- 2025 交易所：`840b15aa...6e65.pdf`，9416509 bytes，273 页，SHA-256 一致，`%PDF-` 头。

`cache_miss = 0`，`downloaded = 0`，`hash_verified = 4`（PDF 头、大小、SHA-256、页数均与 2024/2025 annual bundle 一致）。

合并资产负债表定位（`pdftotext -enc UTF-8 -layout` + PyMuPDF 坐标核验）：
- 2024 年报：资产总计 PDF p113 / 印刷 p111；归母权益 PDF p114 / 印刷 p112；
- 2025 年报：资产总计 PDF p107 / 印刷 p105；归母权益 PDF p108 / 印刷 p106。

## 合并资产负债表原值（人民币百万元，×100 = 万元）

经 `pdftotext -enc UTF-8 -layout`（标签可读）+ PyMuPDF `get_text("words")` 坐标定位（4 列：当年合并 / 上年合并 / 当年公司 / 上年公司，
取“合并”列）+ 三重会计恒等式交叉验证（流动+非流动=资产总计；归母+少数=股东权益合计；负债+股东权益=资产总计）确认：

| Concept | 2024 年报（2024-12-31 当期列） | 2025 年报比较列（2024-12-31） | 2025 年报（2025-12-31 当期列） |
|---|---:|---:|---:|
| total_assets | 2,753,007 | 2,753,007 | 2,828,017 |
| equity_attributable_to_parent | 1,515,371 | 1,515,371 | 1,586,061 |

- 2024 公司/交易所字节相同，数值一致；2025 公司与交易所字节不同但资产负债表数值精确相等（已分别核验）。
- **R = 0**：2025 年报比较列中 2024 两项均与 2024 年报当期列完全相等，未发生重列。
- 未使用总权益（股东权益合计 1,799,548/1,709,863）、流动资产合计、分部或母公司单体（公司列）数据。

归一化（`RMB_MILLION_TO_CNY_10K_X100`，×100 → 万元，均为整数且 < 2^53）：
- 2024 total_assets：275,300,700 万元；2024 equity：151,537,100 万元；
- 2025 total_assets：282,801,700 万元；2025 equity：158,606,100 万元。

## 实施计划

1. Commit 1 `feat: add balance-sheet reconciliation rule`：
   - `reconciliation/engine.py`：新增 `ROE_ROA_DENOMINATOR_RULE_ID/VERSION` 与 `ROE_ROA_DENOMINATOR_RECONCILIATION_RULE`；
   - `validation/validator.py`：微调 `FACT_INSTANT_001`（方案 A）；
   - 新增 Rule 004 单元测试（含相减派生仍被拦截、双源对账放行）。
2. Commit 2 `test: register PetroChina 2025 ROE ROA denominator evidence`：
   - `supplemental/2024_roe_roa_denominators.json`、`supplemental/2025_roe_roa_denominators.json`、
     `restatements/roe_roa_denominators_2024_reviewed_by_2025.json`；
   - Evidence / Context 测试。
3. Commit 3 `test: finalize PetroChina ROE ROA denominator acceptance`：
   - `official_roe_roa_denominator_2025_acceptance.py`（离线 runner，重建 132-fact+63-metric 上游，4 组 Rule 004 对账，R=0，写 run-scoped DuckDB）；
   - `average_balance_input_pairs.json` 输出；
   - 正式报告 `acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md`；
   - Integration 测试。
4. 门禁：Ruff 0.13.2、compileall/import、targeted + full pytest、`git diff --check`、污染检查；
   证明 132 Fact ID、63 Metric Result ID、Stage 2C-C.1/2C-D 受保护文件、Rule 001-003、默认 DB 不变；stash 不动。
5. 逐个 push 3 个提交，local/origin/remote 一致。

## 实际操作

1. 复核 `FACT_INSTANT_001` 阻塞（逐行确认 `validator.py:265-274`、`engine.py:469-471`、`validator.py:_check_reconciled_source`）。
2. 决策：方案 A，微调 `FACT_INSTANT_001` 收窄为“仅拦截相减派生”。
3. Commit 1 `ee0ee7d` `feat: add balance-sheet reconciliation rule`：
   - `reconciliation/engine.py`：新增 `ROE_ROA_DENOMINATOR_RULE_ID/VERSION` 与 `ROE_ROA_DENOMINATOR_RECONCILIATION_RULE`（支持 `total_assets`、`equity_attributable_to_parent`）；
   - `validation/validator.py`：微调 `FACT_INSTANT_001`；
   - `tests/test_roe_roa_denominator_reconciliation_rule.py`：12 项 Rule 004 单元测试（含双源对账放行、相减派生拦截）。
4. PDF 缓存核验：`pdftotext -enc UTF-8 -layout` + PyMuPDF 坐标定位，提取 2024/2025 合并资产负债表；4 份 PDF `cache_miss=0/downloaded=0/hash_verified=4`。
5. Commit 2 `ca6a45e` `test: register PetroChina 2025 ROE ROA denominator evidence`：
   - `supplemental/2024_roe_roa_denominators.json`、`supplemental/2025_roe_roa_denominators.json`、`restatements/roe_roa_denominators_2024_reviewed_by_2025.json`（R=0）；
   - `tests/test_registered_roe_roa_denominator_evidence.py`：10 项证据/Context 测试。
6. Commit 3（进行中）：runner `official_roe_roa_denominator_2025_acceptance.py`（离线，重建 132-fact 上游，4 组 Rule 004 对账，R=0，写 run-scoped DuckDB，输出 `average_balance_input_pairs.json`）；
   `tests/test_official_roe_roa_denominator_2025_acceptance.py`：11 项 Integration 测试；
   正式报告 `acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md`。
7. runner 实跑通过：`status=passed`，R=0，全部动态计数符合，PIT 30/39，平均余额两对 `ready_for_average=true`。

## 验证

- Ruff `0.13.2`：Rule 004 / Evidence / Integration / engine / validator 文件均通过；
- compileall / import：通过（runner 已 `python -m py_compile`）；
- Rule 004 单元测试：`12 passed`；
- Evidence/Context 测试：`10 passed`；
- Integration 测试：`11 passed`（含 protected blob 不变性、132 Fact ID / 63 Metric Result ID digest、默认 DB 不变）；
- 回归（reconciliation + validator + version_chain + m2_facts + earnings_quality_2025_acceptance）：`177 passed`；
- full pytest：`711 passed, 2 warnings`（2 warnings 为与本阶段无关的既有 dateutil 回退）。

## 结果

- 已完成：Rule 004 + FACT_INSTANT_001 微调 + 3 份证据 + 2 个 instant Context + runner + 报告 + 全部测试；
- R = 0（2024 两项 instant 在 2025 比较列未变化）；
- 动态计数全部符合：contexts=7 / facts=144 / raw_ineligible=96 / reconciled_eligible=48 / links=27 / audit=lineage=144 / final PIT=39；
- 不变性：132 Fact ID、38 & 63 Metric Result ID digest、Stage 2C-C.1/2C-D 报告 blob、Rule 001-003、默认 DB 全部不变；
- 当前可用；无遗留问题。

## 最终状态

```text
M2 Stage 2D-A: PASS
2025 ROE/ROA denominator official facts: TRUSTED
2020-2025 instant balance-sheet expansion: ALLOWED
ROE/ROA metric computation: NOT YET
ROIC fact foundation: NOT YET
Scoring: STILL NOT YET
```

## 最终文件变更

新增：
- `src/ashare_research/tools/official_roe_roa_denominator_2025_acceptance.py`
- `tests/test_roe_roa_denominator_reconciliation_rule.py`
- `tests/test_registered_roe_roa_denominator_evidence.py`
- `tests/test_official_roe_roa_denominator_2025_acceptance.py`
- `acceptance/fixtures/official_facts/601857.SH/supplemental/2024_roe_roa_denominators.json`
- `acceptance/fixtures/official_facts/601857.SH/supplemental/2025_roe_roa_denominators.json`
- `acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2024_reviewed_by_2025.json`
- `acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md`

修改：
- `src/ashare_research/reconciliation/engine.py`（新增 Rule 004 常量与规则）
- `src/ashare_research/validation/validator.py`（微调 `FACT_INSTANT_001`）

## 最终Git状态

- 当前分支：`feat/m2-value-assessment-mvp`
- 当前提交：`9e3d1b4b5e1ec24925a3bdf6551ef154fe8966b4`
- 远程 HEAD：`9e3d1b4`（local / origin / remote 一致）
- 是否存在未提交修改：否（worktree clean）
- 是否创建提交：是（3 个提交并逐个 push）：
  - `ee0ee7d` `feat: add balance-sheet reconciliation rule`
  - `ca6a45e` `test: register PetroChina 2025 ROE ROA denominator evidence`
  - `9e3d1b4` `test: finalize PetroChina ROE ROA denominator acceptance`
- 是否执行推送：是（3 次独立 push）
- stash：`stash@{0}` 未动
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（不变）

### Ruff 说明

`ruff check src tests` 报 3 个 `UP038` 警告，全部位于与本阶段无关的既有文件
`src/ashare_research/tools/official_fact_acceptance.py`（2 个）与
`tests/test_official_fact_acceptance.py`（1 个），经核对在父提交 `d19b2c1` 已存在
（前序阶段按“仅检查改动文件”执行 ruff，故未暴露）。本阶段改动的 6 个文件 ruff 全部通过；
按“不随意重构无关代码、不把无关修改混入本次任务”原则，未修改这些既有文件。
