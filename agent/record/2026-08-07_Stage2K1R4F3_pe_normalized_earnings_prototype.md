# 工作记录：M2 Stage 2K.1R4F.3 — PIT Normalized Earnings Prototype and Historical Cycle-Guard Validation Readiness

Status: completed

## 基本信息

- 日期：2026-08-07
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`83e0685`（R4F.2 closeout，最终 tip CI 全绿）
- 任务来源：用户指令 M2 Stage 2K.1R4F.3
- 对应模块：价值评估（PE normalized-earnings prototype / historical readiness）

## 任务目标

1. 把 R4F.2 已允许的 AVERAGE_ROE×CURRENT_BVPS 方法实现为正式 non-scoring
   prototype（2026-07-31 current prototype）。
2. 构建 normalized EPS / normalized PE / raw vs normalized PE diagnostic。
3. 用确定性 counterfactual/property test 证明 normalized PE 消除了
   "当前 TTM 盈利直接进入 PE 分母"造成的机械反转。
4. 建立历史 PIT readiness matrix（3y / 5y historical cycle-guard validation
   readiness），判断现有事实是否足以进行历史验证。
5. 如果历史事实不足，精确冻结需要补采的年度 Fact 集合（fact gap plan），
   然后 fail-closed 停止。

## 范围

- 新增：prototype contract v1、docs、纯函数模块
  `pe_normalized_earnings_prototype.py`、薄 CLI、current prototype v1、
  normalized PE snapshot v1、mechanical inversion audit v1、historical
  readiness v1、historical state ledger v1（必要）、fact gap plan v1
  （gaps 存在时）、R4F3 decision、测试、acceptance、工作记录。
- 读取已提交 canonical inputs：reported/reconciled fact bundle、R4E4
  candidate v2（market observations）、R4E4 timeline v2、R4E5 percentile
  profile、R4F2 decision/diagnostics/inventory。
- Manifest：仅当 generic manifest contract 可零代码覆盖时才建
  `m2_stage2k1r4f3_artifact_manifest.json`，否则记录
  `artifact_manifest = NOT_REQUIRED_PROTOTYPE_STAGE`。不修改
  `artifact_manifest.py`，不为 R4F3 命名注册新 schema。

## 非目标

- 不恢复 va_pe numeric score；不产生 valuation dimension numeric score；
  不产生 production/overall score。
- 不修改 registry v2 / policy v2 / shadow inputs v2 / capsule v5 / shadow
  v6 / sensitivity v8；不创建 registry v3 / policy v3 / shadow v7 /
  sensitivity v9。
- 不创建 cycle peak classifier；不创建 normalized PE scoring percentile；
  不发布正式 normalized PE percentile series（3y/5y/score）。
- 不联网补事实（无 SSE 访问、不下载旧年报、不新增 official facts、
  不修改 fact bundle、不修改 DuckDB）。只产出精确 backfill plan。
- 不缩短 5 年 ROE contract（4y/3y average、expanding average 均禁止作为
  正式 prototype 方法）。
- 不把 ratio=1 变成 cycle threshold；不输出 cheap/expensive/
  undervalued/overvalued/cycle top/bottom。
- margin normalized EPS 不得升级为 fallback denominator。
- 不修改 `pe_cycle_context_preflight.py` 既有行为。
- 不修 R4B/R4C/R4A 历史 manifest debt。
- 未经明确授权：不提交、不推送、不开始 R4F.3A、不修改 scoring。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `83e0685`（R4F.2 closeout）；
  local == origin（0 ahead / 0 behind）；R4F.2 最终 tip CI run
  `31185520773` 全绿。
- worktree：仅保护项（`acceptance/m2_stage2i2r_*.md` 修改、
  `AGENTS.md`、`agent/goals/` 未跟踪）——会话开始前既有状态。
- stash `stash@{0}` 存在；默认 DB SHA `4a71d3c7b88c0b16`（data/research.duckdb）。
- R4F2 decision = `PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED`
  （PASS）；average_roe_x_current_bvps=ELIGIBLE_FOR_PROTOTYPE；
  full_cycle_proven=false；pe_numeric_scoring_authorized=false。
- R4F2 CLI verify：四份 artifacts byte-identical；diagnostics 复算数值一致
  （avg_roe 0.1029179088085938346085963897、norm_eps
  0.9135206151007635380066173292）。
