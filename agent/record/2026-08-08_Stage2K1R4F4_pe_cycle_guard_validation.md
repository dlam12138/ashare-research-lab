# 工作记录：M2 Stage 2K.1R4F.4 — 3Y Historical Normalized-PE Cycle-Guard Validation

Status: completed（closeout：committed + pushed + CI PASS；reviewer correction 已应用）

## 基本信息

- 日期：2026-08-08
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`c38b75a`（R4F.3A closeout，final tip CI PASS）
- 任务来源：用户指令 M2 Stage 2K.1R4F.4
- 对应模块：价值评估（3Y historical normalized-PE cycle-guard validation）

## 任务目标

验证 PIT-safe AVERAGE_ROE_X_CURRENT_BVPS normalized-earnings denominator
是否在 3Y PIT 窗口内提供可重复的机械 guard（当 current TTM EPS 高于
normalized proxy 时，raw PE 被机械压低而 normalized PE 不跟随）。

具体验证 A/B/C/D 四问：
A. 真实 3Y PIT series 确定性重建（728 天）；
B. 多个独立 denominator states 出现；
C. current EPS > normalized EPS → raw PE < normalized PE 的必然方向关系；
D. 无 PIT/restatement/state-transition/identity 异常。

## 范围

- 新增：contract v1、docs、纯函数模块 `pe_cycle_guard_validation.py`、
  薄 CLI、7 份 reports（series/ledger/audits/divergence/percentile/decision）、
  tests、acceptance、work record。
- 生成：3Y normalized-PE series（728 天）、denominator-state ledger
  （normalized/raw state ID，run-length segmentation）、direction audit、
  recurrence audit（预注册 gate）、transition audit、divergence diagnostic、
  normalized 3Y percentile（MIDRANK，DuckDB oracle）。
- 复用：R4F.3 resolver（ROE/BVPS/normalized EPS/PE）、R4F3A overlay、
  R4E4 PE_A_TTM observations、R4E5 percentile 方法（MIDRANK）。

## 非目标

- 不 commit / 不 push / 不开始 R4F.4A / 不修改 PE scoring。
- 不恢复 PE numeric score；不产生 valuation score；不做 cycle-stage
  classification（PEAK/TROUGH 等术语禁止）；不做未来收益预测/回测。
- 不修改 R4F3 `normalized_earnings_state_id`（历史 artifact identity 冻结）。
- 不修改 registry v2 / policy v2 / shadow v6 / sensitivity v8 / capsule v5。
- 不修改 R4F3A committed artifacts、default DB、calendar v1。
- 不生成 5Y percentile；不把 normalized percentile 接入 scoring。
- 不引入 sklearn/scipy runtime dependency；不复制第二套 resolver。
- 不用 close/PE 反推 current EPS（除非 cross-check）。
- 不把 728 daily rows 当 728 独立样本。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `c38b75a`；local == origin；
  R4F.3A final tip CI（run 31234602290）全绿。
- R4F3A decision = `PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED`；
  3Y 728/728/0；5Y BLOCKED；full_cycle NOT_PROVEN；PE scoring
  BLOCKED_UNCHANGED；val_dim NONE。
- 保护项：`m2_stage2i2r`（1 行修改）、`AGENTS.md`、`agent/goals/`、
  `2026-08-08_01_*.md`（核验记录）；stash=1；默认 DB SHA `4a71d3c7…`。
- 上游产物：R4F3A overlay（165+8=173 facts）、R4E4 candidate v2
  （1351 PE_A_TTM observations）、R4E5 percentile profile。

## 实施计划

1. 建工作记录（本文件）。
2. 只读研究 R4E4/R4E5/R4F3 resolver 结构与 R4E5 MIDRANK oracle 模式。
3. contract v1 + 方法文档。
4. 核心模块 `pe_cycle_guard_validation.py` + 薄 CLI。
5. 构建 7 份产物；A/B byte-identical；DuckDB oracle。
6. 写 40+ 项测试；回归 + full pytest + ruff + compileall + diff check。
7. decision + acceptance + 工作记录；本地 STOP。

## 决策记录

