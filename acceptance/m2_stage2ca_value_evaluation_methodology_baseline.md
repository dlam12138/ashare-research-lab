# M2 Stage 2C-A：价值评价方法论基线与事实覆盖路线图正式验收

日期：2026-07-30

分支：`feat/m2-value-assessment-mvp`

起始提交：`5c9f0f7e0ed2e0ae1db6c8dab6f1a7f89825f524`

方法论：`ashare_value_evaluation_v1` / 1.0

## 1. 验收结论

```text
M2 Stage 2C-A: PASS
Value evaluation methodology: TRUSTED
Recommended fact extension: ALLOWED
Scoring: STILL NOT YET
```

本阶段建立了方法论、六项现有指标的解释合同、机器可读注册表、事实覆盖路线图与评分准入门禁。它没有新增事实或指标，没有改变任何公式、Schema、ID、runner 或数据库，也没有产生分值、权重、数值阈值、企业总分、上涨概率或买卖建议。

## 2. 审查过的项目文件

- `A股个股研究与市场机制验证平台-项目北极星.md`
- `A股项目北极星-李大霄投资思想增补稿.md`
- Stage 2A、Stage 2B-A、Stage 2B-B 正式验收报告
- `src/ashare_research/metrics/definitions.py`
- `src/ashare_research/metrics/cashflow_definitions.py`
- `src/ashare_research/metrics/models.py`
- `src/ashare_research/metrics/engine.py`
- `src/ashare_research/facts/concepts.py`
- Stage 2B-B `gap_inventory`
- `AGENTS.md` 检索结果：仓库内不存在该文件

确认现有 Fact Schema 2.1 与 Metric Schema 1.0 无需修改。

## 3. 官方与专业规范

核验并采用：