- R4E4 candidate v2：1351 market rows；PE_A_TTM 2026-07-31 observation：
  close=11.08（market_reconciliation_digest
  4fb3382b25e5889e91e1dc27b46e1ae6c080e4dc5ef23b4e47c65063603d5acc）、
  financial_state_id 6820afee…、TTM EPS（per_share_denominator）
  0.8642943660660668889225593242、ratio_decimal
  12.81970638132453345471096950、observation_id
  98d47da1a60919889c2a143b6a704a373ac9128beafe8cade842dd4a8f075701。
- 已提交 facts 关键 PIT 时间表（effective_from）：
  - annual NP/equity/revenue：2020→2021-03-29；2021→2022-04-06；
    2022→2023-03-31（restated_1 2024-03-27）；2023→2024-03-27
    （restated_1 2025-04-01）；2024→2025-04-01；2025→2026-03-31。
  - MRQ equity：2020-03-31…2026-03-31 全部存在
    （2026-03-31 = 1,624,532,000,000，effective 2026-05-06）。
  - period-end shares：全部 183,020,977,818（r4d1 常数），
    MRQ 各期 effective 与 MRQ equity 同步。
  - 2026-03-31 period-end share fact 只在 reconciled bundle。
- 保护项：AGENTS.md、agent/goals/、acceptance/m2_stage2i2r_*、stash、
  默认 DB、registry v2/policy v2/shadow inputs v2、capsule v5、shadow v6、
  sensitivity v8、R4E4/R4E5 artifacts、R4F/R4F1/R4F2 decisions。

## 实施计划

1. 建工作记录（本文件）。
2. Section 一 起点核验 + Section 二 冻结 prototype contract（config v1）。
3. 写纯函数模块 `pe_normalized_earnings_prototype.py`（当前 state +
   historical PIT readiness resolver + fact gap plan + decision）。
4. 写薄 CLI。
5. 生成 current prototype v1 / normalized PE snapshot v1 /
   mechanical inversion audit v1。
6. 跑 historical readiness → readiness v1 + state ledger + fact gap plan。
7. 生成 R4F3 decision。
8. 写 docs / tests / acceptance。
9. Section 二十七 30 步验证（含 A/B byte-identical）。
10. 更新工作记录（结果、遗留、Git 状态）；本地验证后停止。

## 决策记录

- **5 年 ROE contract 硬边界**：minimum_consecutive_annual_roe=5 冻结；
  历史时点不足 5 个连续年度一律 BLOCKED_INSUFFICIENT_ROE_HISTORY，绝不
  为生成更多历史点缩短为 3y/4y average 或 expanding average。
- **PIT resolver 设计**：`resolve_annual_roe_chain_as_of` 逐年度解析
  （PIT + restatement gate），取"以最新可见年度为终点的最长连续尾部
  运行"，不足 5 则 BLOCKED；`resolve_current_bvps_as_of` 取各
  period_end 的最新可见 equity / shares。
- **walk-forward 引擎**：对 1351 个交易日逐一判定 READY/BLOCKED，无
  forward fill；`validate_prototype` 自身用 synthetic future fact /
  later restatement / 数组反转三种扰动证明 PIT 隔离。
- **fact gap plan**：required ROE years 由目标交易日"可见的最新年度
  报告 + 前四年"推导（非硬编码）；对 2023-07-31 → 2018..2022；
  对 2021-08-02 → 2016..2020。missing facts 精确到 concept ×
  period_end，含最早年 opening equity。不发明 provider 值。
- **normalized PE 输入**：close 只来自 R4E.4 candidate v2 2026-07-31
  PE_A_TTM observation（11.08，reconciliation digest 4fb3382b…）；
  raw PE 复算必须与 candidate ratio_decimal 逐值一致；禁止由 PE×EPS
  反推 close。
- **share scope fail-closed**：normalized earnings state 在 shares ≠
  183,020,977,818 时 BLOCKED（share_scope_mismatch），不产生数字。
- **决策规则**：R4F3 decision 由 evidence 派生；当前真实结果
  （3y window BLOCKED）→ B：PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_
  HISTORICAL_FACT_GAPS_REMAIN（CONDITIONAL PASS）。
- **不建 artifact manifest**：prototype 阶段不改变正式 scoring runtime
  identity；`artifact_manifest = NOT_REQUIRED_PROTOTYPE_STAGE`；不注册
  新 schema。

## 实际操作

1. 核验仓库起点（Section 一）：分支 `feat/m2-value-assessment-mvp`，
   HEAD `83e0685`，local==origin（0/0），R4F.2 最终 tip CI 全绿
   （run 31185520773），worktree 仅保护项，stash=1，默认 DB SHA
   `4a71d3c7b88c0b16`；R4F2 decision / diagnostics / inventory 确认。