- **series ratio 恒等**：`normalized_pe/raw_pe == ttm_eps/normalized_eps`
  从 EPS 操作数计算（close 抵消），不从舍入的 PE 中间值相除，保证
  byte-for-byte 恒等（初版从中间值相除产生末位 ulp 差异，已修正）。
- **raw TTM state identity**：直接绑定 R4E.4 `financial_state_id`
  （官方上游，13 个 state），不另造 identity；禁止 close/PE 反推 EPS。
- **normalized denominator state identity**（R4F4 新增）：payload 仅含
  contract/ROE 年/事实 ID/current equity+share/avg ROE/BVPS/norm EPS，
  不含 date/price/PE；13 个 episode 级 state（与 13 个 raw state 对齐）。
- **R4F.3 `normalized_earnings_state_id` 保持逐字节不变**（含 as_of 的
  历史 artifact identity），R4F4 通过新增 identity 解决 episode 分析。
- **recurrence gate 预注册**：≥2 distinct raw states 且全部方向一致 →
  REPEATED；gate 在看结果前冻结于 contract。
- **current equity 修改测试**：2023-07-31 时点 current equity 是
  2023-03-31 MRQ fact（effective 2023-05-04），非 2026-03-31。

## 实际操作

### 起点核验（2026-08-08）

- 分支 `feat/m2-value-assessment-mvp`；HEAD `c38b75a`；local == origin。
- R4F3A gate：decision TRUSTED_ALLOWED；3Y 728/728/0；5Y BLOCKED；
  full_cycle NOT_PROVEN；PE BLOCKED_UNCHANGED；val_dim NONE。
- 保护项未动；stash=1；DB SHA `4a71d3c7…`。

### 上游研究（只读）

1. R4E4 candidate v2：PE_A_TTM 1351 obs；3Y 窗口 728 obs 全部 computed，
   含 `financial_state_id`（13 distinct，21-101 天/state）、
   `per_share_denominator_decimal`、`ratio_decimal`、`share_basis_decimal`。
2. R4E5 percentile profile：PE_A_TTM 3y midrank 91.964286（N=728，
   L=668 E=2 G=58，rank 1339/1456）——raw PE 3y percentile 绑定源。
3. R4F3 resolver：`build_normalized_earnings_state`（state_id 含 as_of）、
   `build_normalized_pe_state`（raw/normalized PE、ratio）。

### contract + docs（任务 11）

4. `config/pe_3y_cycle_guard_validation_contract_v1.json`：窗口/方法/
   direction 定义/recurrence gate（≥2）/样本语义（728≠728 独立）/术语禁令/
   边界/决策 4 态。
5. `docs/pe_3y_normalized_pe_cycle_guard_validation.md`：参考与裁剪记录。

### 核心模块 + CLI（任务 13）

6. `src/ashare_research/pit_valuation/pe_cycle_guard_validation.py`：
   series/identities/ledger/direction/recurrence/transition/divergence/
   percentile/decision 全部纯函数；复用 R4F.3 resolver。
7. 薄 CLI `m2_stage2k1r4f4_pe_cycle_guard_validation.py`
   （build/verify/oracle/fixtures）。

### 构建 + A/B + oracle（任务 14）

8. build：728/728 series；13 raw + 13 norm + 13 paired states；
   direction violations=0；644 protective days / 11 distinct raw states /
   1 segment；recurrence=REPEATED；transitions 12/12 orphan=0；
   percentile 22.321429（L=161 E=2 G=565，rank 325/1456）。
9. DuckDB oracle：N=728 L=161 E=2 G=565 rank=325/1456 pct=22.321429
   —— python 完全一致。
10. restatement 扰动：later restatement（2025-06-02 生效）对历史行
    零影响。
11. A/B：7/7 byte-identical（多次重跑确认）。

### tests + 全量验证（任务 15）

12. 46 项测试；修复 4 个断言问题（ratio 恒等从 EPS 操作数计算、
    current equity 用 2023-03-31 MRQ、percentile 断言 ×100 有理式、
    contract 字段嵌套）。