- [财政部《企业会计准则——基本准则》](https://www.mof.gov.cn/gkml/caizhengwengao/caizhengbuwengao2006/caizhengwengao20061/200805/t20080519_23593.htm)：实际交易、可靠完整、经济实质的事实边界。
- [财政部 CAS 30 财务报表列报](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/200806/t20080618_46218.htm)、[CAS 28 会计政策、估计变更和差错更正](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/200806/t20080618_46220.htm) 和 [准则索引（含 CAS 31 现金流量表）](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/index_3.htm)：报表构成、可比性、现金流与重列。
- [证监会年度报告内容与格式准则](https://www.csrc.gov.cn/csrc/c101954/c7547588/content.shtml) 和 [上交所信息披露管理办法](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/mainipo/c/c_20250515_10779032.shtml)：正式披露、责任与时点边界。
- [IFRS Foundation IAS 7](https://www.ifrs.org/issued-standards/list-of-standards/ias-7-statement-of-cash-flows/)：经营、投资、筹资现金流和非现金交易边界。
- CFA Institute 的 [Financial Statement Analysis 导论](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/introduction-financial-statement-analysis)、[分析技术](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/financial-analysis-techniques) 和 [报告质量](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/evaluating-quality-financial-reports)：目标—数据—处理—解释—结论—跟进流程，以及历史、同行和现金/利润交叉分析。

这些规范用于方法与证据边界，不被解释为评分阈值。

## 4. 经典书籍

只登记可靠书目信息和公开可核验的方法定位，没有复制受版权保护的长段正文：

- Stephen H. Penman, *Financial Statement Analysis and Security Valuation*, 5th ed., McGraw-Hill, 2013：会计信息、盈利质量以及报表与估值连接。
- Aswath Damodaran, *Investment Valuation*；[作者 NYU 页面](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/Inv3ed.htm)：估值假设、现金流、风险和周期企业的规范化。
- McKinsey & Company, *Valuation*；[Wiley 系列页](https://books.wiley.com/series/wiley-valuation-7e/)：ROIC、增长、价值创造和资本配置。
- CFA Financial Statement Analysis 公开课程资料：规范化财务报表分析流程。
- 李大霄，《李大霄投资战略（第三版）》，经济日报出版社，2025，以及项目本地增补稿：长期主义、风险纪律和行为约束；不作为公式、评分权重或交易信号来源。

无法合法取得的书籍正文没有被猜测为具体章节结论。

## 5. 开源架构参考与裁剪

| 项目 | 借鉴 | 未照搬 |
|---|---|---|
| FinanceToolkit | 显式公式、单项指标与维度分层 | 不引入其外部数据源或大规模指标库 |
| OpenBB | Provider 字段到标准模型的验证映射 | 不构建通用平台或插件生态 |
| Qlib | Point-in-Time 防止后见数据泄漏 | 不引入训练框架或其存储格式 |
| OpenLineage | Run 与输入/输出数据集的血缘分离 | 不接入外部 lineage 服务 |
| Great Expectations / Pandera | 将结构和业务合同变为可执行门禁 | 不新增运行时依赖，以 JSON + pytest 最小实现 |
| 北极星登记的开源项目 | 研究组织、筛选与呈现启发 | 不复制交易信号、评分、数据许可或自动交易功能 |

裁剪目标是个人、本地、审计优先的研究工具，不是通用金融数据平台。

## 6. 六指标解释合同

| Metric | 公式 / 单位 | 当前解释结论 | 单独评分 |
|---|---|---|---|
| `revenue_yoy` | `current revenue / prior revenue - 1` / ratio | 描述收入变化；不能拆分价格、销量、汇率或并购 | 否 |
| `net_profit_attributable_to_parent_yoy` | `current attributable NP / prior - 1` / ratio | 描述归母利润变化；不能识别扣非和一次性项目 | 否 |
| `operating_cash_flow_yoy` | `current OCF / prior OCF - 1` / ratio | 描述经营现金流变化；需解释营运资本与周期 | 否 |
| `operating_cash_flow_to_attributable_net_profit` | `OCF / attributable NP` / ratio | 是现金/利润量级线索；不能机械以 1 判断好坏 | 否 |
| `cash_based_free_cash_flow_proxy` | `OCF - cash paid for fixed assets` / 万元 | 狭义现金余量代理；不是完整 FCFF 或 FCFE | 否 |
| `cash_paid_for_fixed_assets_to_revenue` | `cash paid / revenue` / ratio | 描述相对量级；不是完整资本开支强度 | 否 |

六项均要求 PIT、多年趋势和行业/周期背景，均可能受重列影响，均为可信的描述性证据，`score_eligible=false`。详细合同逐项记录了输入事实、研究问题、不能回答的问题、前提、正负含义、周期限制、比较需求、信任状态和引用。

## 7. 事实覆盖路线图

路线图完整承接 Stage 2B-B 缺口：扣非净利润、毛利率和一般净利率、非经常性损益、ROE / ROA / ROIC、财务安全、分红与回购、估值。

已登记五类事实模块：

- 盈利质量：扣非归母净利润、营业成本、毛利润、营业利润、非经常性损益；
- 资本回报：归母权益、总资产、有息债务、现金、NOPAT 或诚实替代项、平均余额；
- 财务安全：总负债、长短期借款、应付债券、租赁负债、利息费用和现金等价物；
- 分红兑现：现金分红、回购、总股本和实施日期；
- 估值：PIT 股价、市值、PE/PB/PS、股息率和历史分位。

每项都记录研究问题、公式、官方来源、instant/duration、平均余额、附注、重列风险、获取难度、实现复杂度、增量价值和周期适用性。本阶段没有获取这些事实。

## 8. 下一事实阶段推荐

推荐 **盈利质量补充的最小官方事实覆盖**：先覆盖扣非归母净利润、营业成本、营业利润和非经常性损益证据。

透明矩阵只使用 high / medium / low，没有数字总分或加权排名。该方案对北极星和研究结论贡献 high，官方可得性与现有基础设施复用 high，公式争议 low，手工工作量 medium。它以较少事实直接改善归母利润同比无法辨别一次性项目和利润率的盲点，适合先做单年度双官方最小验收。

推荐仅表示下一阶段允许立项，不在本阶段执行。ROE/ROA 紧随其后；ROIC 在 NOPAT 和投入资本口径明确前不得抢跑。

## 9. 评分准入

`docs/value_scoring_readiness_gates.md` 完整登记十二项门禁。当前只有部分基础设施和政策边界具备，其余仍缺少事实覆盖、周期规则、同行/历史基准、阈值证据、敏感性分析、风险否决合同和人工评审。

结论固定为：

```text
Scoring readiness: BLOCKED
```

## 10. 北极星防失焦十问

| 问题 | 结论 |
|---|---|
| 是否服务于示范公司的可追溯价值研究？ | 是；把已有事实和指标限制在可解释边界内 |
| 是否区分好企业、好价格和好投资？ | 是；三者分别定义，不互相替代 |
| 是否保持事实、指标、评价、评分、投资结论分层？ | 是；主文档和测试冻结五层边界 |
| 是否把缺失当作零？ | 否；缺失、不可比和不适用均显式保留 |
| 是否保持 PIT 和重列版本？ | 是；六项指标均声明 PIT 与 restatement 属性 |
| 是否为周期企业保留专门解释？ | 是；要求完整周期、价格/经营拆分和情景解释 |
| 是否使用最小透明实现？ | 是；仅 Markdown、JSON 和 pytest，无新服务或依赖 |
| 是否新增基础设施而偏离研究价值？ | 否；没有新 Schema、runner、数据库或框架 |
| 是否提前评分、估值或输出建议？ | 否；评分 BLOCKED，估值仍为事实缺口 |
| 是否给出一个可停下的下一步？ | 是；仅推荐盈利质量最小事实阶段，未执行 |

项目北极星漂移：`FALSE`。

## 11. 冻结与不变性

| 对象 | 验收证据 |
|---|---|
| 75 Fact IDs | 集合 SHA-256 `7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1` 不变 |
| 38 Metric Result IDs | 集合 SHA-256 `730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa` 不变 |
| Stage 2A 原 26 Result IDs | 集合 SHA-256 `671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf` 不变 |
| Stage 2B-B 正式报告 | Git blob `1e6ae316c8a79b0a48deaa2b2316b17f559f543e` 不变 |
| `data/research.duckdb` | SHA-256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` 不变 |
| stash | `stash@{0}` 保持原条目，未操作 |
| 产物 | 未下载年报，未生成或提交 PDF、PNG、DuckDB、output 产物 |

方法论回归测试还冻结两组 metric definitions、models、engine、Concept Registry、Stage 2A/2B-A/2B-B runners 和三份正式报告的 Git blob。

## 12. 门禁结果

使用项目固定 Ruff 0.13.2 环境：

```text
python -m ruff check src tests
All checks passed!

python -m compileall -q src tests
PASS

pytest -q tests/test_value_evaluation_methodology.py
9 passed

pytest -q
612 passed, 2 warnings

git diff --check
PASS
```

两条 warning 来自既有 `tests/test_quality.py` 对无法推断日期格式的预期异常路径，不是本阶段回归。

## 13. 提交

第一独立提交：

- `a70a82c` — `docs: add value evaluation methodology baseline`

正式报告和工作记录定稿由第二独立提交承载。未 merge main，未创建 Tag / Release，未 force push。

## 14. 最终状态

```text
M2 Stage 2C-A:
PASS

Value evaluation methodology:
TRUSTED

Recommended fact extension:
ALLOWED

Recommended next stage:
minimal official profitability-quality fact coverage

Scoring readiness:
BLOCKED / STILL NOT YET

North-star drift:
FALSE
```
