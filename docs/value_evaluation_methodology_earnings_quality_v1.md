# 盈利质量透明指标方法论扩展 v1

本扩展仅登记四个可追溯、非评分指标。它补充但不修改
`value_evaluation_methodology_v1`。所有计算必须使用公告日可得的
`reconciled_derived` Fact，保留输入 Fact ID、重列版本和 lineage；缺失不置零。

| 指标 | 公式 | 单位 | 能回答 | 不能回答 |
|---|---|---|---|---|
| 扣非归母净利润同比 | `(current/prior)-1` | ratio | 扣除已披露非经常性项目后的年度变化 | 不能证明利润可持续 |
| 毛利润 | `revenue-operating_cost` | 万元 | 收入扣除营业成本后的金额 | 不能单独判断企业好坏 |
| 毛利率 | `(revenue-operating_cost)/revenue` | ratio | 收入与营业成本口径下的毛利水平 | 不能脱离油价、炼化价差和业务结构解释 |
| 营业利润率 | `operating_profit/revenue` | ratio | 营业利润相对收入的水平 | 不是资本回报、EBIT margin 或分部利润率 |

四项指标均要求期间、CAS 与合并范围一致，需结合多年趋势、行业背景和重列信息。
中国石油属于周期企业，油气价格、炼化价差和业务结构会显著影响毛利率与营业
利润率。单年上升或下降不是企业好坏判断，也不构成投资建议。

同比在 prior 为零时不可定义，prior 为负时不可比；2021 缺少 2020 官方事实，
记录 `insufficient_history`。毛利率和营业利润率在收入为零时不可定义，收入为
负时不可比。负毛利润或负营业利润仍如实计算。

四项指标 `score_eligible=false`。评分阻塞项包括：缺少跨周期历史、行业基准、
非经常性损益独立 Fact、资本回报事实、财务安全事实和经批准的阈值/权重契约。

参考框架：

- CFA Institute Financial Statement Analysis 与 Reporting Quality；
- 财政部企业会计准则关于利润表及比较信息的要求；
- Stephen H. Penman, *Financial Statement Analysis and Security Valuation*。

这里只做短述和公式登记，不复制参考资料正文。
