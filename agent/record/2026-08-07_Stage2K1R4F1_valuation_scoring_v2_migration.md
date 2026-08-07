# 工作记录：M2 Stage 2K.1R4F.1 — Valuation Scoring Contract v2 Migration and Non-Production Shadow Refresh

Status: completed

## 基本信息

- 日期：2026-08-07
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`d02bab9`（R4F 最终 tip CI 全绿后）
- 任务来源：用户指令 M2 Stage 2K.1R4F.1
- 对应模块：价值评估（valuation scoring contract v2 migration / non-production shadow refresh）

## 任务目标

- 创建 scoring registry v2 / policy v2 / shadow inputs v2。
- 将 va_pe/va_pb/va_ps 从旧 annual/year-end 语义迁移为 PE_A_TTM / PB_A_MRQ / PS_A_TTM。
- 接入 R4E.5 trusted 3y/5y percentile，实现 DUAL_WINDOW_SINGLE_COMPONENT。
- PB/PS 生成新的 non-production component shadow；PE 保持 coverage_gap_cycle_context_required。
- 刷新 shadow v6；完整重跑 sensitivity v8。
- 保留 production / overall score / peer / M3 禁止状态。
- 不设计 PE cycle-context；PE 不得获得 numeric score；不得进入 production。

## 范围

- 新增 config：registry v2、policy v2、shadow inputs v2。
- 新增 reports：input capsule v3（按仓库约定顺延）、shadow v6、v5→v6 diff、sensitivity v8、R4F.1 decision、artifact manifest。
- 新增 docs / acceptance / tests / work record。
- 必要时扩展 `src/ashare_research/tools/m2_stage2k_scoring_shadow.py`（保留 v1 默认路径与行为）。
- 必要时注册 manifest schema、更新 R4C1 manifest。

## 非目标

- 不修改 v1 registry / policy / shadow v5 / sensitivity v7 / R4E.5 artifacts / registry v4 / candidate v2 / R4F decision。
- 不给 PE 计算 numeric score；不做 overall score / rank / recommendation / target price / peer / M3。
- 不进入 production scoring；不写默认 DB。
- 不为命名一致性无意义修改 artifact_manifest.py。
- 不设计 PE cycle-context 方法。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `d02bab9`；local == origin（0/0）。
- stash `stash@{0}` 存在；默认 DB SHA `4A71D3C7B88C0B16…` 未变。
- R4F decision = `VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`；
  DUAL_WINDOW_SINGLE_COMPONENT；EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN；
  pe_numeric_scoring_authorized=false；cycle_context_status=not_yet_formalized；
  production NOT_AUTHORIZED；overall PROHIBITED。
- R4E.5 percentile profile：6 条记录，MIDRANK_EMPIRICAL_PERCENTILE，as-of 2026-07-31。
- registry v1：va_pe/va_pb/va_ps 为 annual/year-end 语义，benchmark self_history_percentile，
  3y-only；weight va_* = 0.20；multiple_position 0.60 / yield_position 0.40。
- policy v1：coverage gate 0.6、stability tolerance 1.0、band map、missing-never-zero、risk veto。
- shadow v5：valuation_attractiveness score 12.1733 band E ordinal_shadow（旧 3y-only）；
  va_pe 7.9092、va_pb 15.4746、va_ps 7.9092、va_fcf_yield 17.4003、va_dividend_yield coverage_gap。
