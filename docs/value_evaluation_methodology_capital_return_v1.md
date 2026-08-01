# 资本回报方法论合同 v1（ROE / ROA）

方法论 ID：`ashare_value_evaluation_capital_return_v1`

版本：1.0

状态：方法论合同冻结；ROE 方法与输入就绪、下一阶段可计算；ROA 分子事实缺口未覆盖、计算 BLOCKED；
评分仍未准入。

上位文件：[价值评价方法论基线 v1](value_evaluation_methodology_v1.md) §6 资本回报、§13 PIT、§14 缺失数据处理、§16 参考裁剪。本文件只冻结资本回报方法，不新增 Fact、不计算 Metric、不改 Schema/Identity/PIT。

## 1. 方法论目标

把官方披露的期间利润与平均资产负债表余额透明匹配，形成可复算、可反驳的资本回报指标合同。
指标只回答“账面投入的权益或资产产生了多少期间回报”，不回答估值、买卖或评分。

本阶段只冻结方法与口径，不新增 Fact、不计算 Metric。机器合同见
[config/value_evaluation_methodology_capital_return_v1.json](../config/value_evaluation_methodology_capital_return_v1.json)，
输入契约见 [roe_roa_input_contract.md](roe_roa_input_contract.md)。

## 2. 两条核心口径禁令

1. **分子分母口径必须匹配。** ROE 分子为归母净利润、分母为平均归母权益；ROA 分子为合并净利润、
   分母为平均总资产。不得用归母净利润冒充 ROA 分子，不得用总权益替代归母权益，不得用扣非利润
   替代报告净利润。未来若需要归母口径的 ROA 代理，必须另设带 `attributable_proxy` 名称的独立
   方法论阶段，不得静默生成。
2. **分母必须是两时点平均。** instant 余额（年末）与 duration 利润（年度）口径不同；只用期末余额
   会混合 duration 与 instant。平均余额 = (期初 + 期末) / 2，期初期末必须相邻 12-31。

## 3. ROE canonical metric

- **metric_id：** `return_on_average_equity_attributable_to_parent`
- **中文名称：** 基于平均归母权益的净资产收益率
- **公式：**
  `net_profit_attributable_to_parent / ((opening_equity_attributable_to_parent + closing_equity_attributable_to_parent) / 2)`
- **单位：** ratio
- **分子：** `net_profit_attributable_to_parent`，年度 duration 归母净利润。
- **分母：** `equity_attributable_to_parent` 的期初与期末 instant 值算术平均。
- **口径：** 合并、CAS、归母口径；不得使用单一年末权益、总权益或扣非利润。
- **理论用途：** 描述归属母公司股东权益在一年内产生的报告回报。
- **能回答：** 归母权益的账面回报率量级与方向。
- **不能回答：** 回报由杠杆还是经营效率驱动、是否可持续、估值便宜与否、是否应买卖。
- **高 ROE 杠杆检查：** 高 ROE 可能由高杠杆（低权益、高负债）形成，必须结合资产负债结构与
  ROA/财务安全共同解释，不得把高 ROE 直接等同于优质。

### ROE 输入就绪状态

- 分子 `net_profit_attributable_to_parent`：Stage 2C-C.1/2C-D 已覆盖 2021-2025 可信事实（duration）。
- 分母 `equity_attributable_to_parent`：Stage 2D-B 已覆盖 2020-2025 instant 事实（含 R=4 重述），
  10 条平均余额输入对就绪。
- 决策：`inputs_ready=true`，`methodology_ready=true`，`metric_computation=allowed_next_stage`。

## 4. ROA canonical metric

- **metric_id：** `return_on_average_total_assets`
- **中文名称：** 基于平均总资产的资产收益率
- **公式：**
  `net_profit / ((opening_total_assets + closing_total_assets) / 2)`