2. R4F2 CLI `verify`：四份 artifacts byte-identical；diagnostics 复算
   数值一致（avg_roe 0.1029179088…、norm_eps 0.9135206151…）。
3. 盘点已提交 facts 的 PIT 时间表（annual NP/equity/revenue
   effective_from、MRQ equity、period-end shares 全常数）；确认无
   2020 之前 annual facts；确认 R4E.5 PE obs 分布（1351 交易日，
   computed 从 2021-03-29 起）与 raw PE 复算 == candidate ratio。
4. 写 `config/pe_normalized_earnings_prototype_contract_v1.json`。
5. 写 `src/ashare_research/pit_valuation/pe_normalized_earnings_prototype.py`
   （纯函数模块）与薄 CLI。
6. `fixtures` 生成 `tmp/r4f3_synthetic_walk_forward_facts.json`
   （59 future + 1 later restatement，gitignored）。
7. `build` 生成 7 份 artifacts：prototype v1 / normalized PE snapshot
   v1 / mechanical inversion audit v1 / historical readiness v1 /
   historical state ledger v1 / fact gap plan v1 / R4F3 decision。
8. 修复实现期问题：gap plan int/str 比较（`int(target[:4])`）；
   gap plan required-years 语义改为"目标日可见的最新年度报告 + 前四
   年"（修正后 3y→2018..2022，5y→2016..2020）；share scope 对
   normalized earnings state fail-closed；PE snapshot 补充 identity
   字段（normalized_earnings_state_id、annual_fact_ids 等）与
   normalized_pe_decimal。
9. 写 `docs/pe_normalized_earnings_prototype_and_validation_protocol.md`、
   `acceptance/m2_stage2k1r4f3_pe_normalized_earnings_prototype.md`、
   `tests/test_m2_stage2k1r4f3_pe_normalized_earnings_prototype.py`。
10. ruff 修复（unused imports、E501、B007、E741、F841、I001）。

### 关键计算结果（全部 Decimal canonical）

- ROE 2021..2025：0.07434629055079871379731497929 / 0.1129630958714448405117204395 /
  0.1146411949491226163766439180 / 0.1112006593330161818176293251 /
  0.1014383033385868205396732864
- average_roe = 0.1029179088085938346085963897（== R4F2）
- current BVPS = 8.876206538550294436827638346（== R4F2）
- normalized_EPS_ROE = 0.9135206151007635380066173292（== R4F2）
- raw_pe_ttm = 12.81970638132453345471096950（复算 == candidate）
- normalized_pe_roe = 12.12889979366021109951970404
- earnings_normalization_ratio = 0.9461136965920940114716739512
- raw_to_normalized_pe_ratio = 1.056955420476423401383024263
- readiness：ready 84 天（2026-03-31..2026-07-31），blocked 1267 天；
  3y window 644 天全 blocked；5y window 1127 天全 blocked。
- gap plan：MINIMUM_3Y_BACKFILL=5 facts（2017/2018/2019 equity+NP）；
  MINIMUM_5Y_BACKFILL=9 facts（2015..2019 equity+NP）。

## 数据与方法说明

- 数据来源：全部已提交 committed facts + R4E4/R4E5 artifacts，无网络。
- as_of：2026-07-31；历史窗口：2021-01-04..2026-07-31（1351 个交易日）。
- 3y 窗口 = 2023-07-31..2026-07-31；5y 窗口 = 2021-08-02..2026-07-31
  （R4E.5 冻结）。
- 方法：AVERAGE_ROE_X_CURRENT_BVPS（contract v1），Decimal(string) only，
  PIT gate（available_at<=as_of AND effective_from<=as_of），restatement
  gate（最新 effective_from + supersedes 链，平局 fail closed），share
  scope = company-wide ordinary shares（r4d1）。
- 无未来泄漏：历史时点只用 <= 该时点的事实；synthetic future fact /
  later restatement / 数组顺序三种扰动必须证明状态不变。
- 统计假设：无分布假设；纯算术平均；无任意阈值；multiplier 0.5/1.0/2.0
  仅数学 property test 用，无业务含义。

## 验证

按 Section 二十七 顺序执行：

1. branch/HEAD/CI/protected：`feat/m2-value-assessment-mvp` @ `83e0685`；
   origin 同步；R4F.2 最终 tip CI 全绿；worktree 仅保护项 + 本轮新增；
   stash=1。
2. R4F2 decision verifier：CLI verify **4/4 byte-identical**；
   R4F2 测试 **35 passed**。
