# M2 Stage 2D-C 验收：ROE/ROA 方法论合同与 ROA 分子决策

对应分支：`feat/m2-value-assessment-mvp`
开始提交：`a36b86d`（Stage 2D-B push 落地后）
阶段性质：方法论合同冻结；不新增 Fact、不计算 Metric、不访问网络/PDF/cache、不改 Schema/Identity/PIT。

## 1. 结论（决策矩阵）

| 指标 | inputs_ready | methodology_ready | metric_computation |
|---|---|---|---|
| **ROE** `return_on_average_equity_attributable_to_parent` | true | true | **allowed_next_stage** |
| **ROA** `return_on_average_total_assets` | denominator=true / numerator=false | true | **blocked** |
| ROIC | false | false | blocked（不讨论实现） |
| scoring | - | - | blocked |

- ROE 分子 `net_profit_attributable_to_parent`（Stage 2C 覆盖）与分母平均归母权益（Stage 2D-B 覆盖，10 对就绪）均就绪。
- ROA 分母平均总资产就绪；**分子 `net_profit`（合并净利润）无 2021-2025 可信事实**，`required_fact=net_profit`，计算 BLOCKED。

## 2. ROE canonical metric

- **公式：** `net_profit_attributable_to_parent / ((opening_equity_attributable_to_parent + closing_equity_attributable_to_parent) / 2)`
- **input_concepts：** `[net_profit_attributable_to_parent, equity_attributable_to_parent, equity_attributable_to_parent]`
- **input_roles：** `[numerator, opening, closing]`
- **input_period_types：** numerator=duration；opening/closing=instant
- **口径：** 合并、CAS、归母口径；不得使用单一年末权益、总权益或扣非利润。
- **高 ROE 杠杆检查：** 高 ROE 可能由高杠杆形成，须结合资产负债结构与 ROA/财务安全共同解释。

## 3. ROA canonical metric 与分子决策

- **公式：** `net_profit / ((opening_total_assets + closing_total_assets) / 2)`
- **input_concepts：** `[net_profit, total_assets, total_assets]`
- **input_roles：** `[numerator, opening, closing]`
- **分子口径：** `consolidated_net_profit`（合并净利润，含少数股东损益）。
- **禁令：** 不得用 `net_profit_attributable_to_parent` 冒充 ROA 分子；不得静默生成 proxy。
  未来若需归母口径 ROA 代理，必须另设带 `attributable_proxy` 名称的独立方法论阶段。
- **BLOCKER：** `net_profit` 2021-2025 无可信事实（Concept Registry 仅登记语义入口）。
  ROA 计算必须在 Stage 2D-E 完成 `net_profit` 官方事实与重列覆盖后才允许。

## 4. 平均余额与 PIT 规则

- **平均：** `(opening + closing) / 2`，Decimal `prec=28`、`ROUND_HALF_EVEN`、量化 `1e-12`。
- **两时点强制：** opening/closing 必须同时存在且相邻 12-31；缺失不计算平均、不置零。
- **版本选择：** 每年输入用该年度年报可用时的 latest 版本（重述 v2 优先）。
- **PIT：** `metric available_at = max(numerator, opening, closing available_at)`；只用研究时点已公开版本；
  视图标注“当时可知”或“当前最新复核”。
- **重列传播：** 任一输入 Fact ID/value 变化 -> 新 Metric 版本（`result_version+1`，
  `supersedes_metric_result_id` 连接旧版）；旧版保留。Stage 2D-B R=4（2022/2023 重述）将传播到 FY2022/FY2023 Metric。

## 5. 状态规则

| 条件 | 状态 |
|---|---|
| 平均分母 = 0 | `undefined_zero_denominator` |
| ROE 平均归母权益 < 0 | `not_comparable` |
| 任一输入缺失 | `missing_input`（不置零） |
| 首年无合法相邻两时点 | `insufficient_history` |
| 全部就绪且分母有效非负可比 | `computed` |

`MetricStatus` 枚举无专门 negative-denominator 值；实现阶段（Stage 2D-D）须诚实绑定或通过治理提案新增。
**本阶段不改 Schema/枚举**（决策 4）。

## 6. 口径兼容性

opening/closing 必须同 concept、同单位（万元）、CAS、consolidated、相邻 12-31、eligible/reconciled；
instant Context `SYMBOL|FY|instant|consolidated`，不复用 duration Context。

## 7. 2020 开仓基线限制与 2025 状态

