# 工作记录：M2 Stage 2K.1R4F — Post-Percentile North-Star Review and Valuation Scoring Contract Reconciliation

Status: completed

## 基本信息

- 日期：2026-08-07
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`017b656`（R4E.5 CI 全绿后的 tip）
- 任务来源：用户指令 M2 Stage 2K.1R4F
- 对应模块：价值评估（post-percentile scoring north-star review / decision）

## 任务目标

基于已 CI-confirmed 的 R4E.5 trusted percentile profile，重新审查
`valuation_attractiveness` scoring contract，冻结下一阶段 v2 scoring migration
的方法与边界。本轮是 REVIEW / DECISION 阶段，不修改 scoring implementation。

## 范围

- 新增 `reports/petrochina_valuation_scoring_contract_gap_matrix_v1.json`。
- 新增 `docs/post_percentile_scoring_north_star_review.md`。
- 新增 `reports/petrochina_valuation_scoring_migration_plan_v1.json`。
- 新增 `reports/petrochina_post_percentile_scoring_option_matrix_v1.json`。
- 新增 `reports/m2_stage2k1r4f_decision.json`。
- 新增 `acceptance/m2_stage2k1r4f_post_percentile_scoring_north_star_review.md`。
- 新增 `tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`。
- 新增本工作记录。

## 非目标

- 不修改 scoring registry / policy / engine / shadow / sensitivity。
- 不重算 score、不重新运行 sensitivity、不生成生产评分。
- 不创建 registry v2 / policy v2 / shadow v6 / 新 component score。
- 不做 peer acquisition、不做 overall score / rank / recommendation / buy/sell /
  target price / upside probability / portfolio weight / M3。
- 不修改 `src/ashare_research/scoring/*`。
- 不创建 artifact manifest（review-only stage，见 acceptance 说明）。
- 未经明确授权不提交、不推送、不开始 R4F.1。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `017b656`；local == origin（0/0）。
- R4E.5 CI 全绿：run `31151600368` + `31152356097`（Ubuntu/Windows 1665 passed+
  3 skipped，identity-compare pass）。
- 默认 DB SHA `4a71d3c7b88c0b16…`（financial_facts=0，受保护基线）。
- 保护基线：354 Facts / 102 Metric Results / 16 definitions（post-M2 review 记录）。
- R4E.5 decision =
  `PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED`；
  record_count=6、oracle_identical=true、all_windows_ready=true、
  non_production=true、score_eligible=false。
- percentile profile：`petrochina_pit_valuation_percentile_profile_v1`，6 条记录，
  MIDRANK_EMPIRICAL_PERCENTILE，as-of 2026-07-31。
- scoring registry v1：va_pe=`a_share_price_to_latest_annual_parent_earnings`、
  va_pb=`a_share_price_to_latest_year_end_parent_equity`、
  va_ps=`a_share_price_to_latest_annual_revenue`；accepted_contract_versions=
  `value_evaluation_methodology_valuation_pit_v1`；benchmark_mode=
  self_history_percentile；multiple_position=0.60 / yield_position=0.40；
  va_pe/pb/ps/fcf/dividend 各 0.20。
- scoring policy v1：cycle_rule.history_window="3y/5y/expanding PIT percentiles"。
- shadow v5：va_pe 3y=0.9209、va_pb 3y=0.8453、va_ps 3y=0.9209（3y-only 旧分位）；
  va_pe score 7.9092、va_pb 15.4746、va_ps 7.9092；va_dividend_yield coverage_gap；
  valuation_attractiveness score 12.1733 band E ordinal_shadow。
- sensitivity v7：valuation_attractiveness stability_status=NOT_STABLE、
  max_score_delta=3.1637、stability_tolerance=1.0。
