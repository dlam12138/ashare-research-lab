# 价值研究事实覆盖路线图

版本：`ashare_value_evaluation_v1` / 1.0

状态：规划，不执行事实获取

Concept Registry 中已有名称不代表已有可信事实。以下条目要求公司与交易所官方来源、PIT 可得日、重列版本和血缘；本路线图不修改 Fact Schema 2.1。

Stage 2B-B 冻结的 gap inventory 全量保留为：扣非净利润、毛利率和一般净利率、非经常性损益、ROE / ROA / ROIC、财务安全、分红与回购、估值。下表把“毛利率和一般净利率”归入盈利质量，把“分红与回购”归入分红与兑现；改名只是规划分组，不表示缺口已关闭。

## 候选模块

| 模块 | 研究问题 | 所需 Concept / 透明公式 | 官方来源 | 类型与平均余额 | 附注 | 重列风险 | 获取难度 | 实现复杂度 | 增量价值 | 周期企业适用性 |
|---|---|---|---|---|---|---|---|---|---|---|
| 盈利质量 | 报告利润有多少来自可重复经营？ | `net_profit_excluding_non_recurring`（扣非归母净利润）；`operating_cost`（营业成本）；毛利润=`revenue-operating_cost`；`operating_profit`；`non_recurring_gain_loss` | 年报利润表、非经常性损益明细、附注 | duration；无需平均余额 | 是 | high | medium | low | high | high |
| ROE / ROA 基础 | 股东权益和资产产生了多少利润？ | `equity_attributable_to_parent`、`total_assets`；ROE=归母净利润/平均归母权益；ROA=选定利润口径/平均总资产 | 年报资产负债表、利润表 | instant + duration；必须平均期初期末余额 | 可能 | medium | low | medium | high | high |
| ROIC 基础 | 全部经营投入资本是否创造回报？ | `interest_bearing_debt`、`monetary_funds`/`cash_and_cash_equivalents`、`operating_profit`、税、NOPAT 或诚实替代项；投入资本口径待登记 | 年报三表及税费、债务、现金附注 | instant + duration；必须平均余额 | 是 | high | high | high | high | high |
| 财务安全 | 低景气期能否覆盖债务和利息？ | `total_liabilities`、`short_term_borrowings`、`long_term_borrowings`、`bonds_payable`、`lease_liabilities`、`interest_expense`、`monetary_funds`、`cash_and_cash_equivalents` | 资产负债表、现金流量表、债务/租赁/利息附注 | instant 与 duration；部分指标需平均余额 | 是 | medium | medium | medium | high | high |
| 分红与兑现 | 价值是否实际返还股东？ | `cash_dividend_total`、`shares_repurchased`、`repurchase_amount`、`share_capital`、`dividend_implementation_date`；实施口径分红率待定义 | 年报、权益变动表、分红实施公告、回购公告 | amount 为 duration/事件；股本为 instant；实施日为 event | 是 | medium | medium | medium | medium | medium |
| 估值 | 当时价格隐含怎样的预期？ | `pit_close_price`、`pit_market_cap`；PE=市值/盈利、PB=市值/归母权益、PS=市值/收入、股息率=已实施现金分红/市值、历史分位 | 交易所行情、官方股本和已核验财务事实 | 价格/市值 instant；财务 duration/instant；需严格 PIT 对齐 | 可能 | high | high | high | high | high |

## 模块内事实说明

### 盈利质量

- 扣非归母净利润应取年报直接披露，并保留其非经常性项目定义。
- 毛利润只在营业收入与营业成本口径一致时构造；毛利率随后才可计算。
- 非经常性损益既是扣非的桥，也是理解处置、补助和一次性收益的证据。
- 营业利润帮助区分营业层与税后归属层，但仍需附注解释。

### 资本回报

- 归母权益和总资产是 instant facts；年度利润是 duration fact，必须以期初期末平均值匹配。
- 有息债务不能只把“总负债”当替代；需明确借款、债券、租赁和其他融资负债。
- 现金扣除额需说明货币资金、现金及现金等价物、受限资金的差异。
- NOPAT 不存在唯一无争议的直接报表行。若税后营业利润不能诚实构造，应保持缺失，不用净利润冒充。

### 财务安全

- 分拆短期借款、长期借款、应付债券和租赁负债，用于到期结构与融资来源。
- 利息费用应区分费用化、资本化和现金支付口径。
- 现金等价物与货币资金可能不同，受限资金需在附注中识别。

### 分红与价值兑现