- 2020 `comparison_only_opening_baseline`（`available_at=2022-04-01`，取自 2021 年报比较列）只能作 FY2021 opening；
  不得伪装成 2020 独立年报 Fact，不用于 FY2020 closing 或独立计算；不为 2020 建 review/v2。
- 2025 `revision_review_status` 保持 `not_yet_reviewable`；作 FY2025 closing/FY2026 opening 时按 latest 可用版本使用。

## 8. 评分准入

- ROE/ROA `score_eligible=false`；
- 机器合同 `forbidden_fields=[weight, score, rating, threshold, target_price, buy, sell]`，
  递归扫描全部 JSON key 无任何禁止字段命中（`score_eligible`/`score_blockers` 为门禁字段，非分值，不命中 exact key `score`）；
- 评分 BLOCKED，须满足 [评分准入门禁](../docs/value_scoring_readiness_gates.md) 后才可研究。

## 9. 参考依据与裁剪（方法摘要，不复制书籍正文）

- CFA FSA：期间利润与平均资产负债表余额匹配、分子分母口径一致。
- Penman：归属口径与资本回报解释连接（归母权益配归母利润、总资产配合并利润）。
- 财政部 CAS：合并报表、比较信息与重列依据。
- Qlib PIT / OpenLineage：按发布日期保留历史可得版本与输入/输出血缘。

## 10. 下一阶段（不在本阶段执行）

- **A. Stage 2D-D：** ROE 透明 Metric 计算（基于本合同与 Stage 2D-B 平均余额输入对）。
- **B. Stage 2D-E：** 2021-2025 consolidated `net_profit` 官方事实与重列。
- **C.** `net_profit` 覆盖与重列完成后才允许 ROA 计算。

本阶段 `this_stage_executes = none_of_A_B_C`。

## 11. 变更范围

本阶段实际变更（提交 `ecfde23` + `ff6f6ab`）：

**新增文件（6 个，方法论/测试/验收/记录）：**

- `docs/value_evaluation_methodology_capital_return_v1.md`（方法论）
- `config/value_evaluation_methodology_capital_return_v1.json`（机器合同）
- `docs/roe_roa_input_contract.md`（输入契约）
- `tests/test_capital_return_methodology.py`（22 项合同测试）
- `acceptance/m2_stage2dc_roe_roa_methodology_contract.md`（本报告）
- `agent/record/2026-08-01_0915_m2_stage2dc_roe_roa_methodology_contract.md`（工作记录）

**既有文件修改（4 处 surgical edit，无语义改动）：**

- `docs/value_fact_coverage_roadmap.md`：append-only 追加 Stage 2D-C 状态与下一步 A/B/C（历史基线文本未改写）；
- `tests/test_official_earnings_quality_2025_acceptance.py`：同步 roadmap blob 引用（`9d737e00…`→`04d323dd…`）；
- `tests/test_official_roe_roa_denominator_2025_acceptance.py`：同上同步；
- `tests/test_official_roe_roa_denominator_foundation.py`：同上同步。

除以上 surgical edits 外，既有代码、事实、指标和方法论基线未改变。

## 12. 不变性证明

- 默认 `data/research.duckdb` SHA-256 = `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（不变）；
- 上游 132 Fact ID 集合 SHA = `1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`（不变）；
- 63 Metric Result ID 集合 SHA = `34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`（不变）；
- Stage 2D-B runner/report/evidence/restatement、Stage 2D-A 产物、Rule 001-004 代码（engine/validator/version_chain/as_of/identity/service）、
  Metric 代码（models/identity/engine/definitions/earnings_quality_definitions）、Concept Registry Git blob 全部不变（测试 `test_protected_stage2db_and_metric_files_unchanged` 覆盖）；
- `stash@{0}` 未动（测试 `test_stash_unchanged` 覆盖）。

## 13. 工程门禁

- `ruff check src tests`：exit 0；
- `compileall -q src tests`：exit 0；
- targeted + full pytest：全部通过；
- `git diff --check`：exit 0；
- 污染检查：无 DB/PDF/PNG 入库；提交范围见 §11（6 新增 + 4 surgical edit），最终 worktree clean。

## 14. 最终状态

- 分支 `feat/m2-value-assessment-mvp`，2 个提交（`ecfde23` 方法论合同、`ff6f6ab` 验收报告）均已 push；
- worktree clean，local/origin/remote 一致；
- 不 merge main，不建 Tag/Release。