- **单位：** ratio
- **分子：** `net_profit`，年度 duration **合并净利润**（含少数股东损益，非归母净利润）。
- **分母：** `total_assets` 的期初与期末 instant 值算术平均。
- **口径：** 合并、CAS；分子为合并净利润，不得用归母净利润替代。
- **理论用途：** 描述全部资产在一年内产生的报告回报，与 ROE 对照识别杠杆贡献。

### ROA 分子事实缺口（BLOCKER）

- 当前可信 Fact 中**没有 2021-2025 `net_profit`**（合并净利润）。Concept Registry 仅登记了语义入口，
  不等于已有可信官方事实（见方法论基线 v1 §14）。
- 分母 `total_assets`：Stage 2D-B 已覆盖 2020-2025 instant 事实，`denominator_ready=true`。
- 决策：`denominator_ready=true`，`numerator_ready=false`，`required_fact=net_profit`，
  `metric_computation=blocked`。
- 本阶段不得自行补录 `net_profit`，不得用归母净利润冒充，不得静默生成 proxy。
  ROA 计算必须在 Stage 2D-E 完成 `net_profit` 官方事实与重列覆盖后才允许。

## 5. 平均余额规则

- **公式：** `average = (opening + closing) / 2`
- **精度：** Python `decimal.Decimal`，`getcontext().prec = 28`，`ROUND_HALF_EVEN`（银行家舍入），
  量化到 `1e-12`（`Decimal("0.000000000001")`）。
- **两时点强制：** opening 与 closing 必须同时存在且为相邻年末（12-31）；缺失任一时点不计算平均，
  不以单点或零填充。
- **版本选择：** 每年输入使用该年度年报可用时（`available_at` <= 研究时点）的 **latest 版本**；
  重述后的 v2 值优先于 v1。
- **2020 开仓基线限制：** 2020 的 `comparison_only_opening_baseline` 事实只能作为 FY2021 的 opening，
  不得伪装成 2020 独立年报 Fact，不得用于 FY2020 的 closing 或独立 ROE/ROA 计算。
- **2025 复核状态：** 2025 `revision_review_status` 保持 `not_yet_reviewable`；其作为 FY2025 closing
  与 FY2026 opening 时按 latest 可用版本使用，但不视作已复核。

## 6. Point-in-Time 规则

- **metric available_at = max(分子 available_at, opening available_at, closing available_at)。**
  指标只在所有输入事实都对市场可用后才可得。
- **PIT 查询：** 只能使用研究时点已经公开的事实版本；后续年报比较列出现的重述不得回写覆盖
  当时认知（Qlib PIT 防泄漏原则）。
- **视图标注：** 评价必须指明“当时可知”还是“当前最新复核”视图，不得混合两个时间面。

## 7. 重列传播规则

- 当任一输入 Fact 的 ID 或 value 因重列发生变化（如 Stage 2D-B 的 R=4：2022/2023 归母权益与
  总资产 v2 重述），必须创建新 Metric 版本（`result_version` +1）并以 `supersedes_metric_result_id`
  连接旧版本。
- 旧版本保留，不删除；PIT 查询按 `available_at` 返回当时可得版本。
- `metric_result_id` 由 `build_metric_result_id` 规范生成（含 `input_fact_ids`、`result_version`、
  `available_at`、`supersedes_metric_result_id`），重列导致输入变化时 ID 自然更新。

## 8. 状态规则

- **average denominator = 0：** `undefined_zero_denominator`（既有枚举）。
- **ROE 平均归母权益 < 0：** `not_comparable`（负分母使比率失真）。
  当前 `MetricStatus` 枚举无专门 negative-denominator 值；实现阶段（Stage 2D-D）须诚实绑定到既有
  状态并明确标注，或通过治理提案新增枚举值。**本阶段不改 Schema/枚举。**
- **任一输入缺失：** `missing_input`；缺失不得置零，不得以比较列、第三方口径或估算值静默填充。
- **历史不足：** 首年（FY2021 opening 依赖 2020 baseline）若无合法相邻两时点，`insufficient_history`。
- **可计算：** 全部输入就绪、分母有效且非负可比时 `computed`。