3. R4F2 diagnostics 复算：avg_roe / BVPS / norm_eps **逐值一致**。
4. prototype contract：`config/pe_normalized_earnings_prototype_contract_v1.json`
   冻结（5y 硬边界、Decimal-only、PIT/restatement/share-scope 规则）。
5. current 5y ROE 重建：2021..2025，状态 READY。
6. current BVPS 重建：8.8762065385…，READY。
7. current market observation：R4E.4 candidate v2 2026-07-31 PE_A_TTM
   observation（close 11.08，digest 4fb3382b…，obs 98d47da1…）。
8. current raw PE 复算：12.81970638132453345471096950 == candidate ratio。
9. normalized EPS：0.9135206151007635380066173292。
10. normalized PE：12.12889979366021109951970404。
11. mechanical inversion property：PASS（EPS 0.5x/1x/2x → raw PE 变、
    normalized PE 不变、state ID 不变、无 peak label）。
12. historical walk-forward readiness：1351 天，READY 84 / BLOCKED 1267。
13. earliest ready date：2026-03-31（最新 2026-07-31）。
14. 3y readiness：BLOCKED（644 天全 blocked）。
15. 5y readiness：BLOCKED（1127 天全 blocked）。
16. exact fact-gap derivation：3y=5 facts（2017..2019），5y=9 facts
    （2015..2019）。
17. build A：7 份 artifacts 生成。
18. build B：隔离 output-root 复算。
19. byte/identity 比较：**A/B 及 A/committed 全部 byte-identical**（7/7）。
20. R4F3 测试：**45 passed**。
21. R4F2 测试：**35 passed**。
22. R4F1 protected 测试：**20 passed**。
23. R4F protected 测试：**22 passed**。
24. full pytest：**1789 passed, 2 warnings**（1744 + 45）。
25. `ruff check src/ tests/`：**All checks passed**。
26. `python -m compileall -q src tests`：**OK**。
27. `git diff --check`：**PASS**（exit 0）。
28. secret/path/pollution scan（新 R4F3 文件）：**clean**（无 secret、
    无绝对路径、无 build-time 字段）。
29. scoring artifact exact diff：registry v2 / policy v2 / shadow inputs
    v2 / capsule v5 / shadow v6 / sensitivity v8 / R4F1/R4F2 decisions /
    scoring engine **0 diff**。
30. 默认 DB SHA `4a71d3c7b88c0b16` 未变；stash 未动；保护项
    （AGENTS.md、agent/goals/、acceptance/m2_stage2i2r_*、R4E4/R4E5
    artifacts、R4F/R4F1/R4F2 decisions）未动。

walk-forward 扰动验证（validate_prototype，fixture 驱动）：future fact
不改变历史 state（59 条）、later restatement 不倒灌（1 条）、数组顺序
无关 — 全部 true。

交叉验证：

- raw PE 复算 == R4E.4 candidate ratio（逐值）。
- normalized EPS == R4F.2 diagnostics（逐值，独立重建）。
- TTM EPS 0.8642943660… == R4E.4 per_share_denominator。
- 2022/2023 restated 值由 supersession 链确定性解析。

## 结果

- 已完成：prototype contract v1、docs、纯函数模块、薄 CLI、current
  prototype v1、normalized PE snapshot v1、mechanical inversion audit v1、
  historical readiness v1、historical state ledger v1、fact gap plan v1、
  R4F3 decision、45 项测试、acceptance、工作记录。
- 决策：`PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN`
  （CONDITIONAL PASS）——current prototype TRUSTED_NON_SCORING；
  mechanical inversion property PASS；PIT resolver trusted；3y history
  coverage 不足 → 精确 fact gap plan 已冻结。
- 当前数值：normalized EPS 0.9135206151007635380066173292；raw PE
  12.81970638132453345471096950（== candidate）；normalized PE
  12.12889979366021109951970404；ratio 0.9461136965920940114716739512。
- 历史 readiness：READY 84 天（2026-03-31..2026-07-31）；3y window
  BLOCKED（644 天全 blocked）；5y window BLOCKED（1127 天全 blocked）；
  FULL_CYCLE NOT_PROVEN。状态：
  CURRENT_PROTOTYPE_TRUSTED / HISTORICAL_VALIDATION_FACT_GAPS_REMAIN。
- gap plan：MINIMUM_3Y_BACKFILL = 5 facts（2017/2018/2019 equity+NP）；
  MINIMUM_5Y_BACKFILL = 9 facts（2015..2019 equity+NP）。先补 3y
  （Section 十四 优先级原则）。
