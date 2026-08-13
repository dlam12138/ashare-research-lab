# 工作记录：M2 Stage 2F 中国石油现金分红兑现事实与透明指标

## 基本信息

- 日期：2026-08-01
- Agent：Codex
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`118c05e63b6e559e10649c5b891e3fc09e8dd5d4`
- 任务来源：goal objective `M2 Stage 2F`
- 对应模块：价值评估 / 数据底座 / 工程治理

## 任务目标

建立中国石油 2021—2025 A 股人民币现金分红兑现事实、事件链、回购事件扫描、PIT
回放和四类描述性 Metric。只有正式分红实施公告支持的现金分红进入 canonical
兑现事实；方案、批准和实施公告分层保留，不相互冒充。普通年度或回购事件缺口显式
记录，不把缺口写成零。

## 初始复核与冻结

- 未发现根目录 `AGENTS.md`；已阅读 `agent/agent.md`、`agent/record/README.md`、
  North-Star review、roadmap、scoring gates、Stage 2B-B/2D-F/2E-B 文档及最近记录。
- 起始 HEAD 为 `118c05e`，worktree clean，分支与 origin 一致；stash 保持既有
  `protect pre-existing Stage 1B.4 record edit before Stage 1C`，不触碰。
- 冻结 Stage 2E-B 事实层 `354 Fact`、组合 `102 Metric Result`、`16 definitions`、
  ROE/ROA、财务安全、Rule 001—006、默认 `data/research.duckdb`（SHA-256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`）和受保护文件哈希。
- 初始 North-Star 结论：财务安全已完成；ROIC 因 NOPAT/投入资本边界仍 blocked；
  估值仍需 PIT 价格、股本和市值合同；分红兑现可直接回答价值返还并为未来股息率输入
  提供实施口径。本阶段不进入估值计算、ROIC 或评分。

## 参考裁剪

记录 OpenBB provider→mapping→standard model、FinanceToolkit reported fact→derived
metric、Arelle Fact/Context/Unit 与 duration/event、OpenLineage run/input/output 的
分层和血缘思想；不引入外部框架、网络依赖、自动交易或黑箱评分。

## 范围与非目标

- 允许修改：新增 dividend realization evidence/events、Rule007 additive contract、
  分红指标 registry/engine extension、离线 runner、测试、报告、acceptance、roadmap
  append-only 和本记录。
- 不修改：Fact Schema/Identity/PIT、旧 354 Fact/102 Result/16 definitions、ROE/ROA、
  财务安全、Rule 001—006、默认 DB、stash、main、Tag/Release。
- 非目标：股息率、目标价、估值、ROIC、评分、阈值、评级、买卖建议。

## 实施计划

1. 盘点 2021—2025 公司官网/上交所正式公告与本地 PDF cache，建立事件状态和双官方证据。
2. 新增 Rule007、必要的事件 JSON、canonical dividend Facts 与四类透明 Metric。
3. 重建并冻结旧 354 Fact/102 Result/16 definitions，离线回放 PIT、事件更正和回购扫描。
4. 增加 targeted/full tests、报告、acceptance 和 append-only roadmap；执行全量门禁。
5. 按提交逐个 push，最终确认 worktree、local/origin/remote、stash 和默认 DB 不变。

## 初步工程观察

- 基础 ConceptRegistry 已有 `cash_dividend_total`、`cash_dividend_per_share`、`share_capital`、
  `shares_repurchased`、`repurchase_amount`，优先复用，不升级 Schema。
- 现有官方 filing provider 仍是 manual-facts canonical 入口；正式 runner 必须只读 committed
  evidence JSON 和临时 foundation，不调用 provider、网络、PDF/cache 或默认 DB。
- 既有 Metric Engine 支持 role-bound facts、Decimal prec28、ROUND_HALF_EVEN、PIT available_at
  和 lineage，可通过 additive registry/runner 扩展，不改旧公式语义。

## 数据与方法约束

- 只接受 A 股人民币普通股或明确合并口径；H 股、外币、不同股本基数隔离，不混算。
- `source_fiscal_year` 归属报告年度，不按支付年份归属；中期和末期实施事件分别记录后再透明汇总。
- 方案、股东大会批准、实施公告和 payment event 分层；只有 implementation/payment evidence
  可进入兑现计算。缺失不填零。
- 回购扫描若无实施事件只登记 `bounded_search_no_event_found`，不生成零值 Fact。
- 分红金额、每股分红、股本和回购数值的双官方对账必须精确匹配；事件日期用 committed
  `DividendEventRecord v1`，不改通用 Fact Schema。

## 当前状态

- 状态：`in_progress`
- 已完成：目标读取、基线冻结、相关方法/实现/历史产物阅读、记录先行。
- 尚未完成：官方分红/回购证据核验、代码、测试、正式 runner、报告、全量门禁和 push。

## 官方证据核验完成

- 逐年核验 2021—2025 interim/final 实施公告，共 10 条 `paid/implemented` 事件；每条
  保留公司官方与上交所官方定位、公告日、股权登记日、除息日、发放日、每股金额和总额。
- 2025 final 实施公告日期为 2026-06-18，故在 2026-03-30 年报 PIT 明确保持不可见；
  run latest 固定为 2026-07-01，仅用于离线完整回放。
- 2021—2026 有界回购扫描未发现已实施回购事件，登记为
  `bounded_search_no_event_found`，没有创建零值 Fact。

## 实现完成

- 新增 `RECON_OFFICIAL_NUMERIC_007 v1`，只扩展现金分红/股本/回购数值的精确 Decimal
  对账；Rule 001—006 与 Fact/Metric Schema 不变。
- 新增 canonical dividend event contract、10 条事件台账、5 年 supplemental official
  fact contract、四个 non-scoring realization Metric、事件列表 role binding engine 和
  离线 runner。runner 从 Stage 2E-B foundation 重建，隔离 default DB、网络、PDF/cache。
- Stage 2F 正式验证 run `stage2f_validation_20260801e`：旧 354 Fact 保持，Rule007 新增
  90 Fact（30 reconciled eligible），20 个 dividend Result、20 computed、60 lineage；
  FY2025 `not_yet_reviewable`。
- 已新增验收文档：`acceptance/m2_stage2f_petrochina_dividend_realization.md`。

## 测试与待完成门禁

- Stage 2F targeted tests：`9 passed`；覆盖定义/方法、canonical ID、Rule007、事件链、
  role/lineage、零/缺失/raw 边界、PIT、无 ROIC/score、幂等重跑。

## 最终门禁与交付

- 全量 pytest：`920 passed, 2 warnings`；全仓 Ruff、compileall/import、`git diff --check`、
  污染检查均通过。
- 正式 runner `stage2f_validation_20260801e`：`passed`；354 旧 Fact、102 旧 Metric Result
  ID/语义、默认 DB SHA-256、stash 与旧保护 blob 均保持；Rule007 新增 90 run-scoped Fact。
- 三个提交已逐个推送到 `origin/feat/m2-value-assessment-mvp`：
  `2cec1b4`（feature）、`214fcd6`（tests），当前文档提交待完成后复核。
- 当前状态：`M2 Stage 2F PASS`；Dividend implementation facts `TRUSTED`；Payout/cash-flow
  coverage metrics `TRUSTED`；Repurchase evidence `DOCUMENTED`；Dividend realization layer
  `COMPLETE`；Valuation PIT foundation `ALLOWED`；ROIC `NOT YET`；Scoring `STILL NOT YET`；
  Next-stage selection `NORTH-STAR REVIEW REQUIRED`。