## 9. 口径兼容性

| 维度 | ROE | ROA |
|---|---|---|
| 分子 concept | `net_profit_attributable_to_parent` | `net_profit` |
| 分母 concept | `equity_attributable_to_parent` | `total_assets` |
| 分子 period | duration（年度） | duration（年度） |
| 分母 period | instant（年末）×2 | instant（年末）×2 |
| 会计准则 | CAS | CAS |
| 合并口径 | consolidated | consolidated |
| 单位 | 万元（分子分母同单位） | 万元（分子分母同单位） |
| 期初期末 | 相邻 12-31 | 相邻 12-31 |
| eligible | 分子分母均 eligible/reconciled | 分子分母均 eligible/reconciled |

opening 与 closing 必须同 concept、同单位、同 CAS、同 consolidated 口径、相邻 12-31；
任一不满足则该年度平均不可构造（`missing_input` 或 `not_comparable`）。

## 10. 评分准入

- ROE/ROA 的 `score_eligible = false`。
- 本合同不含 weight、score、rating、阈值、等级、总分或买卖建议。
- 评分仍 BLOCKED；须满足 [评分准入门禁](value_scoring_readiness_gates.md) 全部门禁后才可另行研究。

## 11. 决策矩阵

| 指标 | inputs_ready | methodology_ready | metric_computation | 说明 |
|---|---|---|---|---|
| ROE | true | true | allowed_next_stage | 分子（归母净利润）与分母（平均归母权益）事实均已覆盖 |
| ROA | denominator=true / numerator=false | true | blocked | 分母（平均总资产）就绪；分子 `net_profit` 无可信事实 |
| ROIC | false | false | blocked | NOPAT 与投入资本口径未登记，不讨论实现 |
| scoring | — | — | blocked | 评分门禁未触发 |

## 12. 推荐下一阶段（不在本阶段执行）

- **A. Stage 2D-D：ROE 透明 Metric 计算。** 基于 ROE 合同与本阶段平均余额输入对，透明计算
  2021-2025 ROE Metric Result，PIT 与重列传播以本合同为准。
- **B. Stage 2D-E：2021-2025 consolidated `net_profit` 官方事实与重列。** 补齐 ROA 分子事实覆盖。
- **C. 之后才允许 ROA 计算。** 在 `net_profit` 事实覆盖与重列完成后，按 ROA 合同计算。

本阶段不得执行 A/B/C。

## 13. 参考依据与裁剪（只写方法摘要，不复制书籍正文）

- **CFA Institute FSA**（[导论](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/introduction-financial-statement-analysis)、
  [分析技术](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/financial-analysis-techniques)、
  [报告质量](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/evaluating-quality-financial-reports)）：
  采用“期间利润与平均资产负债表余额匹配”和“分子分母口径一致”原则；不照搬其指标库。
- **Penman, *Financial Statement Analysis and Security Valuation*, 5th ed., McGraw-Hill, 2013：**
  采用归属口径与资本回报的解释连接（归母权益配归母利润、总资产配合并利润）；不猜测未取得正文。
- **财政部 CAS**（[基本准则](https://www.mof.gov.cn/kkml/caizhengwengao/caizhengbuwengao2006/caizhengwengao20061/200805/t20080519_23593.htm)、
  [CAS 30 财务报表列报](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/200806/t20080618_46218.htm)、
  [CAS 28](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/200806/t20080618_46220.htm)）：
  采用合并报表、比较信息与重列依据；不引入其条文为本地法律结论。
- **[Qlib PIT](https://qlib.readthedocs.io/en/stable/advanced/PIT.html) /
  [OpenLineage](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md)：**
  采用按发布日期保留历史可得版本与输入/输出血缘；不引入其存储或外部服务。

以上仅做方法蒸馏与书目登记，不从书名推断未公开内容，不复制书籍正文。
