# 工作记录：M2 Stage 2D-C ROE/ROA 方法论合同与 ROA 分子决策

## 基本信息

- 日期：2026-08-01
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`a36b86d`（Stage 2D-B push 落地后的 HEAD）
- 任务来源：`/goal` 指令（M2 Stage 2D-C：ROE/ROA 方法论合同与 ROA 分子决策）
- 对应模块：价值评估（资本回报方法论冻结）

## 任务目标

冻结 ROE/ROA 资本回报方法论合同，明确 ROA 分子（consolidated `net_profit`）事实缺口，
形成机器可读合同与决策矩阵。本阶段只冻结方法，不新增 Fact、不计算 Metric、不访问网络/PDF/cache、
不改 Schema/Identity/PIT。

## 范围

- 新增 `docs/value_evaluation_methodology_capital_return_v1.md`（方法论文档）；
- 新增 `config/value_evaluation_methodology_capital_return_v1.json`（机器合同）；
- 新增 `docs/roe_roa_input_contract.md`（输入契约）；
- 新增 `tests/test_capital_return_methodology.py`（合同测试）；
- 新增 `acceptance/m2_stage2dc_roe_roa_methodology_contract.md`（验收报告）；
- 追加更新 `docs/value_fact_coverage_roadmap.md`（只追加当前状态/下一步，不改写历史）；
- 新增本工作记录。

## 非目标

- 不新增 Fact、不计算 Metric、不访问网络/PDF/cache；
- 不改 Fact Schema / Metric Schema / MetricStatus 枚举 / Identity / PIT / VersionChain；
- 不修改 Rule 001-004 代码、engine/validator/version_chain/as_of/identity/service；
- 不修改 Stage 2D-B runner/evidence/restatement/report；
- 不补录 `net_profit` 事实，不计算 ROE/ROA；
- 不引入 weight/score/rating/阈值/买卖建议；
- 不 merge main，不创建 Tag/Release；
- 不执行 Stage 2D-D/2D-E/ROA 计算。

## 开始前状态

