# M2 Stage 2G.1 — Trusted-Lineage Closeout

日期：2026-08-02
状态：**PASS WITH EXPLICIT GAPS**
范围：仅收口 Stage 2G 的 Rule007、canonical Fact/PIT 血缘、证据股本时间线和风险否决项语义；未启动 ROIC、评分、Web、市场机制、目标价或推荐。

## 1. 起点与保护对象

- 起点分支：`feat/m2-value-assessment-mvp`
- 起点 HEAD：`61e4f5eb5e1642246a69ccfac895c21459fead20` (`61e4f5e`)
- 默认 DB：`data/research.duckdb`，formal runner 不打开、不初始化、不写入。
- 既有 stash 保留：`stash@{0}`，Stage 1B.4 保护记录未改动。
- 既有 354 Fact / 102 Metric Result / 16 definitions、Fact Identity/PIT/version-chain 测试及历史提交未重写。

## 2. Rule007 与 Phase A

Phase A 仍为 `pass_with_explicit_gaps`：10 个事件、20 个登记 source、1 个双官方独立事件、9 个交易所证据缺口。`designated_disclosure_platform` 未被重标为 issuer official；URL locator hash 未被当作 content hash。

raw Fact 现在逐 source 读取以下 payload：

| Event concept | Source payload key |
|---|---|
| `cash_dividend_total` | `extracted_values.cash_dividend_total` |
| `cash_dividend_per_share` | `extracted_values.cash_dividend_per_share` |
| `share_capital_on_record_date` | `extracted_values.share_capital` |

event 数值只做交叉检查；reconciled value 来自两个独立 raw Fact 的公共值，`input_fact_ids` 精确覆盖两份 raw Fact。source payload 不一致会产生 `numeric_or_scope_conflict` 并取消 Rule007 eligible 输出。announcement window 和 payment window 仍使用独立语义。

## 3. Canonical Fact/PIT 血缘

formal CLI 现在要求显式 `--fact-db <read-only canonical DB>`；缺失输入直接报告 `missing_input`，没有 fixture fallback、`ANNUAL_AVAILABLE_AT` 或 `SHARES` fallback。正式 run 使用的逻辑输入标识如下：

- logical name：`net_profit.duckdb`
- schema：`2.1`
- input DB SHA-256：`47a09e98a8062f72b6907bc6ec55927588e4a815517ba8b4c0b595507ada7f0e`
- Fact 总数：`201`；`eligible_for_metrics`：`67`
- 实际使用 canonical Fact：`33` 个原始 `fact_id`
- required coverage：net profit `7`、equity `8`、revenue `6`、operating cash flow `6`、capex `6`
- Canonical Identity：PASS；version chain：PASS

实现通过既有 `FactRepository.query_facts()`、`FactRepository.get_latest_available()`、`AsOfQuery` 和 `FactService.query_as_of()` 读取；输出保留原始 `fact_id`、`context_id`、`concept_version`、`source_id/source_tier`、`fact_version`、`restatement_version`、`supersedes_fact_id`、公告/申报/可得日期、验证字段、source hash 及 lineage。每个估值日仍满足 `available_at <= trade_date`。

## 4. Evidence-driven 股本时间线

`ordinary_share_capital_timeline_v1` 由 11 条登记 source evidence ledger 生成，折叠为 10 个有效区间；每行均保留 `evidence_ids`，并验证存在 A/H 字段时 `A + H = total`。当前登记 payload 提供了总普通股本和 A/H entitlement scope，但没有 A/H 拆分字段，因此该拆分被列为显式 gap；估值仍仅使用有证据的 `total_ordinary_shares`，不补入隐藏常量。首个证据生效日前的区间保持缺失，不提前使用未来股本。

乘以 A 股收盘价的诊断名称仍为：`a_share_price_implied_total_ordinary_equity_value`，没有改成 canonical market cap。

## 5. 风险否决项语义

输出改为 `risk_veto_checks`，只使用允许状态：

- `future_data_leakage`: `not_observed_within_bounded_evidence`
- `canonical_identity_break`: `not_observed_within_bounded_evidence`
- `official_exchange_evidence_gap`: `observed`
- `non_positive_comparable_input`: `not_observed_within_bounded_evidence`
- governance / audit / related-party：`not_evaluated`

因此，控制通过不再被错误标为 risk observed；实际存在的交易所证据缺口仍明确为 observed，未研究风险没有被写成“无风险”。

## 6. Old → New 差异

| 项目 | Stage 2G 原实现 | Stage 2G.1 收口后 |
|---|---|---|
| 财务输入 | acceptance fixture + runner 生成 `fact_*` ID | 显式只读 canonical Fact DB，原始 Identity/lineage 保留 |
| PIT 日期 | `ANNUAL_AVAILABLE_AT` 手工表 | canonical `available_at` + 现有 PIT latest/version 选择 |
| 估值数值 | 旧报告最新值：P/E `12.89158710139375214555441126`、P/B `1.278558916853412321468089815`、P/S `0.7079400874030893683960273264`、FCF proxy yield `0.05903773727554334316827771199` | 数值保持一致；lineage ID 改为 canonical：`9009db…`、`45a891…`、`460056…`、`ad3b6e…` + `5dc4c3…` |
| 股本 | `SHARES` 常量 + 单一 URL | 11 条 source evidence ledger → 10 个 evidence-bounded intervals |
| Rule007 | raw value 共享 `event[concept]` | raw value 逐 source `extracted_values`；reconciled 精确引用两 raw IDs |
| 风险语义 | Identity/PIT 等控制被写成 observed | 控制为 not observed；真实 exchange gap 为 observed；未研究项为 not evaluated |

## 7. Formal 输出与边界

- run id：`stage2g_valuation_pit_20260801`
- market：`2021-01-04` 至 `2026-07-31`，`1,351` 行，复用既有 `stock_daily` model
- observations：`8,106`
- Rule007：`6` raw Facts、`3` reconciled Facts、`1` eligible event
- network used：`False`
- default DB mutated：`False`
- formal offline 两次逐文件 hash：PASS（byte-idempotent）
- profile：descriptive only，`score_eligible=false`

仍明确不做：ROIC、评分闭环、市场机制、Web、目标价、买卖推荐、自动交易。

## 8. 验收命令与结果

本次 Stage 2G 定向套件新增 Rule007 source mutation、event/source 分离、share evidence mutation/removal/inconsistency 和 canonical input 测试；当前定向结果为 **13 passed**。全仓收集到 **933 tests**，分片执行全部通过；Fact Identity、PIT、version-chain、protected baseline、Ruff、compileall 和污染检查均通过。