13. ruff 20 项修复（F401/SIM110/B007/B905）→ All checks passed。
14. 回归：R4F3A 48 / R4F3 45 / R4F2 35 / R4F1 19；full pytest
    **1883 passed, 2 warnings**（4m45s）。
15. compileall / git diff --check PASS；scoring zero-change；DB SHA 未变；
    stash 未动；secret/path 扫描 clean。

## 验证

- R4F4 测试：**49 passed**（含 3 项 identification 回归，reviewer correction 后）。
- 全量：full pytest 重跑见任务 19（修正后执行）。
- ruff / compileall / diff-check：全绿。
- A/B：7/7 byte-identical。
- oracle：python == DuckDB（N/L/E/G/rank 完全一致）。
- before/after：R4F.3 state ID 逐字节一致；R4F3A artifacts 未动。
- 默认 DB SHA `4a71d3c7…` 未变；stash 未动；保护项未动。

## Reviewer correction（2026-08-08，R4F.4 REVIEW CORRECTION）

识别问题：direction relation（current_eps > normalized_eps ⇒
normalized_pe > raw_pe）由 PE 算式代数恒等保证，不能单独作为 empirical
cycle-guard validation 证据。已按指令修正（未删除任何工程成果）：

1. **verdict**：PASS → **CONDITIONAL PASS — LOCAL CANDIDATE**。
2. **decision**：SUPPORTED_5Y_CONFIRMATION_REQUIRED →
   **PE_3Y_NORMALIZED_PE_MECHANICAL_GUARD_CONFIRMED_INDEPENDENT_CYCLE_VALIDATION_REQUIRED**。
3. **direction audit 保留**（728 rows / 644 days / 11 states / 1 segment /
   0 violations），重命名为 `mechanical_direction_consistency = PASS` +
   `algebraic_guard_consistency = PASS`，明确写出代数恒等理由与
   `not_independent_empirical_cycle_evidence = true`。
4. **recurrence 降级**：`CONDITION_OBSERVED_ACROSS_MULTIPLE_DENOMINATOR_STATES`
   （非 independently replicated）；`protective_direction_segments = 1`
   + 说明"one contiguous regime ≠ multiple independent cycle episodes"；
   `independent_protective_episodes = NOT_ESTABLISHED`。
5. **identification gates 新增**（decision.gates）：
   mechanical_relation_excluded_as_empirical_evidence=true、
   independent_cycle_context_evidence_present=false、
   cycle_stage_identified=false、cycle_guard_empirically_validated=false、
   normalized_earnings_mid_cycle_validated=false；evidence 增加
   mechanical_denominator_guard=CONFIRMED、
   normalized_earnings_as_valid_cycle_proxy=NOT_YET_VALIDATED、
   cycle_guard_empirical_validation=NOT_ESTABLISHED。
6. **percentile 保留**（22.321429 / oracle PASS），comparison_status =
   DESCRIPTIVE_DENOMINATOR_NORMALIZATION_COMPARISON，明确"分位差只证明
   denominator 选择改变历史估值位置，非 normalization 正确性证据"。
7. **identification 回归测试 +3**（49 项）：代数恒等（任意 positive
   price/eps/norm_eps，200 组随机）、mechanical consistency 不能设置
   cycle_guard_empirically_validated / 不能触发 scoring、identification
   gates 断言。
8. **next stage**：R4F.4A_INDEPENDENT_CYCLE_CONTEXT_VALIDATION_PREFLIGHT
   （冻结非由 PE 算式定义的 cycle-context contract）；5Y remaining 4 facts
   = DEFERRED_PENDING_IDENTIFICATION_REVIEW（非取消）。
9. 工程成果不变：728/728、13/13/13 states、644 days、11 states、1 segment、
   0 violations、0 orphans、22.321429、normalized_denominator_state_id 设计、
   R4F3 state ID byte-compatible。

## 结果（修正后）

- 决策：**PE_3Y_NORMALIZED_PE_MECHANICAL_GUARD_CONFIRMED_INDEPENDENT_CYCLE_VALIDATION_REQUIRED**
  （**CONDITIONAL PASS**）——mechanical guard CONFIRMED；independent cycle
  validation NOT_ESTABLISHED（需 R4F.4A preflight）。