- 当前分支 `feat/m2-value-assessment-mvp`，HEAD `a36b86d`，worktree clean；
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，未动；
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（与基线一致）；
- Stage 2D-B 已落地：180 Fact（132 上游 + 48 新增）、R=4、10 平均余额输入对、年度 PIT 11/20/29/38/47；
- 63 Metric Result ID 集合 SHA：`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`；
- 上游 132 Fact ID 集合 SHA：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`；
- Concept Registry（`facts/concepts.py`）已登记 `net_profit`、`net_profit_attributable_to_parent`、
  `total_assets`、`equity_attributable_to_parent`；其中 `net_profit` 仅有语义入口，无 2021-2025 可信事实；
- MetricDefinition 结构：`metric_id/version/display_name_zh/formula/input_concept_ids/input_roles/unit`；
  `EarningsQualityMetricDefinition` 扩展 `score_eligible=False`；
- MetricStatus 枚举：`computed/insufficient_history/missing_input/undefined_zero_denominator/
  not_comparable_negative_prior/not_comparable_non_positive_profit/not_comparable_negative_revenue`；
  无专门 negative-denominator 值（实现阶段需绑定，本阶段不改枚举）。

受保护 Git blob（本次不得变更）：
Stage 2D-B runner `959fee57…`、Stage 2D-B 报告 `52c87458…`、Stage 2D-A runner `8d3ab73a…`、
2024/2025 evidence/restatement、engine.py `459adfc7…`、validator.py `4f90195f…`、
version_chain.py `292442c3…`、as_of.py `d707ec3a…`、identity.py(facts) `85c84b4e…`、
service.py `62837ed1…`、concepts.py `f3a9d425…`、metrics/models.py `16e36169…`、
metrics/identity.py `2073a297…`、metrics/engine.py `7505cccc…`、metrics/definitions.py `bb06f1e5…`、
metrics/earnings_quality_definitions.py `1bd9a75e…`、Stage 2C 报告与 runner、docs 三份方法学文件。

## 实施计划

1. 阅读北极星、methodology v1、coverage roadmap、Stage 2D-B 报告/runner、Concept Registry、
   Metric models/engine/identity/definitions；记录基线。
2. 创建本工作记录。
3. 编写 `docs/value_evaluation_methodology_capital_return_v1.md`（ROE/ROA 方法、平均余额与 PIT、
   重列传播、状态规则、口径兼容、参考裁剪、决策矩阵）。
4. 编写 `config/value_evaluation_methodology_capital_return_v1.json`（机器合同：metric_id、formula、
   input concepts/roles、period type、average rule、PIT rule、restatement rule、status rules、
   scope compatibility、score_eligible=false、references、blockers）。
5. 编写 `docs/roe_roa_input_contract.md`（输入契约：分子/分母 concept、role、period、eligible/reconciled、
   CAS/consolidated/同单位/相邻 12-31、2020 baseline 限制、2025 not_yet_reviewable）。
6. 编写 `tests/test_capital_return_methodology.py`（验证公式/口径/ROA 不绑归母/两时点/PIT max/
   重列传播/2020 baseline/score_eligible=false/无 weight-score-target_price/不变性）。
7. 编写 `acceptance/m2_stage2dc_roe_roa_methodology_contract.md`。
8. 追加更新 `docs/value_fact_coverage_roadmap.md`。
9. 门禁：ruff、compileall、targeted/full pytest、git diff --check、污染检查；证明不变性。
10. 2 个提交逐个 push。

## 决策记录

### 决策 1：ROE 分子用归母净利润，ROA 分子用合并净利润（不互替）

- 内容：ROE `return_on_average_equity_attributable_to_parent` 分子为 `net_profit_attributable_to_parent`
 （duration 归母净利润）；ROA `return_on_average_total_assets` 分子为 `net_profit`（合并净利润）。
  不得用归母净利润冒充 ROA 分子，不得静默生成 proxy。
- 原因：归母净利润与合并净利润口径不同（合并净利润含少数股东损益）；CFA FSA 与 Penman 强调
  分子分母口径匹配——归母权益配归母利润，总资产配合并利润。当前可信事实中
  `net_profit_attributable_to_parent` 已由 Stage 2C 覆盖（2021-2025），`net_profit` 无可信事实，
  故 ROE 可进入下一阶段计算，ROA 必须 BLOCKED。
- 替代方案：用归母净利润作 ROA proxy；未采用（口径不匹配，且 `/goal` 明确禁止静默 proxy，
  未来若需 proxy 必须另设 `attributable_proxy` 命名的独立方法论阶段）。
- 风险：ROA 暂不可算；但诚实记录缺口优于伪造精确性。

### 决策 2：平均余额 Decimal precision28/ROUND_HALF_EVEN/量化1e-12

- 内容：average=(opening+closing)/2，使用 Decimal precision 28、ROUND_HALF_EVEN、量化 1e-12。
- 原因：财务比率需可复算且避免浮点漂移；ROUND_HALF_EVEN 为银行家舍入，符合财务惯例；
  量化 1e-12 消除微小残差同时保留有效精度。
- 风险：与潜在其他指标舍入不一致；但本阶段只冻结方法，实现阶段（2D-D）以本合同为准。

### 决策 3：metric available_at = max(分子、opening、closing available_at)

- 内容：Metric 的 `available_at` 取三个输入事实 `available_at` 的最大值；每年输入用该年度年报
  可用时的 latest 版本。
- 原因：PIT 语义要求指标只在所有输入都对市场可用后才可得；Qlib PIT 设计说明后见数据泄漏风险。
- 风险：无；与 Stage 2D-B 的 latest-available 选择一致。

### 决策 4：不改 MetricStatus 枚举，negative-denominator 状态绑定延后至实现阶段

- 内容：本阶段不改 `MetricStatus` 枚举。状态规则记录为：分母=0->`undefined_zero_denominator`；
  ROE 平均归母权益<0->not_comparable；缺失->`missing_input`（不置零）。当前枚举无专门
  negative-denominator 值，实现阶段（2D-D）须诚实绑定到既有状态或通过治理提案新增，
  不在本阶段改 Schema。
- 原因：`/goal` 硬约束“不改 Schema/Identity/PIT”；状态规则本身可文档化，无需现在改枚举。
- 风险：实现阶段可能需枚举提案；已记为 blocker，不构成本阶段硬阻塞。

## 实际操作

（进行中，按执行顺序持续记录）

1. 读取 `agent/record/README.md`；确认分支 `feat/m2-value-assessment-mvp`、HEAD `a36b86d`、
   worktree clean、`stash@{0}` 未动。
2. 读取北极星（资本回报=ROE/ROA/ROIC + 高ROE杠杆检查）、`value_evaluation_methodology_v1`
   （§6 资本回报、§13 PIT、§14 缺失不置零、§16 参考裁剪）、`value_fact_coverage_roadmap`
   （资本回报基础、append-only 规则）、Stage 2D-B 报告/runner、`facts/concepts.py`、
   `metrics/{models,identity,definitions,earnings_quality_definitions}.py`。
3. 记录基线：默认 DB SHA、Stage 2D-B 产物 blob、metrics/concepts 代码 blob（见开始前状态）。

## 验证

实际执行（全部通过）：

1. `ruff check src tests`：exit 0（All checks passed）。
2. `compileall -q src tests`：exit 0。
3. targeted pytest（2D-C 22 + 2D-B 12 + evidence 17 = 51）：51 passed。
4. full pytest：762 passed（2 warnings，均为既有 `test_quality.py` 日期解析，与本任务无关；
   含此前因 roadmap blob 暂时漂移的 2 项 protected-blob 测试，更新引用后恢复）。
5. `git diff --check`：exit 0（仅 CRLF 行尾提示，非错误）。
6. 污染检查：`git status` 无 .duckdb/.wal/.pdf/.png 入库；默认 `data/research.duckdb` SHA 不变；
   `stash@{0}` 未动。

不变性证明（测试 `test_protected_stage2db_and_metric_files_unchanged` 等覆盖）：
- 默认 DB SHA=`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（不变）；
- 上游 132 Fact ID 集合 SHA=`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`（不变）；
- 63 Metric Result ID 集合 SHA=`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`（不变）；
- Stage 2D-B runner/report/evidence/restatement、Stage 2D-A 产物、Rule 001-004 代码（engine/validator/
  version_chain/as_of/identity(facts)/service）、Metric 代码（models/identity/engine/definitions/
  earnings_quality_definitions）、Concept Registry Git blob 全部不变。

