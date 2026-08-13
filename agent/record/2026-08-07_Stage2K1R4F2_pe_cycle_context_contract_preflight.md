# 工作记录：M2 Stage 2K.1R4F.2 — PE Cycle Context Contract Preflight and Normalized Earnings Method Review

Status: completed

## 基本信息

- 日期：2026-08-07
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`3a0437a`（R4F.1 closeout，CI 全绿后）
- 任务来源：用户指令 M2 Stage 2K.1R4F.2
- 对应模块：价值评估（PE cycle-context method preflight / evidence inventory）

## 任务目标

- 冻结本阶段问题定义：为周期敏感发行人，何种确定性、PIT-safe 的
  normalized-earnings 契约足以防止"当前盈利高于可持续/中周期盈利时，
  低 PE 机械获得高估值分"。
- 盘点真实 committed fact inputs（annual NP / revenue / equity / shares /
  MRQ / TTM / R4E.5 PE 观察）。
- 比较至少五种 normalized-earnings 方法（Option A–F），记录借用与裁剪。
- 构建 ROE-normalized diagnostics（prototype candidate）与 margin /
  historical-window EPS 诊断。
- 输出 inventory / method matrix / diagnostics / decision，全部
  Decimal(string) canonical，禁止 float identity。
- 本阶段**绝不恢复 PE numeric score**；不修改 registry/policy/shadow
  inputs v2；不创建 registry v3 / policy v3 / shadow v7 / sensitivity v9。

## 范围

- 新增：docs、input inventory v1、method matrix v1、diagnostics v1、
  R4F.2 decision、纯函数模块 `pe_cycle_context_preflight.py`、薄 CLI、
  测试、acceptance、工作记录。
- 允许新增 R4F2 generic manifest 仅当零代码改动可生成（否则不建）。
- 读取已提交的 canonical facts：`petrochina_pit_denominator_reported_fact_bundle_v1.json`
  （127 facts）、`petrochina_pit_denominator_reconciled_fact_bundle_v1.json`（38 facts）、
  `petrochina_pit_financial_state_timeline_v2.json`、
  `petrochina_pit_valuation_percentile_profile_v1.json`。

## 非目标

- 不恢复 PE numeric score；不产生 valuation dimension numeric score；
  不产生 production/overall score；不做 recommendation / target price /
  peer / M3。
- 不设计完整 PE cycle-context contract（那是下一阶段）；本轮只冻结
  prototype contract 的 evidence contract 与 method 选择。
- 不网络采集；不写默认 DB；不改 scoring engine
  （`m2_stage2k_scoring_shadow.py`）。
- 不修 R4B/R4C 历史 manifest stale（KNOWN_HISTORICAL_MANIFEST_DEBT，
  NON_BLOCKING_FOR_R4F2）。
- 不为了 R4F2 名字注册修改 `artifact_manifest.py`。
- 不设置 1.2/1.5/80th 等任意 peak 阈值；不把 >1 描述为 cycle peak。
- 未经明确授权：不提交、不推送、不开始 normalized earnings prototype。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `3a0437ab82c1da8dcb0cbd010656bc1afa86f333`；
  local == origin（0/0）；R4F.1 最终 tip CI 全绿（run 31178429549）。
- stash `stash@{0}` 存在；默认 DB SHA `4A71D3C7B88C0B16…` 未变。
- R4F1 decision = `VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS`；
  pe_numeric_scoring_authorized=false；cycle_context_status=not_yet_formalized。
- shadow v6 valuation：score=null / insufficient_evidence_cycle_context /
  coverage 0.6 / blocked=[va_pe]；policy v2 pe_weight_not_reassigned=true、
  non_renormalizable_gap_statuses=[coverage_gap_cycle_context_required]。
- R4E.5 PE_A_TTM：3y 91.964286、5y 93.270025（midrank percentile）；
  current_ratio_decimal=12.81970638132453345471096950；as_of 2026-07-31。
- R4E.4 timeline：PE_A_TTM 2026-03-31 state value=158,184,000,000
  （TTM parent NP，computed）；PS TTM revenue 2,847,796,000,000。