- 3Y series 728/728 TRUSTED；PIT/restatement PASS；mechanical inversion
  PASS；percentile oracle PASS。
- 边界保持：full_cycle NOT_PROVEN；5Y BLOCKED；PE scoring
  BLOCKED_UNCHANGED；cycle stage 未识别；无未来收益测试。
- 未 commit、未 push（本地验证阶段，按授权边界停止）。

## 遗留问题

- **independent cycle-context validation 未建立**——R4F.4A preflight 需
  冻结不由 raw/norm PE 算式定义的、可证伪的 cycle-context contract。
- 5Y remaining 4 facts DEFERRED_PENDING_IDENTIFICATION_REVIEW（先确认
  "补完以后要验证什么"，非取消）。
- full_cycle NOT_PROVEN（单一 issuer、无独立周期证据）。
- 未来收益预测属独立机制研究（OUT_OF_SCOPE，未混入本 gate）。

## Closeout（2026-08-08，用户授权）

1. commit `25c182b`（feat: validate 3y normalized PE mechanical guard，
   12 文件）+ `f3b37cb`（docs: record R4F.4 conditional local closeout）+
   `3b8fe15`（fix: restatement test clean-clone safe）。
2. push `c38b75a..3b8fe15`；local == origin。
3. CI run 31239398738（f3b37cb）失败：`test_later_restatement_does_not_alter_history`
   加载 gitignored `tmp/r4f4_synthetic_later_restatement.json` →
   FileNotFoundError（双平台，与 R4F3A 同型问题）→ `3b8fe15` 改为内联
   构造合成 facts，本地 1886 全绿。
4. CI run 31239685208（3b8fe15）：**三作业全绿**（Ubuntu/Windows
   clean-clone + identity-compare）。
5. 本 closeout（acceptance/work record 补 CI 证据）→ push → final-tip CI。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；HEAD `3b8fe15`（R4F4 实现 tip，
  CI PASS）；local == origin。
- 3 笔提交已推送：`25c182b`、`f3b37cb`、`3b8fe15`。
- 保护项未动；stash 未动；默认 DB SHA 未变。

## 下一步建议

- R4F.4A（Independent Cycle-Context Validation Preflight）——需另行授权；
  冻结不由 PE 算式定义的 cycle-context contract；5Y 补数
  DEFERRED_PENDING_IDENTIFICATION_REVIEW；不授权 scoring。
- final-tip CI 全绿后 R4F4 正式关闭（CONDITIONAL PASS — CI CONFIRMED）。

## 最终文件变更

新增：
- `config/pe_3y_cycle_guard_validation_contract_v1.json`
- `docs/pe_3y_normalized_pe_cycle_guard_validation.md`
- `src/ashare_research/pit_valuation/pe_cycle_guard_validation.py`
- `src/ashare_research/tools/m2_stage2k1r4f4_pe_cycle_guard_validation.py`
- `reports/petrochina_pe_3y_normalized_pe_series_v1.json`
- `reports/petrochina_pe_3y_denominator_state_ledger_v1.json`
- `reports/petrochina_pe_3y_cycle_guard_direction_audit_v1.json`
- `reports/petrochina_pe_3y_denominator_transition_audit_v1.json`
- `reports/petrochina_pe_3y_raw_vs_normalized_divergence_v1.json`
- `reports/petrochina_pe_normalized_3y_percentile_profile_v1.json`
- `reports/m2_stage2k1r4f4_decision.json`
- `tests/test_m2_stage2k1r4f4_pe_cycle_guard_validation.py`
- `acceptance/m2_stage2k1r4f4_pe_cycle_guard_validation.md`
- 本工作记录

修改：无（R4F3/R4F3A artifacts、scoring、calendar v1、既有代码未动）。

辅助（gitignored）：`tmp/r4f4_synthetic_later_restatement.json`。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；HEAD `c38b75a`（R4F3A closeout）。
- **未提交、未推送**（本地验证阶段完成，按授权边界停止）。
- 新增 14 个未跟踪文件（见上）；保护项未动；stash 未动；
  默认 DB SHA 未变。