跨阶段共享文档处理：`docs/value_fact_coverage_roadmap.md` 经 append-only 追加（Stage 2D-C 状态 + 下一步 A/B/C），
blob 由 `9d737e00…` 推进至 `04d323dd…`，历史基线文本不变。Stage 2C-D、2D-A、2D-B 三处 protected-blob 测试的
roadmap 引用已同步更新为新 blob（surgical edit + 注释说明），三处测试恢复通过。
`docs/value_evaluation_methodology_v1.md` 与 `docs/value_scoring_readiness_gates.md` 未修改，blob 不变。

## 结果

- 资本回报方法论合同冻结完成；ROE/ROA 公式、口径、平均余额、PIT、重列传播、状态规则全部机器可读。
- 决策矩阵落地：ROE inputs_ready=true/methodology_ready=true/metric_computation=allowed_next_stage；
  ROA denominator_ready=true/numerator_ready=false/required_fact=net_profit/metric_computation=blocked；
  ROIC blocked；scoring blocked。
- ROE 分子（归母净利润，Stage 2C）与分母（平均归母权益，Stage 2D-B）均就绪；
  ROA 分子 `net_profit` 2021-2025 无可信事实，BLOCKED，未补录、未用归母净利润冒充、未静默生成 proxy。
- 零既有文件语义修改：仅 append-only 追加 roadmap + 3 处 protected-blob 引用同步更新；其余为新增文件。
- 全部门禁通过；不新增 Fact、不计算 Metric、不访问网络/PDF/cache、不改 Schema/Identity/PIT。

## 遗留问题

- 无硬阻塞。
- `MetricStatus` 枚举无专门 negative-denominator 值；ROE 平均归母权益<0 的 `not_comparable` 绑定
  延后至实现阶段（Stage 2D-D）诚实处理或通过治理提案新增枚举。本阶段不改 Schema（决策 4）。
- ROA 计算仍 BLOCKED，须 Stage 2D-E 完成 `net_profit` 官方事实与重列覆盖后才允许（下一阶段 B/C）。

## 下一步建议

仅价值评估核心目标内：
- **A. Stage 2D-D：ROE 透明 Metric 计算。** 基于本合同与 Stage 2D-B 平均余额输入对，透明计算 2021-2025 ROE。
- **B. Stage 2D-E：2021-2025 consolidated `net_profit` 官方事实与重列。**
- **C.** `net_profit` 覆盖与重列完成后才允许 ROA 计算。

## 最终文件变更

新增（6 个文件）：
1. `docs/value_evaluation_methodology_capital_return_v1.md`
2. `config/value_evaluation_methodology_capital_return_v1.json`
3. `docs/roe_roa_input_contract.md`
4. `tests/test_capital_return_methodology.py`
5. `acceptance/m2_stage2dc_roe_roa_methodology_contract.md`
6. `agent/record/2026-08-01_0915_m2_stage2dc_roe_roa_methodology_contract.md`（本记录）

修改（4 处 surgical edit，无语义改动）：
1. `docs/value_fact_coverage_roadmap.md`（append-only 追加 Stage 2D-C 状态与下一步 A/B/C）；
2. `tests/test_official_earnings_quality_2025_acceptance.py`（roadmap blob 引用更新）；
3. `tests/test_official_roe_roa_denominator_2025_acceptance.py`（roadmap blob 引用更新）；
4. `tests/test_official_roe_roa_denominator_foundation.py`（roadmap blob 引用更新）。

## 最终Git状态

（待填）