- readiness gates v2：影子允许，生产未授权。
- post-M2 north-star review：Decision `M2_SCORING_ADDENDUM_REOPENED`。
- 受保护项：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`、stash、
  默认 DB、registry v4、candidate v2、R4E.5 percentile artifacts、所有现有
  scoring 文件。
- 环境：Python 3.13.9（本地）/ 3.11（CI）。

## 实施计划

1. 建工作记录（本文件）。
2. 核验仓库起点（分支/HEAD/origin/worktree/stash/CI/DB/artifacts/protected）。
3. 生成 Gap Matrix（现状 scoring contract vs trusted R4E.5 contract）。
4. 生成 North-Star review 文档（参考成熟设计：MADR、SemVer 思想）。
5. 生成 Option Matrix（5 种 window 方案，固定评价轴，不用实际 percentile）。
6. 生成 Migration Plan。
7. 生成 R4F Decision。
8. 新增 acceptance。
9. 新增小型静态决策测试。
10. 全量验证（pytest R4F / pytest / ruff / git diff --check）。
11. 更新工作记录。

## 决策记录

本轮为 REVIEW / DECISION，核心工程决策：

- **决策内容**：冻结 `DUAL_WINDOW_SINGLE_COMPONENT` 作为 v2 迁移窗口模型，
  每个 `va_pe/va_pb/va_ps` 保持单组件、绑定 `percentile_3y + percentile_5y`，
  权重 0.5/0.5，`dual_window_percentile = (p3y + p5y) / 2`，Decimal-only，
  `aggregation_contract_version = self_history_dual_window_percentile_v1`。
- **采用原因**：同时使用 3y+5y 可信证据，不丢弃任一窗口；不把同一经济信号
  计两次；不增加自由参数；保持三组件拓扑；确定性、可解释、PIT 精确。
- **考虑过的替代方案**：THREE_YEAR_ONLY（丢弃 5y，违背双窗口意图）、
  FIVE_YEAR_ONLY（丢弃 3y）、SIX_SEPARATE_COMPONENTS（六组件双重计权）、
  EVIDENCE_CARD_ONLY_NO_SHADOW_REFRESH（过度保守）。
- **未采用替代方案的原因**：见 option matrix；其中六组件因双重计权被否决。
- **决策基础**：仅方法属性（North Star、既有冻结策略、避免双重计权、
  可解释性、PIT、确定性、既有拓扑、最少自由参数），不以 PetroChina 实际
  percentile 作为方法选择依据（HARD_RULE_NO_PERCENTILE_PEEKING）。
- **潜在风险**：registry v2/policy v2 迁移工作量；PE 周期上下文契约必须在
  PE 数值评分前设计；shadow 刷新后必须重跑完整 sensitivity。
- **提交前补充**（按用户提交指令）：decision artifact 显式补充
  `expanding_percentile = DEFERRED_NOT_REQUIRED`、`semantic_migrations`
  （va_pe ANNUAL→PE_A_TTM、va_pb YEAR_END→PB_A_MRQ、
  va_ps ANNUAL→PS_A_TTM）、PE 显式字段
  `pe_numeric_scoring_authorized = false`、
  `pe_blocked_reason = cycle_context_contract_required`、
  `pe_missing_not_zero / pe_component_not_deleted /
  pe_weight_not_reassigned / registered_weight_topology_unchanged = true`；
  对应新增 3 项静态断言（PE-block-not-zero、semantic migrations、
  expanding DEFERRED_NOT_REQUIRED）。

## 实际操作

1. 核验仓库起点：分支 `feat/m2-value-assessment-mvp`，HEAD `017b656`，
   local == origin（0/0），stash 存在，默认 DB SHA
   `4a71d3c7b88c0b16…` 未变，受保护项未动。
2. 读取 scoring 相关 artifact：registry v1、policy v1、shadow v5、
   sensitivity v7、readiness gates v2、post-M2 north-star review、
   R4E.5 decision / percentile profile / contract / record。
   捕获迁移所需精确契约字符串与 6 条 percentile_record_id。
3. 新建本工作记录。
4. 新建 `reports/petrochina_valuation_scoring_contract_gap_matrix_v1.json`
   （7 项 gap：va_pe/va_pb/va_ps semantic、history_windows、
   percentile_methodology、pe_cycle_handling、production_state）。
5. 新建 `docs/post_percentile_scoring_north_star_review.md`（23 节，
   含 §2 引用 MADR 与 SemVer 思想、§5 五窗口方案、§22 证据-only percentile）。
6. 新建 `reports/petrochina_post_percentile_scoring_option_matrix_v1.json`
   （5 方案 × 10 固定轴，选 D；governance_note 声明不以实际 percentile 定案）。
7. 新建 `reports/petrochina_valuation_scoring_migration_plan_v1.json`
   （current v1 / target v2、受影响组件、窗口契约、双窗口聚合、cycle guard、
   old-shadow 状态、显式未授权项、next artifacts）。
8. 新建 `reports/m2_stage2k1r4f_decision.json`（decision、
   所选窗口契约、PE 阻塞、PB/PS 非生产允许、production NOT_AUTHORIZED、
   overall PROHIBITED、next_stage=R4F1）。
9. 新建 `acceptance/m2_stage2k1r4f_post_percentile_scoring_north_star_review.md`
   （VERDICT PASS、各边界、artifact_manifest=NOT_REQUIRED_REVIEW_ONLY_STAGE）。
10. 新建 `tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`
    （19 个静态只读测试；EVIDENCE_ONLY_PERCENTILES 作为 sentinel，
    断言不得进入 option 论证）。
11. 修正测试：R4E5 decision 键为 `decision`（非 `decision_value`）；
    profile 字段为 `records`/`metric_id`/`window_id`；南星文档断言子串
    避开加粗与换行；ruff E501/F401/W292 修复。
12. 全量验证并更新本记录。

## 数据与方法说明

- 数据来源：CI-confirmed 的 R4E.5 trusted percentile profile
  （`petrochina_pit_valuation_percentile_profile_v1`，6 条记录，
  MIDRANK_EMPIRICAL_PERCENTILE，as-of `2026-07-31`），未重新抓取、未重算。
- 本轮为 review-only：不计算任何 score，不运行 sensitivity，不写默认 DB。
- 6 条 percentile 的实际数值仅作为证据展示（§22），不参与方法选择。
- 方法选择依据仅方法属性（§4 HARD RULE）。

## 验证

- `pytest tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`：
  **22 passed**（静态只读，未写、未抓取、未算分；含提交前补充的 3 项
  PE-block/semantic-migration/expanding 断言）。
- `pytest`（全量离线）：**1690 passed, 2 warnings**（新增 R4F 22 项较此前
  1668 增加，2 条为既有 pandas dateutil warning）。
- `ruff check tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`：
  **All checks passed**。
- `git diff --check`：**pass**。
- JSON 解析校验：所有 R4F JSON artifact 可正常 `json.load`。
- 受保护项（`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`、
  stash、默认 DB、registry v4、R4E.4/R4E.5 artifacts、scoring 文件）未动。

## 结果

- 已完成：Gap Matrix、north-star review 文档、option matrix、migration plan、
  R4F decision、acceptance、静态决策测试、工作记录。
- 决策：`VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`；
  `DUAL_WINDOW_SINGLE_COMPONENT`；`EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN`；
  PE 数值评分 `BLOCKED_PENDING_CYCLE_CONTEXT_GUARD`；PB/PS 非生产允许；
  production NOT_AUTHORIZED；overall PROHIBITED；next_stage=R4F1。
- 未完成/未开始：registry v2、policy v2、shadow 刷新、sensitivity 重跑、
  R4F1 迁移实现（均属后续 R4F1，需另行授权）。
- 与本任务对比：无偏差；REVIEW/DECISION 阶段边界保持。
- 可用性：本轮为 review-only，无可运行产品行为变更。

## 遗留问题

- PE cycle-context 形式化契约尚未设计，PE 数值评分保持阻塞。
- shadow v6 刷新后必须重跑完整 sensitivity（migration 计划已冻结该要求）。
- R4F1 尚未开始，需用户明确授权。

## 下一步建议

- R4F.1（Valuation Scoring Contract v2 Migration and Non-Production Shadow
  Refresh）——按本计划创建 registry v2 / policy v2、刷新非生产 shadow v6、
  重跑完整 sensitivity。需另行授权后方可开始。

## 最终文件变更

- 新增：`reports/petrochina_valuation_scoring_contract_gap_matrix_v1.json`
- 新增：`docs/post_percentile_scoring_north_star_review.md`
- 新增：`reports/petrochina_post_percentile_scoring_option_matrix_v1.json`
- 新增：`reports/petrochina_valuation_scoring_migration_plan_v1.json`
- 新增：`reports/m2_stage2k1r4f_decision.json`
- 新增：`acceptance/m2_stage2k1r4f_post_percentile_scoring_north_star_review.md`
- 新增：`tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`
- 更新：本工作记录
- 未修改任何 scoring registry / policy / engine / shadow / sensitivity。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；HEAD `017b656`（未变）。
- 未提交修改：上述 R4F 新增文件均未跟踪（`??`）；另有既有受保护修改
  `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`、
  `AGENTS.md`、`agent/goals/`（未动）。
- 未创建提交、未打 Tag、未推送（按指令：未经明确授权不提交不推送）。