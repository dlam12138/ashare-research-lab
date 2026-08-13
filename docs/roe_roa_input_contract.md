# ROE / ROA 输入契约

版本：`ashare_value_evaluation_capital_return_v1` / 1.0

状态：输入契约冻结。本文件约束 ROE/ROA 指标的输入事实选择、口径、PIT 与重列要求；
不新增 Fact、不计算 Metric。

上位合同：[资本回报方法论 v1](value_evaluation_methodology_capital_return_v1.md) 与
[机器合同](../config/value_evaluation_methodology_capital_return_v1.json)。

## 1. 指标与输入角色

| 指标 metric_id | 角色 | concept_id | period 类型 | 说明 |
|---|---|---|---|---|
| `return_on_average_equity_attributable_to_parent` | numerator | `net_profit_attributable_to_parent` | duration | 年度归母净利润 |
| | opening | `equity_attributable_to_parent` | instant | 期初年末归母权益 |
| | closing | `equity_attributable_to_parent` | instant | 期末年末归母权益 |
| `return_on_average_total_assets` | numerator | `net_profit` | duration | 年度合并净利润（BLOCKED：无可信事实） |
| | opening | `total_assets` | instant | 期初年末总资产 |
| | closing | `total_assets` | instant | 期末年末总资产 |

`input_roles` 序列：`["numerator", "opening", "closing"]`。
opening 与 closing 必须为**同一 concept_id** 的相邻两个年末 instant 值。

## 2. 口径与兼容性硬约束

每个平均对的 opening 与 closing 必须同时满足：

- **会计准则：** CAS；
- **合并口径：** consolidated（不得用母公司单体）；
- **同单位：** 均为万元（`RMB_MILLION_TO_CNY_10K_X100` 归一化后）；
- **相邻期间：** opening = `FY-1-12-31`，closing = `FY-12-31`；
- **eligible / reconciled：** 两端均 `eligible_for_metrics=true` 且 `source_tier=reconciled_derived`
  （Rule 004 双源核对输出）；
- **instant Context：** `SYMBOL|FY|instant|consolidated`，`period_start=period_end=12-31`；
  不得复用 annual duration Context。

任一不满足 -> 该年度平均不可构造，状态 `missing_input` 或 `not_comparable`，**不置零、不以单点填充**。

## 3. 分子口径禁令

- ROE 分子为 `net_profit_attributable_to_parent`（归母），ROA 分子为 `net_profit`（合并），
  **二者不可互替**。
- ROA 不得绑定 `net_profit_attributable_to_parent` 作为分子；不得静默生成 proxy。
- 扣非净利润、营业利润、总权益均不得替代上述分子或分母。

## 4. 平均余额规则

- `average = (opening + closing) / 2`；
- Decimal `prec=28`、`ROUND_HALF_EVEN`、量化 `1e-12`；
- 两时点强制：缺失任一时点不计算平均；
- 版本选择：每年输入用该年度年报可用时的 **latest 版本**（重述 v2 优先于 v1）。

## 5. PIT 规则

- `metric available_at = max(numerator.available_at, opening.available_at, closing.available_at)`；
- 只用研究时点已公开的事实版本；
- 视图须标注“当时可知”或“当前最新复核”，不得混合。

## 6. 重列传播

- 任一输入 Fact ID 或 value 因重列变化 -> 新建 Metric 版本（`result_version+1`），
  `supersedes_metric_result_id` 指向旧版；旧版保留。
- Stage 2D-B 已记录 R=4（2022/2023 归母权益与总资产 v2 重述）：FY2022/FY2023 的 opening/closing
  在重述公告日后切换为 v2，对应 Metric 必须建新版本。

## 7. 2020 开仓基线限制

- 2020 的 `comparison_only_opening_baseline` 事实（`available_at=2022-04-01`，取自 2021 年报比较列）
  **只能作为 FY2021 的 opening**。
- 不得伪装成 2020 独立年报 Fact；不得用于 FY2020 closing 或独立 ROE/ROA 计算；
- 不为 2020 建 review/v2。

## 8. 2025 复核状态

- 2025 `revision_review_status = not_yet_reviewable`；
- 作为 FY2025 closing 与 FY2026 opening 时按 latest 可用版本使用，但不视作已复核。

## 9. 状态规则汇总

| 条件 | 状态 |
|---|---|
| 全部输入就绪、分母有效且非负可比 | `computed` |
| 平均分母 = 0 | `undefined_zero_denominator` |
| ROE 平均归母权益 < 0 | `not_comparable`（枚举绑定延后至实现阶段，本阶段不改 Schema） |
| 任一输入缺失 | `missing_input`（不置零） |
| 首年无合法相邻两时点 | `insufficient_history` |

## 10. 输入就绪状态（截至 Stage 2D-B）

| 指标 | 分子就绪 | 分母就绪 | 计算 |
|---|---|---|---|
| ROE | true（`net_profit_attributable_to_parent`，Stage 2C） | true（`equity_attributable_to_parent`，Stage 2D-B，10 对就绪） | allowed_next_stage |
| ROA | **false**（`net_profit` 无可信事实） | true（`total_assets`，Stage 2D-B） | blocked |

## 11. 评分

- ROE/ROA `score_eligible=false`；
- 本契约不含 weight/score/rating/阈值/target_price/买卖建议；
- 评分 BLOCKED，须满足 [评分准入门禁](value_scoring_readiness_gates.md) 后才可研究。