- 已提交 canonical facts（reported bundle，exchange_official tier）：
  - annual parent NP 2020–2025（2022 restated_1=148,738,000,000 可见、
    2023 restated_1=161,414,000,000 可见）；
  - annual parent equity 2020–2025（original）；
  - annual revenue 2020–2025（2023 restated_1=3,012,812,000,000 可见）；
  - basic_eps 2020–2025（0.10/0.50/0.82/0.88/0.90/0.86）；
  - MRQ 2026-03-31：NP 48,332,000,000 / revenue 736,383,000,000 /
    equity 1,624,532,000,000 / basic_eps 0.264；
  - shares 恒定 183,020,977,818（r4d1-share-continuity-constancy-v1）。
- 保护项：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`、stash、
  默认 DB、registry v4、R4E.5 artifacts、R4F/R4F1 decisions、全部既有
  scoring artifact（registry/policy/shadow inputs v2、capsule v5、shadow v6、
  sensitivity v8）。

## 实施计划

1. 建工作记录（本文件）。
2. 核验仓库起点（已完成，见上）。
3. 写 `docs/pe_cycle_context_normalized_earnings_review.md`（问题定义 +
   成熟方法引用与裁剪）。
4. 写纯函数模块 `src/ashare_research/pit_valuation/pe_cycle_context_preflight.py`
   （inventory / ROE 重建 / BVPS / normalized EPS / margin / method matrix /
   decision / verify；Decimal-only；PIT + restatement + share-scope gates）。
5. 写薄 CLI `src/ashare_research/tools/m2_stage2k1r4f2_pe_cycle_context_preflight.py`
   （inventory / build / verify / fixtures；显式输入路径）。
6. 生成四个 JSON：input inventory v1、method matrix v1、diagnostics v1、
   R4F2 decision。
7. 写测试 `tests/test_m2_stage2k1r4f2_pe_cycle_context_preflight.py`。
8. 写 acceptance `acceptance/m2_stage2k1r4f2_pe_cycle_context_contract_preflight.md`。
9. 全量验证（Section 二十五 顺序）。
10. 更新工作记录（结果、遗留、Git 状态）。

## 决策记录

- **方法矩阵冻结**：Option A 二值峰值标记 REJECT（阈值任意、单期同比
  不能定义周期）；B HISTORICAL_AVERAGE_EPS_FULL_CYCLE 仅当
  full_cycle_coverage_status=PROVEN 才 eligible，否则
  BLOCKED_FULL_CYCLE_NOT_PROVEN；C AVERAGE_ROE×CURRENT_BVPS 为
  PRIMARY PROTOTYPE CANDIDATE；D NORMALIZED_MARGIN×CURRENT_REVENUE
  仅 INDEPENDENT_DIAGNOSTIC；E 商品价格模型 DEFER/REJECT_AS_PRIMARY
  （主观油价 + 无 commodity-to-earnings mapping）；F 同业平均 DEFER
  （peer acquisition 未授权）。
- **PIT gate**：as_of=2026-07-31；annual 输入 available_at<=as_of 且
  effective_from<=as_of 才可见；current facts effective_from<=2026-07-31。
  synthetic future fact（available_at>as_of）必须被排除。绝不按 JSON
  数组顺序决定可见性。
- **Restatement gate**：每 period 按 effective_from 排序，取
  effective_from<=as_of 的最新版本；同 effective_from 平局由
  supersedes 链裁决，否则 fail closed。as-of 2026-07-31 可见 2022=
  restated_1 148,738,000,000、2023=restated_1 161,414,000,000（即 supersession
  后的 as-of 值，不是"倒灌最终修订值"——as-of 已覆盖 restatement 发布时间）。
- **Share scope**：沿用 R4C/R4D/R4E 冻结的公司整体普通股
  183,020,977,818（r4d1 证明）；拒绝 A-share-only denominator；
  BVPS 使用当前 PIT（2026-03-31）period-end shares，与 PE_A_TTM
  的 weighted shares 数值一致。
- **Decimal-only**：所有计算 Decimal(str(value))；平均 equity、ROE、
  mean、BVPS、normalized EPS 均 Decimal canonical；禁止 float /
  round-before-aggregation。
- **ROE 语义**：average_equity_y=(begin+end)/2，ROE_y=NP_y/avg_equity_y；
  historical_average_roe=算术平均；本阶段不 trim/winsorize/排除坏年份。
  2020 年 opening equity（2019-12-31）缺失 → 2020 ROE 不 eligible；
  2021–2025 为 5 个连续年度 → history_coverage_ready=true；
  full_cycle_proven=false（5y != 完整周期，无独立证据）。
- **命名冻结**：full_cycle_proven=false 时禁止
  NORMALIZED_FULL_CYCLE_EPS，只能用 HISTORICAL_WINDOW_AVERAGE_EPS。
- **不建 artifact manifest**：method/evidence preflight 不改变正式
  scoring runtime identity；若 generic manifest 需改 artifact_manifest.py
  则明确不建。
- **决策规则**：decision 由 evidence 决定，不参考 R4E.5 percentile
  （"选哪个方法让 PE 更高/更低"禁止）。

## 实际操作

1. 核验仓库起点（Section 一）：branch `feat/m2-value-assessment-mvp`，
   HEAD `3a0437ab82c1da8dcb0cbd010656bc1afa86f333`，origin 同步（0/0），
   worktree 仅保护项，stash=1，默认 DB SHA `4A71D3C7B88C0B16…`，R4F.1 最终
   tip CI 全绿（run 31178429549），R4F/R4F1 decisions、registry v2 /
   policy v2 / shadow v6 硬缺口状态全部确认。
2. 盘点已提交 canonical facts（reported bundle 127 facts + reconciled
   bundle 38 facts）：annual NP/equity/revenue 2020–2025、restatement
   （2022 NP→148,738,000,000；2023 NP→161,414,000,000、revenue→3,012,812,000,000）、
   basic_eps 2020–2025、MRQ 2026-03-31（NP 48,332,000,000 / equity
   1,624,532,000,000 / revenue 736,383,000,000 / basic_eps 0.264）、
   shares 恒定 183,020,977,818；R4E.5 PE 3y/5y percentile 与
   current_ratio_decimal；R4E.4 PE/PS TTM 2026-03-31 states。
3. 写 `src/ashare_research/pit_valuation/pe_cycle_context_preflight.py`
   （纯函数模块）：visible_versions / resolve_latest_visible /
   merge_fact_bundles / build_annual_fact_inventory / build_annual_roe_chain /
   build_current_bvps_and_normalized_eps / build_historical_window_eps_diagnostic /
   build_normalized_margin_diagnostic / build_method_matrix /
   build_diagnostics / build_decision + 三个派生 gate（_derive_pit_pass /
   _derive_restatement_pass / _derive_share_scope_pass）；Decimal-only。
4. 写 `src/ashare_research/tools/m2_stage2k1r4f2_pe_cycle_context_preflight.py`
   （薄 CLI：inventory / build / verify / fixtures）。
5. 生成四份 JSON artifact：input inventory v1、method matrix v1、
   diagnostics v1、R4F2 decision（CLI build；`verify` 复算逐字节一致）。
   决策 = `PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED` (PASS)；
   全部 11 个 gate 由真实 evidence 派生（pit/restatement/share_scope 等）。
   inventory 含 annual series（42 条，A–G）与 latest PIT items（H–L：
   MRQ equity / MRQ shares / TTM NP / TTM revenue / R4E.5 PE observation），
   TTM 值带 3 个输入 Fact ID，PE observation 带 R4E.5 record/observation ID。
6. 写 `docs/pe_cycle_context_normalized_earnings_review.md` 与
   `acceptance/m2_stage2k1r4f2_pe_cycle_context_contract_preflight.md`。
7. 写 `tests/test_m2_stage2k1r4f2_pe_cycle_context_preflight.py`（35 项）；
   修复 ruff 问题（unused imports、E501、B905、SIM300、E402、CLI E402）。
8. CLI fixtures 模式生成 `tmp/r4f2_synthetic_future_facts.json`（gitignored，
   34 条 future NP facts，供 PIT 测试使用）。

### 关键计算结果（全部 Decimal canonical）

- ROE 链 2021–2025 连续 5 年；2020 blocked（missing_opening_equity）。
- average_roe = 0.1029179088085938346085963897
- current BVPS = 1624532000000.0 / 183020977818 = 8.876206538550294436827638346
- normalized_EPS_ROE = 0.9135206151007635380066173292
- 当前 TTM parent NP = 158,184,000,000（与 R4E.4 PE_A_TTM 2026-03-31 state
  逐值一致，交叉验证通过）；TTM EPS = 0.8642943660660668889225593242
- context ratio (current_eps/roe_norm_eps) = 0.9461136965920940114716739512
  （纯数学关系，无 peak 标签）
- historical window avg EPS (basic) = 0.792 → HISTORICAL_WINDOW_AVERAGE_EPS
  （full_cycle_proven=false，禁用 NORMALIZED_FULL_CYCLE_EPS）
- avg margin = 0.04914241455740617927483288526；normalized EPS (margin) =
  0.7646531740535774286590419341；TTM revenue = 2,847,796,000,000
  （与 R4E.4 PS_A_TTM 2026-03-31 state 一致）

## 数据与方法说明

- 数据来源：全部已提交 committed facts（reported/reconciled fact bundle、
  R4E.4 timeline、R4E.5 profile），未重新抓取。
- 单位：facts 中 unit=CNY（raw_unit=CNY_million 已规范化），value 为
  canonical Decimal string；shares 为股数整数。
- as_of：2026-07-31（R4E.5 as_of_trade_date）。
- 复权方式：不涉及价格复权；PE ratio 读取已提交的
  current_ratio_decimal（12.81970638132453345471096950）。
- 缺失值处理：opening equity 缺失 → 该年 ROE 不 eligible（不视为零）。
- 未来泄漏：PIT gate 排除 available_at>as_of 的 facts；synthetic future
  fact 测试验证排除；不按数组顺序。
- 统计假设：无分布假设；纯算术平均；无任意阈值。

## 验证

按 Section 二十五 顺序执行：

1. branch/HEAD/CI/protected：`feat/m2-value-assessment-mvp` @
   `3a0437ab82c1da8dcb0cbd010656bc1afa86f333`；origin 同步；R4F.1 最终 tip
   CI run `31178429549` success；worktree 仅保护项；stash=1。
2. R4F1 decision verifier：R4F1 测试 **19 passed**（含 manifest verify）。
3. scoring v2 hard-gap baseline：shadow v6 valuation score=null /
   insufficient_evidence_cycle_context / blocked=[va_pe]；policy v2
   pe_weight_not_reassigned=true。
4–13. 实际 Fact inventory / PIT / restatement / ROE / BVPS / historical EPS /
   margin / normalized diagnostics / method matrix：全部由已提交事实构建，
   见"实际操作"。
14–16. build A → build B（CLI `verify` 复算）→ 四份 JSON **byte-identical**。
17. R4F2 测试：**35 passed**。
18. R4F1 protected tests：**19 passed**。
19. R4F protected tests：**22 passed**。
20. full pytest：**1744 passed, 2 warnings**（1709 + R4F2 新增 35）。
21. `ruff check src/ tests/`：**All checks passed**。
22. `python -m compileall -q src tests`：**OK**。
23. `git diff --check`：**PASS**（仅 CRLF 提示）。
24. secret/path/pollution scan（新 R4F2 文件）：**clean**。
25. scoring files exact diff check：registry v2 / policy v2 / shadow inputs
   v2 / capsule v5 / shadow v6 / sensitivity v8 / scoring engine 全部
   **0 diff**。
26. 默认 DB SHA `4A71D3C7B88C0B16…` 未变；stash 未动；保护项
   （AGENTS.md、agent/goals/、acceptance/m2_stage2i2r_*、R4F/R4F1
   decisions、R4E.5 artifacts、registry v4）未动。

交叉验证：

- TTM parent NP 158,184,000,000 == R4E.4 PE_A_TTM 2026-03-31 state。
- TTM revenue 2,847,796,000,000 == R4E.4 PS_A_TTM 2026-03-31 state。
- 2022/2023 restated 值由 supersession 链确定性解析（restated_1）。

## 结果

- 已完成：docs review、input inventory v1、method matrix v1（Option A–F）、
  diagnostics v1、R4F2 decision（`PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED`
  PASS，11 个 gate 全部由真实 evidence 派生）、纯函数模块、薄 CLI、
  35 项测试、acceptance、工作记录。
- 决策：AVERAGE_ROE×CURRENT_BVPS 为 PRIMARY PROTOTYPE CANDIDATE
  （ELIGIBLE_FOR_PROTOTYPE，连续 5 年 ROE）；HISTORICAL_AVERAGE_EPS
  BLOCKED_FULL_CYCLE_NOT_PROVEN；margin 仅 DIAGNOSTIC；商品价格模型
  DEFERRED_NOT_PRIMARY；同业 DEFERRED_NOT_AUTHORIZED；二值峰值标记 REJECT。
- PE numeric scoring：**BLOCKED_UNCHANGED**；valuation dimension 无数值分；
  production NOT_AUTHORIZED；overall PROHIBITED；registry/policy/shadow
  inputs v2 未改。
- 未完成/未开始：NORMALIZED_EARNINGS_PROTOTYPE 未开始（需另行授权）。
- 提交/推送：R4F.2 以 2 个提交落在 base `3a0437a` 之上并已推送至
  `origin/feat/m2-value-assessment-mvp`（`3a0437a..1f8e490`）；remote CI
  run `31184282923` 对 tip commit `1f8e490` 全绿（Ubuntu/Windows
  clean-clone + identity-compare）。
- 与本任务对比：无偏离；全部边界保持（无 score、无阈值、无 future
  leak、无网络、无 DB 写入）。
- 可用性：method/evidence preflight 产物已生成，非评分、可复现。

## 遗留问题

- 2020 ROE 因缺少 2019-12-31 opening equity 不可重建（不视为零）。
- full_cycle_coverage_status=NOT_PROVEN：当前 2020–2025 窗口无独立证据
  证明覆盖完整 earnings cycle；如后续获得更早年度事实，可重新评估。
- R4B/R4C 历史 manifest stale：KNOWN_HISTORICAL_MANIFEST_DEBT，
  NON_BLOCKING_FOR_R4F2，留到 final M2 milestone-wide integrity closeout。
  全量 sweep（18 份）：6 PASS；12 FAIL 全部前置既有（R4A/R4B/R4C 内容
  stale + 9 份 legacy schema，见 acceptance 2a 节）；R4F2 未触碰任何
  manifest、未注册新 schema。
- 本轮不建 artifact manifest（method/evidence preflight，不修改正式
  scoring runtime identity；R4F1 manifest 仍 verify pass）。
- remote CI 已复核并通过：run `31184282923`（Ubuntu/Windows clean-clone +
  identity-compare 全绿，tip commit `1f8e490`；full pytest 1744 passed /
  2 warnings，R4F2 35、R4F1 19、R4F 22 passed；旧 scoring contract
  零变化）。

## 下一步建议

- 本阶段已完成并推送，remote CI 对 tip commit 全绿（run `31184282923`）。
- 下一独立阶段 `NORMALIZED_EARNINGS_PROTOTYPE`（需另行授权）：验证 PIT
  historical reconstruction、normalized-earnings identity、normalized-PE
  定义、current vs historical 行为、deterministic A/B、sensitivity、
  peak-low-PE inversion 是否真正消除。METHOD READY != SCORING READY。
- 禁止开始 R4F.3；不得修改 PE scoring。

## 最终文件变更

新增：
- `docs/pe_cycle_context_normalized_earnings_review.md`
- `reports/petrochina_pe_cycle_context_input_inventory_v1.json`
- `reports/petrochina_pe_normalized_earnings_method_matrix_v1.json`
- `reports/petrochina_pe_normalized_earnings_diagnostics_v1.json`
- `reports/m2_stage2k1r4f2_decision.json`
- `src/ashare_research/pit_valuation/pe_cycle_context_preflight.py`
- `src/ashare_research/tools/m2_stage2k1r4f2_pe_cycle_context_preflight.py`
- `tests/test_m2_stage2k1r4f2_pe_cycle_context_preflight.py`
- `acceptance/m2_stage2k1r4f2_pe_cycle_context_contract_preflight.md`
- 本工作记录

修改：无（scoring contracts、既有 artifacts、既有代码全部未动）。

辅助（gitignored，不交付）：`tmp/r4f2_synthetic_future_facts.json`。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；本地与 origin 均位于 `1f8e490`
  （R4F.2 closeout tip），其上 CI run `31184282923` 全绿。
- R4F.2 以 2 个提交落于 base `3a0437a` 之上并**已推送**至
  `origin/feat/m2-value-assessment-mvp`（`3a0437a..1f8e490`）：
  1. `2e75dc7` feat: add PE normalized earnings method preflight
  2. `1f8e490` docs: record R4F.2 local closeout
- 未 force push、未 reset、未 git clean、未 merge、未 PR、未 tag、未 release。
- 既有未跟踪/修改项（`AGENTS.md`、`agent/goals/`、
  `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`）
  为会话开始前既有状态，未纳入 R4F.2 提交，未改动。