- sensitivity v7：valuation_attractiveness NOT_STABLE max_score_delta 3.1637 tolerance 1.0。
- 保护项：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`、stash、默认 DB、
  registry v4、candidate v2、R4E.5 percentile artifacts、R4F decision、scoring 文件。

## 实施计划

1. 建工作记录（本文件）。
2. 核验仓库起点（分支/HEAD/origin/stash/CI/DB/artifacts/protected）。
3. 调研现有 scoring shadow/sensitivity/capsule producer 管线。
4. 设计文 v2 迁移文档 `docs/valuation_scoring_contract_v2_migration.md`。
5. 创建 registry v2 / policy v2 / shadow inputs v2。
6. 扩展 engine（若需）支持 v2 + dual-window + hard-gap policy；v1 golden regression。
7. 构建 input capsule v3、shadow v6、v5→v6 diff、sensitivity v8。
8. 生成 R4F.1 decision。
9. 新增 acceptance 与静态/回归测试。
10. 新增 artifact manifest（v2 schema，按需注册）。
11. 全量验证（pytest R4F.1 / full pytest / ruff / compileall / git diff --check /
    manifest verifier / secret-path scan / clean clone检查）。
12. 更新工作记录（结果、遗留、最终 Git 状态）。
13. 完成后停止（不提交、不推送、不开始 PE cycle-context stage）。

## 决策记录

- **扩展引擎而非另建**：按任务第八节"优先扩展现有
  `src/ashare_research/tools/m2_stage2k_scoring_shadow.py`"，在既有引擎上新增
  `self_history_dual_window_percentile` benchmark、`coverage_gap_cycle_context_required`
  硬缺口处理、`compute_dimension` 的 hard-gap policy 检查，以及
  `--registry/--policy/--inputs` CLI 参数（默认 v1）。v1 默认路径保持逐字节不变
  （golden regression 通过）。考虑过新建独立 v2 引擎，但因公共计算必须单一入口
  而否决。
- **Registry/policy/shadow-inputs v2 采用"复制 v1 + 迁移三条估值组件"**：
  只改 va_pe/va_pb/va_ps（→ PE_A_TTM/PB_A_MRQ/PS_A_TTM，
  benchmark → self_history_dual_window_percentile），其它组件与全部维度拓扑
  原样保留；v1 文件保持不可变。supersedes/supersession_reason 按 R4F migration
  plan 冻结值。
- **shadow v6 基于 capsule v4 派生输入，而非 shadow_inputs_v1**：为确保
  v5→v6 diff 只落在 valuation 维度、且 eq/realization 与 v5 完全一致，v6 使用
  `_capsule_to_inputs(capsule_v4)` 作为非估值维度输入，仅将三条估值组件重绑到
  v2 双窗口 Decimal 百分位并让 va_pe 进入 cycle-context 硬缺口。若直接用
  shadow_inputs_v2（v1 输入副本）会使 eq/realization 漂移（73.4738 vs 73.6694），
  产生误导性 diff，故否决。
- **Decimal-only 聚合**：双窗口百分位 `(p3y+p5y)/2` 用 `Decimal(str)` 计算，
  引擎 `_component_score` 读取 `dual_window_percentile_decimal`（0..100 Decimal
  字符串）并计算 `score = 100 - dual`（lower_better），从未用二进制浮点 identity。
- **PE 硬缺口 fail-closed**：policy v2 新增
  `non_renormalizable_gap_statuses = ["coverage_gap_cycle_context_required"]`；
  当 valuation 组件命中该状态时，维度 score/band 置 null、status =
  `insufficient_evidence_cycle_context`，不重归一化，仍上报
  eligible_weight/covered_weight/coverage_ratio/missing/blocked。coverage==0.6
  不输出数值分。blocked != score=0；组件不删除、权重 0.20 不重分配。
- **artifact_manifest.py 注册 R4F1 schema**：verifier 需要 stage schema 才能
  通过 `ALLOWED_MANIFEST_SCHEMAS`，故新增 `m2_stage2k1r4f1_artifact_manifest_v2`
  到两个 allow-list；因确改 verifier 代码，同步重算 R4C1 manifest 的
  artifact_manifest.py 条目与 manifest_digest（R4C1 仍 verify pass）。

## 实际操作

1. 读取 R4F1 记录、R4F decision、R4E5 percentile profile、migration plan、
   registry/policy/shadow inputs v1、capsule v4、shadow v5、sensitivity v7、
   confidence v3、artifact_manifest.py。
2. 扩展引擎 `m2_stage2k_scoring_shadow.py`：
   - 顶部新增 `from decimal import Decimal`；
   - 新增 v2 路径常量与 `CYCLE_CONTEXT_GAP_STATUS`；
   - `_component_score` 新增硬缺口状态分支（返回 score None + status）与
     `self_history_dual_window_percentile` 分支（Decimal 读取并计算）；
   - `compute_dimension` 在 coverage 计算后、veto 前新增 hard-gap policy 检查
     （`blocked_component_ids` + `insufficient_evidence_cycle_context`）；
   - `validate_and_emit`/`main` 支持 `--registry/--policy/--inputs`（默认 v1）。
3. 因引擎被旧 `m2_stage2k_artifact_manifest.json` 字节钉住，重新生成该
   manifest 的引擎条目（byte_size/sha256 更新），并确认全条目匹配。
4. golden regression：v1 registry/policy + capsule_v4 派生输入 → 引擎
   compute_dimension 复现 shadow v5 核心（eq 73.6694、valuation 12.1733、
   realization 21.7562）逐值一致。
5. 生成 v2 config：registry v2 / policy v2 / shadow inputs v2（见决策记录）。
   验证 v2 下 valuation 维度被 cycle-context 阻塞、eq/realization/risk 与 v1
   一致。
6. 写 `tmp/r4f1_build_artifacts.py` 生成 shadow v6 与 sensitivity v8（基于
   capsule_v4 派生输入 + v2 组件重绑）：valuation 维度 score=None、
   status=insufficient_evidence_cycle_context、blocked=[va_pe]、coverage=0.6；
   PB/PS 组件分 12.0417/6.4332；eq 73.6694、realization 21.7562（与 v5 一致）；
   sensitivity v8 38 scenarios，valuation 全被阻塞。
7. 写 `tmp/r4f1_build_capsule_v5.py` 生成 capsule v5（v4 + 三条估值组件
   observation_set 重绑到双窗口 Decimal 百分位、va_pe 标记硬缺口），重新计算
   capsule_digest。
8. 写 `tmp/r4f1_diff_v5_v6.py` 生成 v5→v6 diff（仅 valuation 改变，eq/realization
   保留，pe_numeric_score_produced_in_v6=false）。
9. 新增 `reports/m2_stage2k1r4f1_decision.json`（decision =
   VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS，
   PASS，PE 仍阻塞，production/overall/peer/M3 禁止，next_stage=
   PE_CYCLE_CONTEXT_METHOD_DESIGN NOT_STARTED）。
10. artifact_manifest.py 注册 R4F1 schema；重算 R4C1 manifest 的
    artifact_manifest.py 条目；生成 `reports/m2_stage2k1r4f1_artifact_manifest.json`
    （13 条目，verify pass）。
11. 新增 `docs/valuation_scoring_contract_v2_migration.md`、
    `acceptance/m2_stage2k1r4f1_valuation_scoring_v2_migration.md`、
    `tests/test_m2_stage2k1r4f1_valuation_scoring_v2_migration.py`（19 静态/回归测试）。
12. 全量验证（见下）。

## 数据与方法说明

- 数据来源：全部读取已提交的规范 artifact，未重新抓取、未重算 percentile：
  - R4E.5 trusted profile `petrochina_pit_valuation_percentile_profile_v1`（6 条，
    MIDRANK_EMPIRICAL_PERCENTILE，as-of 2026-07-31）；
  - capsule v4 `petrochina_score_input_capsule_v4`（非估值维度输入来源）；
  - v1 registry/policy/shadow inputs（不可变基线）。
- 双窗口百分位（Decimal 0..100）：PE (91.964286+93.270025)/2=92.6171555；
  PB (84.958791+90.957886)/2=87.9583385；PS (91.964286+95.169282)/2=93.566784。
- 引擎对 PB/PS 计算 `score=100-dual`：PB 12.0417、PS 6.4332（组件级，无维度分）。
- 非估值维度输入与 v5 相同（来自 capsule v4），保证 diff 干净。
- 未来泄漏：Percentile 为 PIT（as-of 2026-07-31），无 forward-looking 输入；
  引擎仅读取已提交 Decimal 字符串，无浮点 identity。

## 验证

- `pytest tests/test_m2_stage2k1r4f1_valuation_scoring_v2_migration.py`：
  **19 passed**。
- `pytest tests/test_m2_stage2k_dimension_scoring.py`：**22 passed**
  （含 legacy manifest 重生成后）。
- golden regression：v1 路径逐值复现 shadow v5 核心（见实际操作）。
- `reports/m2_stage2k1r4c1_artifact_manifest.json` verify：**pass**（17 文件）。
- `reports/m2_stage2k1r4f1_artifact_manifest.json` verify：**pass**（13 文件）。
- v5→v6 diff：仅 valuation 改变；eq/realization 保留；pe_numeric_score_produced_in_v6=false。
- sensitivity v8：38 scenarios；valuation 全为 insufficient_evidence_cycle_context；
  非估值维度正常扰动。
- 受保护项（AGENTS.md、agent/goals/、acceptance/m2_stage2i2r_*、stash、
  默认 DB、registry v4、R4E.5 artifacts、R4F decision）未动。
- full pytest：**1709 passed, 2 warnings**（含新增 R4F1 19 项；R4E5/R4F
  既有测试因 verifier/状态更新而修复后全绿）。
- `ruff check`（引擎、artifact_manifest.py、R4F1 测试、R4F 测试）：**All checks passed**。
- `git diff --check`：**PASS**。
- `compileall`：**OK**。
- manifest verifier（Section 二 依赖扫描，`rg -l` 命中 5 份）：
  - R4C1（17）/ R4E5（15）/ R4E4（22）全部 **pass**（artifact_manifest.py 条目
    已按真实变化更新，R4E4 另同步 manifest_digest）。
  - R4B（8）/ R4C（13）**fail**，但仅因**既有 stale**（sensitivity.py、
    r3_closeout.py、ADR、decision JSON、tests 等），这些文件 R4F1 **未改动**
    （vs base HEAD `d02bab9` 均为 0 diff；sensitivity.py 在 base HEAD 与当前
    一致 `21906abb…`）。R4B/R4C manifest 创建于 R4C.1 改动（e0d53ad）之前，
    故其 stale 为**前置既有问题，非 R4F1 引入**。按 Section 二"其他 artifact
    条目必须逐字节保持原身份"，仅更新了 R4B/R4C 的 artifact_manifest.py 条目
    （各 4 行 diff），未触碰 pre-existing stale 条目（修复它们超出 R4F1 范围，
    且会被禁止）。R4B/R4C 测试（71 passed）不逐文件验证已提交 manifest，故
    该既有 stale 不阻塞 CI。
- `reports/m2_stage2k1r4f1_artifact_manifest.json` verify：**pass**（13 文件）。
- secret-path scan（新 R4F1 artifact）：**clean**。
- 受保护项（AGENTS.md、agent/goals/、acceptance/m2_stage2i2r_*、stash、
  默认 DB、registry v4、R4E.5 percentile 数据 artifact、R4F decision）未动。

> 注：R4E5 manifest 的 `src/ashare_research/scoring/artifact_manifest.py` 条目
> 因本阶段确改 verifier 代码（注册 R4F1 schema）而变为 stale，已同步重算该条目
> 与 manifest_digest（仅 3 行 diff，R4E5 verify 仍 pass）。R4E.5 percentile
> 数据 artifact 本身未改。

## 结果

- 已完成：registry v2 / policy v2 / shadow inputs v2；
  capsule v5；shadow v6；v5→v6 diff；sensitivity v8；
  R4F1 decision；R4F1 artifact manifest；migration 文档；acceptance；19 项
  静态/回归测试；工作记录。
- 决策：`VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS`；
  valuation 维度 `insufficient_evidence_cycle_context`（无数值分）；
  PE 仍 `coverage_gap_cycle_context_required`（blocked != 0）；
  PB/PS 仅有组件分；production NOT_AUTHORIZED；overall PROHIBITED；
  next_stage=PE_CYCLE_CONTEXT_METHOD_DESIGN（NOT_STARTED）。
- 未完成/未开始：PE cycle-context 方法未设计；PE 数值评分保持阻塞。
- 提交/推送：R4F.1 以 3 个提交（feat migrate / feat refresh / docs closeout）
  落在 base `d02bab9` 之上并已推送至 `origin/feat/m2-value-assessment-mvp`
  （`d02bab9..0f2fcf9`）。remote CI（Stage 2G reproducibility）对该 tip
  commit 全绿：run `31177835006`，Windows clean-clone / Ubuntu clean-clone /
  identity-compare 全部 **success**。
- 与本任务对比：无偏离；非生产、不可重归一化、PE 不设数值分等边界保持。
- 可用性：非生产研究 artifact 已生成；无生产行为变更。

## 遗留问题

- PE cycle-context 形式化契约尚未设计，PE 数值评分保持阻塞（下一独立阶段）。
- shadow v6 已刷新并重跑完整 sensitivity v8；若后续 v3 迁移需再次全量重跑。
- remote CI 已复核并通过：run `31177835006`（Windows/Ubuntu clean-clone +
  identity-compare 全绿）。R4B/R4C manifest 的既有 stale（sensitivity.py /
  r3_closeout.py 等，前置既有、非 R4F1 引入）不阻塞 CI；若未来某阶段确改
  这些文件，应一并重算对应 manifest 条目。

## 下一步建议

- 本阶段已完成并推送，remote CI 对 tip commit 全绿（run `31177835006`）。
- 后续独立阶段：PE cycle-context 方法设计（需另行授权，禁止在本阶段开始）。

## 最终文件变更

新增：
- `config/value_dimension_scoring_registry_v2.json`
- `config/value_dimension_scoring_policy_v2.json`
- `config/value_dimension_scoring_shadow_inputs_v2.json`
- `docs/valuation_scoring_contract_v2_migration.md`
- `reports/m2_stage2k1r4f1_decision.json`
- `reports/m2_stage2k1r4f1_artifact_manifest.json`
- `reports/petrochina_score_input_capsule_v5.json`
- `reports/petrochina_dimension_scoring_shadow_v6.json`
- `reports/petrochina_dimension_scoring_shadow_v5_to_v6_diff.json`
- `reports/petrochina_dimension_scoring_sensitivity_v8.json`
- `acceptance/m2_stage2k1r4f1_valuation_scoring_v2_migration.md`
- `tests/test_m2_stage2k1r4f1_valuation_scoring_v2_migration.py`
- 本工作记录

修改：
- `src/ashare_research/tools/m2_stage2k_scoring_shadow.py`（v2 支持）
- `src/ashare_research/scoring/artifact_manifest.py`（注册 R4F1 schema）
- `reports/m2_stage2k_artifact_manifest.json`（引擎字节条目重算）
- `reports/m2_stage2k1r4c1_artifact_manifest.json`（artifact_manifest.py
  条目重算，2 行）
- `reports/m2_stage2k1r4e5_artifact_manifest.json`（artifact_manifest.py
  条目 + manifest_digest 重算，3 行）
- `tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`（"v2 文件
  必须不存在"改为"如存在则须 supersedes v1"，反映 R4F1 已创建 v2）

辅助（gitignored，不交付）：`tmp/r4f1_build_artifacts.py`、
`tmp/r4f1_build_capsule_v5.py`、`tmp/r4f1_diff_v5_v6.py`。

未动（保护/不可变）：v1 registry/policy/shadow inputs、shadow v5、
sensitivity v7、R4E.5 percentile **数据** artifact、R4F decision、registry v4、
candidate v2、默认 DB、AGENTS.md、agent/goals/、
acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md
（既有用户修改，未动）、stash。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；本地与 origin 均位于 `0f2fcf9`
  （R4F.1 closeout tip），其上 CI run `31177835006` 全绿。
- R4F.1 以 3 个提交落于 base `d02bab9` 之上并**已推送**至
  `origin/feat/m2-value-assessment-mvp`（`d02bab9..0f2fcf9`）：
  1. `f198d3e` feat: migrate valuation scoring contract to v2
  2. `c5261bf` feat: refresh non-production valuation scoring shadow
  3. `0f2fcf9` docs: record R4F.1 local closeout
- 未 force push、未 reset、未 git clean、未 merge、未 PR、未 tag、未 release。
- 既有未跟踪/修改项（`AGENTS.md`、`agent/goals/`、
  `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`）
  为会话开始前既有状态，未纳入 R4F.1 提交，未改动。