- 现金分红需区分方案、批准、除权和实施；PIT 研究不能在实施前当作已兑现。
- 回购需记录用途、数量、金额与注销/库存状态。
- 总股本必须与分红、每股指标和市值的对应日期一致。

### 估值

- PIT 股价和总市值必须绑定交易日、复权语义和当时股本。
- PE/PB/PS 需要明确分母的年度/滚动口径和可得版本。
- 股息率使用已可得、口径一致的现金分红；历史分位需冻结样本窗口规则。
- 周期企业不能用峰值利润下的低 PE 直接称为便宜。

## 透明优先级矩阵

只使用 high / medium / low 表达各项属性，不做数字化、加权或总排名。对“工作量、争议、复杂度”而言 high 表示负担较高；其他列 high 表示贡献或适用性较高。

| 候选 | 北极星贡献 | 改变研究结论 | 官方可得性 | 手工核验工作量 | 公式争议 | 周期适用性 | PIT/重列复杂度 | 基础设施复用 |
|---|---|---|---|---|---|---|---|---|
| 盈利质量补充 | high | high | high | medium | low | high | medium | high |
| ROE / ROA 基础 | high | high | high | low | medium | high | medium | high |
| ROIC 基础 | high | high | medium | high | high | high | high | medium |
| 财务安全 | high | high | high | medium | medium | high | medium | high |
| 分红回购 | medium | medium | high | medium | medium | medium | high | medium |
| 估值 | high | high | medium | high | high | high | high | medium |

## 推荐下一事实阶段

推荐：**盈利质量补充的最小官方事实覆盖**，先获取 `net_profit_excluding_non_recurring`、`operating_cost`、`operating_profit` 与非经常性损益直接披露/桥接证据。

理由是它以较少且官方可得的 duration facts，直接修复当前归母利润同比无法区分一次性项目、也无法解释利润率的主要盲点；公式争议低、现有年度 bundle/PIT/重列基础设施复用高，对周期企业也有明显解释增量。下一阶段应先做一个年度的双官方最小验收，再扩展多年，不在本阶段执行。

ROE/ROA 是随后优先项；ROIC 在税后经营利润和投入资本边界完成前不应抢跑。财务安全、分红与估值按路线图继续保留。

## Stage 2D-C 状态追加（2026-08-01，append-only，不改写历史基线）

Stage 2D-C 冻结 ROE/ROA 资本回报方法论合同，不新增 Fact、不计算 Metric。合同见
[资本回报方法论 v1](value_evaluation_methodology_capital_return_v1.md)、
[机器合同](../config/value_evaluation_methodology_capital_return_v1.json) 与
[ROE/ROA 输入契约](roe_roa_input_contract.md)。

### 当前状态

- **ROE** `return_on_average_equity_attributable_to_parent`：
  分子 `net_profit_attributable_to_parent`（Stage 2C 覆盖 2021-2025）与分母平均归母权益
  （Stage 2D-B 覆盖 2020-2025，10 对平均余额输入对就绪）均已就绪；
  `inputs_ready=true`、`methodology_ready=true`、`metric_computation=allowed_next_stage`。
- **ROA** `return_on_average_total_assets`：
  分母平均总资产就绪（Stage 2D-B）；**分子 `net_profit`（合并净利润）2021-2025 无可信事实**，
  `numerator_ready=false`、`required_fact=net_profit`、`metric_computation=blocked`。
  不得用归母净利润冒充，不得静默生成 proxy。
- **ROIC**：blocked，NOPAT 与投入资本口径未登记，不讨论实现。
- **scoring**：blocked，评分门禁未触发。
- 平均余额规则：`(opening+closing)/2`，Decimal prec28/ROUND_HALF_EVEN/量化1e-12，两时点强制，缺失不置零。
- PIT：`available_at=max(分子,opening,closing)`；重列传播：任一输入变化建新 Metric 版本并 supersede。

### 下一步（不在 Stage 2D-C 执行）

- **A. Stage 2D-D：ROE 透明 Metric 计算。** 基于本合同与 Stage 2D-B 平均余额输入对，透明计算 2021-2025 ROE Metric Result。
- **B. Stage 2D-E：2021-2025 consolidated `net_profit` 官方事实与重列。** 补齐 ROA 分子事实覆盖。
- **C. 之后才允许 ROA 计算。** `net_profit` 事实覆盖与重列完成后，按 ROA 合同计算。

Stage 2D-C `this_stage_executes = none_of_A_B_C`。