- PE numeric scoring：**BLOCKED_UNCHANGED**；valuation dimension 无数值分；
  production NOT_AUTHORIZED；overall PROHIBITED；registry/policy v2、
  shadow v6、sensitivity v8 未改。
- 未完成/未开始：R4F.3A（HISTORICAL ANNUAL FACT BACKFILL）未开始；
  3y/5y historical cycle-guard validation 未开始（fact gaps 阻塞）。
- 与本任务对比：无偏离；全部边界保持（无 score、无 percentile、无
  peak classifier、无未来泄漏、无网络、无 DB 写入）。
- 可用性：prototype/readiness/plan 产物全部生成，非评分、可复现；
  decision 为 CONDITIONAL PASS（B 分支），与预期一致。
- 提交/推送：**未提交、未推送**（本轮为本地验证阶段，未经授权）。

## 遗留问题

- 3y / 5y historical validation 因历史事实缺口 BLOCKED（见 gap plan）：
  2020 年 opening equity（2019-12-31）缺 2018/2019 前序年度事实而不可
  重建；需 R4F.3A 补采后重新评估。
- full_cycle_coverage_status=NOT_PROVEN：当前无独立证据证明覆盖完整
  earnings cycle。
- R4B/R4C/R4A 历史 manifest debt：KNOWN_NON_BLOCKING，留到 final
  milestone-wide integrity closeout；本轮 artifact_manifest =
  NOT_REQUIRED_PROTOTYPE_STAGE。
- 本阶段不建 artifact manifest（prototype 不改变正式 scoring runtime
  identity；未注册新 verifier schema）。
- 未执行：remote CI（本轮仅本地验证）；未提交未推送。

## 下一步建议

- 下一独立阶段 `R4F.3A — Historical Annual Fact Backfill`（需另行授权）：
  按 gap plan 的 MINIMUM_3Y_BACKFILL 集合补采（2017-12-31 equity +
  2018/2019 equity+NP，exchange_official tier，PIT 生效日期 <= 目标
  交易日），完成后重跑 readiness → 3y window；若 3y prototype
  validation 本身失败，则无需补 5y。
- 之后（数据充分时）执行 Section 十八 冻结的 6 项未来验证协议。
- METHOD READY != SCORING READY；PE numeric scoring 保持 BLOCKED。
- 禁止开始 R4F.3A 或任何新阶段（未经授权）。

## 最终文件变更

新增：
- `config/pe_normalized_earnings_prototype_contract_v1.json`
- `docs/pe_normalized_earnings_prototype_and_validation_protocol.md`
- `src/ashare_research/pit_valuation/pe_normalized_earnings_prototype.py`
- `src/ashare_research/tools/m2_stage2k1r4f3_pe_normalized_earnings_prototype.py`
- `reports/petrochina_pe_normalized_earnings_prototype_v1.json`
- `reports/petrochina_pe_normalized_pe_snapshot_v1.json`
- `reports/petrochina_pe_mechanical_inversion_audit_v1.json`
- `reports/petrochina_pe_normalized_earnings_historical_readiness_v1.json`
- `reports/petrochina_pe_normalized_earnings_historical_state_ledger_v1.json`
- `reports/petrochina_pe_normalized_earnings_historical_fact_gap_plan_v1.json`
- `reports/m2_stage2k1r4f3_decision.json`
- `tests/test_m2_stage2k1r4f3_pe_normalized_earnings_prototype.py`
- `acceptance/m2_stage2k1r4f3_pe_normalized_earnings_prototype.md`
- 本工作记录

修改：无（scoring contracts、既有 artifacts、既有代码全部未动）。

辅助（gitignored，不交付）：`tmp/r4f3_synthetic_walk_forward_facts.json`、
`tmp/r4f3_build_a/`、`tmp/r4f3_build_b/`。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；HEAD `83e0685`（R4F.2
  closeout）；local == origin。
- **未提交、未推送**：本轮 R4F.3 全部新增文件处于未跟踪状态
  （本地验证阶段，按 Section 二十七 要求停止）。
- 未 force push、未 reset、未 git clean、未 merge、未 PR、未 tag、
  未 release。
- 既有未跟踪/修改项（`AGENTS.md`、`agent/goals/`、
  `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`）
  为会话开始前既有状态，未纳入本轮，未改动。
- stash `stash@{0}` 未动；默认 DB SHA `4a71d3c7b88c0b16` 未变。

## 最终Git状态

（待完成。）
