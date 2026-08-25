# A股个股研究与市场机制验证平台

> 项目北极星文档 v2.0  
> 更新日期：2026-08-24  
> 目的：防止项目在开发过程中滑向“自动荐股”“短线预测”“参数挖掘”或“大而全量化平台”，始终围绕 **价值评估、机制验证与可证伪研究** 推进。  
> v2.0 在原北极星基础上吸收 M1–M3 的实际研究经验，并为 M4 增加 **Theory / Hypothesis Registry（理论 / 假设注册层）**。  
> 本文档是长期治理约束；阶段性的 commit、CI、缺口与验收事实仍以仓库 README、reports、acceptance 与 agent/record 中的 canonical evidence 为准。

---

# 0. 当前项目状态与本版决策

截至 v2.0：

- **Milestone 1：免费数据底座 — 已完成**
- **Milestone 2：价值评估 MVP — CONDITIONALLY CLOSED**
- **Milestone 3：机制验证 MVP — CONDITIONALLY CLOSED**
- M3 首个中国石油日线机制研究的最终 disposition：
  - development primary：正的受控异常表现 **NOT ESTABLISHED**
  - registered executable development robustness：已完成，未建立稳定正效应
  - holdout：已解封并消费，但因 frozen market coverage gate 未满足而 **INCONCLUSIVE**
  - holdout accepted primary execution count：`0`
  - 最终日线结论：`M3_DAILY_MECHANISM_NOT_ESTABLISHED`
- **Milestone 4 尚未启动。**
- 分钟级研究、指数贡献扩展、进一步 holdout recovery、经济显著性/可交易性研究、组合与实盘均未因本文件自动授权。

当前最优下一步：

> **M4 North-Star Preflight → M4-A 通用机制研究器 → M4-B Theory / Hypothesis Registry。**

M3 的 explicit evidence gaps 不自动成为 M4 TODO。任何延续都必须重新说明为什么服务于当前北极星目标。

---

# 1. 项目定位

本项目是一个面向个人研究、本地运行、免费数据优先的 A 股可解释研究平台。

平台当前主要回答两个问题：

1. **价值评估**  
   一家公司是否值得长期研究？当前价格处于什么估值环境？价值通过什么方式兑现？存在哪些不可忽视的风险？

2. **机制验证**  
   个股与大盘、行业、商品、汇率、市场风格、政策事件、财务事件或其他股票之间，是否存在稳定、可复现、可证伪的关系？

项目进一步允许：

3. **研究假设发现与整理**  
   从个人观察、经济金融理论、教材、学术论文、经典实证 anomaly 和官方制度机制中提取候选假设，并将其转化为可计算、可预注册、可反证的研究规格。

项目最终定位仍然是：

> **以免费或低成本可审计数据为基础，对 A 股个股形成可解释的价值档案，并用预注册、可复现的统计方法验证市场机制与候选规律。**

## 1.1 长期投资研究方向

项目允许把“最终希望获得投资研究优势”作为长期动机，但当前不把“盈利”写成软件功能承诺。

长期可以逐步研究：

- 统计关系是否存在；
- 关系是否具有经济显著性；
- 扣除交易成本、滑点和不可成交约束后是否仍有价值；
- 多个经过独立验证的规律能否形成稳定的风险调整收益。

但是：

> **统计显著 ≠ 可交易；历史可交易 ≠ 未来盈利；文献 anomaly ≠ A 股 alpha。**

在进入系统化 alpha、组合构建、仓位管理或实盘之前，必须单独修订北极星并重新授权。

---

# 2. 不做什么

为了避免失焦，当前明确不做：

- 自动买卖和券商下单；
- 明日涨跌预测；
- 精确目标价预测；
- 黑箱式“综合得分超过 80 就买入”；
- LLM 直接判断股票好坏；
- LLM 直接生成未经验证的交易信号；
- 新闻情绪自动荐股；
- 为追求回测收益自动穷举大量参数；
- “技术指标大全”式特征堆积；
- 全市场长期分钟级数据仓库；
- 深度学习价格预测作为当前主线；
- 多智能体自动交易平台；
- 加密货币、外汇、期权等非 A 股扩展；
- 为追求功能数量而引入复杂基础设施；
- 把已发表论文或教材结论直接当成本项目 evidence；
- 因 development 或 holdout 结果不理想而事后修改冻结研究规格；
- 为了得到可估计结果而静默降低数据质量门槛。

## 2.1 LLM 的允许角色

LLM 可以用于：

- 整理程序计算结果；
- 生成自然语言报告；
- 解释指标；
- 总结风险；
- 辅助把个人观察改写成可检验假设；
- 从教材、论文和公开研究中发现候选假设；
- 建立理论、文献、replication 与候选机制之间的索引；
- 检查报告是否前后矛盾；
- 审查研究设计是否存在未来数据泄漏、幸存者偏差、机械相关、p-hacking 等风险；
- 帮助设计反证与稳健性测试。

LLM 不可以：

- 把文献原结论自动升级为 A 股证据；
- 用语言模型记忆替代数据来源；
- 直接填写缺失关键数字；
- 为了得到“好看结果”挑选参数；
- 直接改变冻结的 research contract；
- 把 `missing_evidence` 改写成“没有风险”；
- 把 `NOT_ESTABLISHED` 改写成“证明不存在”。

所有关键数字、样本、结果、统计判定和 canonical status 必须由确定性程序或明确的人工治理合同生成。

---

# 3. 核心模块一：个股价值评估

## 3.1 模块目标

价值评估不是为了机械选股，而是为了：

1. 排除明显有问题的公司；
2. 找到值得持续研究的企业；
3. 判断当前价格是否有安全边际；
4. 判断低估是否存在兑现路径；
5. 记录原始投资逻辑并持续复核。

价值评估必须区分：

- 好企业；
- 好价格；
- 好投资。

三者不能混为一谈。

---

## 3.2 企业质量评估

回答：

> 这是不是一家值得长期研究的企业？

建议拆分为独立维度，而不是只给总分。

### 盈利质量

- 营收增长率；
- 扣非净利润增长率；
- 毛利率和净利率趋势；
- 非经常性损益占比；
- 盈利波动程度；
- 利润是否过度依赖补贴、资产处置或公允价值变动。

### 现金流质量

- 经营活动现金流净额；
- 经营现金流与净利润之比；
- 自由现金流；
- 资本开支强度；
- 分红是否由真实现金流支持。

参考指标：

```text
现金利润质量 = 经营活动现金流净额 / 净利润
```

不能机械认为小于 1 一定有问题，需要结合行业和企业发展阶段判断。

### 资本回报

- ROE；
- ROA；
- ROIC；
- 投入资本回报趋势；
- 高 ROE 是否由高杠杆形成；
- 留存利润是否创造新增价值。

关键规则：

> 如果严格证据合同不能唯一确定 ROIC 等指标，不得使用未经授权的 proxy、plug、残差分配或弱化口径来强行生成数值。

### 财务安全

- 资产负债率；
- 有息负债；
- 短期偿债压力；
- 利息覆盖倍数；
- 现金及等价物；
- 或有负债和担保。

### 经营稳定性

- 收入和利润的周期性；
- 客户集中度；
- 产品集中度；
- 应收账款增速；
- 存货增速；
- 应收、存货与营收是否匹配；
- 行业供需变化。

### 治理质量

- 控股股东质押；
- 关联交易；
- 频繁融资与股本稀释；
- 管理层增减持；
- 审计意见；
- 财务重述；
- 信息披露质量；
- 大股东是否侵占中小股东利益。

---

## 3.3 估值与安全边际

回答：

> 现在的价格是否值得承担相应风险？

建议分析：

- PE-TTM；
- PB；
- PS；
- 股息率；
- 自由现金流收益率；
- EV/EBITDA（适用行业）；
- 历史 3 年、5 年估值分位；
- 行业横向估值分位；
- 市值相近企业比较；
- 盈利下滑后的压力估值。

必须区分：

- **原始指标可计算**
- **历史位置可描述**
- **评分是否经过独立验证**

如果 scoring contract 的验证条件不可满足：

> 数值评分应保持 `null`，不得补 0，不得把权重自动转移到其他维度。

### 悲观情景

- 利润下降 20%；
- 利润下降 30%；
- 毛利率下降；
- 行业景气回落；
- 估值分位回到历史低位。

### 中性情景

- 盈利基本稳定；
- 分红维持；
- 估值保持历史中位。

### 乐观情景

- 盈利增长；
- 经营改善；
- 估值回归合理区间。

重要原则：

> 低 PE 不自动等于低估，特别是周期股利润顶部可能对应最低 PE。

---

## 3.4 价值兑现能力

回答：

> 即使公司被低估，市场为什么会在未来重新定价？

建议检查：

- 稳定或提高现金分红；
- 分红是否可持续；
- 回购是否注销；
- 控股股东增持；
- 减少低效资本开支；
- 处置低效资产；
- 盈利拐点；
- 行业供需改善；
- 国企改革；
- 管理层治理改善；
- 业务结构优化；
- 资产重组；
- 市场风格是否转向有利。

价值兑现必须与企业质量、估值分开。

---

## 3.5 风险否决项

部分问题不能通过其他高分抵消，应直接标红。

建议否决项包括：

- 审计非标准意见；
- 监管立案；
- 重大财务重述；
- 经营现金流长期显著低于净利润；
- 利润主要来自非经常性项目；
- 大股东高比例质押；
- 频繁、大额关联交易；
- 连续融资但资本回报低；
- 高额商誉且主营业务恶化；
- 分红依赖新增负债；
- 股本持续大幅稀释；
- 关键财务数据来源或公告日期缺失；
- 周期顶部仍按当期低 PE 判断便宜。

规则：

> `missing_evidence` 是证据缺口，不是“未发现风险”。

---

## 3.6 价值评估输出

推荐输出“价值档案”，包含：

- 企业质量；
- 估值吸引力；
- 价值兑现能力；
- 风险；
- canonical evidence；
- explicit gaps；
- 可追溯的指标来源。

结论必须避免：

- “建议买入”；
- “目标价 XX 元”；
- “上涨概率 XX%”；
- “综合分高所以值得买”。

---

# 4. 核心模块二：市场机制验证

## 4.1 模块目标

机制验证用于检验可明确表达的市场观察、经济理论或文献规律。

重点不是证明某种阴谋或交易主体意图，而是验证：

- 现象是否真实；
- 是否稳定；
- 是否具有时间顺序；
- 是否能被其他因素解释；
- 实际影响有多大；
- 在不同市场阶段是否仍成立；
- 哪些证据会推翻当前解释。

机制验证必须允许得到：

- `ESTABLISHED`
- `NOT_ESTABLISHED`
- `INCONCLUSIVE`

而不是要求所有研究最终都得到“存在规律”。

---

## 4.2 假设来源与 provenance

候选假设可以来自：

1. `USER_OBSERVATION` — 用户个人市场观察；
2. `TEXTBOOK_THEORY` — 经济学、金融学、行为金融、市场微观结构等教材理论；
3. `ACADEMIC_PAPER` — 学术论文与工作论文；
4. `KNOWN_ANOMALY` — 已知资产定价 anomaly / factor；
5. `OFFICIAL_MECHANISM` — 交易所、监管、指数编制、制度安排等官方机制；
6. `REPLICATION_EXTENSION` — 对已完成研究的预先定义、可解释扩展。

每条候选假设必须尽可能记录：

```text
hypothesis_id
source_type
source_title
authors_or_issuer
publication_or_version_date
citation_or_document_identity
theory
original_market
original_sample
expected_direction
candidate_signal
target_horizon
known_controls
known_alternative_explanations
known_replications
known_failures_or_decay
a_share_data_feasibility
free_data_feasibility
current_project_status
```

关键规则：

> 文献、教材和经典 anomaly 只提供 **research prior / hypothesis source**。  
> 它们不自动构成本项目 A 股 evidence。

---

## 4.3 假设必须可计算

不能写：

```text
中石油是不是用来护盘的？
```

应改写为：

```text
当剔除中国石油后的沪市收益率低于 -1% 时，
控制市场、原油和行业后，
中国石油是否存在显著正异常收益？
```

假设至少应包含：

- 目标股票或股票集合；
- 目标因素；
- 条件阈值或信号定义；
- 观察窗口；
- 控制变量；
- development 样本；
- holdout / OOS 设计；
- 预期方向；
- 反证条件；
- 数据频率；
- 统计方法；
- 数据质量门槛；
- 是否允许分钟级升级；
- 明确停止规则。

---

## 4.4 研究必须先冻结，再读取 outcome

机制研究原则：

> **先定义研究合同，再读取研究结果。**

冻结内容应视研究类型包含：

- 样本区间；
- universe；
- factor / condition；
- control；
- threshold；
- return definition；
- 缺失值处理；
- coverage gate；
- regression specification；
- bootstrap / resampling；
- multiple-testing correction；
- robustness registry；
- holdout policy；
- success / failure / inconclusive rule。

在冻结后的真实 outcome 被读取后：

- 不得因结果不显著而修改 threshold；
- 不得增加“刚好显著”的新 controls；
- 不得静默改数据源；
- 不得降低覆盖门；
- 不得把未注册的新测试写成 confirmatory evidence。

任何 post-outcome 变化必须被明确标记为：

> exploratory / new hypothesis / new stage

而不是回写原研究。

---

## 4.5 描述性统计

正式模型前可以计算：

- 全样本相关系数；
- 滚动相关性；
- 条件日表现；
- 上涨概率；
- 平均收益；
- 中位数收益；
- 成交量异常；
- 分年度结果；
- 不同市场阶段结果。

描述性结果不能替代控制模型，也不能自动升级为高等级证据。

---

## 4.6 排除机械相关

例如研究中国石油与上证指数时，不能直接忽略目标股本身包含在指数中的机械相关。

优先考虑：

- 剔除目标股票后的市场代理；
- PIT-aware 等权市场收益；
- 全 A 收益率中位数；
- 上涨家数比例；
- 剔除目标行业后的市场指标；
- 其他能够降低机械包含关系的代理。

市场 universe 必须考虑：

- 上市日期；
- 退市日期；
- 证券级身份；
- A/B 股等证券类型；
- 股票代码变化；
- t-1 membership；
- 幸存者偏差。

---

## 4.7 控制替代解释

研究某个异常现象时，应优先问：

> 它是否只是市场、行业、商品、风格、流动性或制度因素的普通结果？

可能的 controls 包括：

- 市场；
- 行业；
- 商品；
- 汇率；
- size；
- value；
- momentum；
- volatility；
- liquidity；
- dividend style；
- central-SOE style；
- market turnover；
- macro variables。

控制变量不能为了提高显著性无限增加。

---

## 4.8 条件检验、回归与稳健性

按照预注册合同逐级执行：

- primary specification；
- 已注册阈值变化；
- 样本敏感性；
- leave-period-out；
- 极端日期影响；
- Bootstrap；
- multiple-testing correction；
- alternative proxy（仅在 pre-outcome 注册且数据可信时）；
- OOS。

核心问题：

> 控制主要替代解释后，目标关系是否仍稳定存在？

### 多重检验

如果一次研究测试多个 threshold、factor、horizon 或信号：

- 必须记录测试族；
- 必须考虑 FDR / family-wise error 等校正；
- 不得只汇报最显著的一项。

---

## 4.9 Holdout / OOS 治理

Holdout 是反证工具，不是“第二次调参区”。

必须明确：

- 什么时候 sealed；
- 什么时候 unsealed；
- accepted primary execution count；
- 是否已经观察 primary statistic；
- post-unseal 是否发生技术修复；
- 是否仍能称为 pristine OOS。

如果 frozen data-quality gate 未满足：

> 正确状态可以是 `INCONCLUSIVE`。

不得为了得到回归结果而：

- 更换 provider；
- 降低 coverage；
- 删除缺失证券；
- 改 window；
- 插值关键 outcome；
- 修改 proxy。

如果这些变化确有研究价值，应重新注册为新研究。

---

## 4.10 分钟级研究

只有日线层面出现足够的、预先定义的升级理由后，才允许下载有限分钟数据。

研究可包括：

- 上午与下午；
- 14:00 以后；
- 尾盘成交量；
- 集合竞价；
- 多只权重股同步；
- 次日回吐；
- lead-lag。

时间顺序比普通相关性更接近机制判断，但仍不等于主体意图或因果。

分钟级不是 M3/M4 缺口的自动补偿手段。

---

## 4.11 指数贡献估算

可以估算：

```text
股票指数贡献 ≈ 估算权重 × 股票收益率
```

进一步计算：

- 正向贡献概率；
- 平均抵消市场跌幅比例；
- 最大单日抵消比例；
- 多只权重股共同贡献。

缺少精确历史权重时，应明确：

> 估算贡献，而非官方指数点位归因。

指数贡献是独立的 mechanical analysis，不得被用来证明主体意图。

---

## 4.12 证据分级

### 一级：未发现稳定关系

- 结果不显著；
- 不同样本期方向不一致；
- 主要由少数极端日期驱动。

### 二级：存在表面相关性

- 条件收益存在差异；
- 但可能由行业、商品或风格解释。

### 三级：控制主要因素后仍存在异常表现

- 控制变量后仍有统计证据；
- 预注册的多种检验下较稳定。

### 四级：存在稳定时间顺序和异常成交

- 市场先变化；
- 目标证券随后异常表现；
- 特定时段集中；
- 伴随异常成交量；
- 关系跨样本较稳定。

### 五级：存在资金主体证据

- 逐笔委托；
- 席位；
- 持仓；
- 资金来源；
- 官方或可靠公开证据。

重要限制：

> 如果 evidence level 的机器判定规则没有在 outcome 前冻结，不得事后根据结果创建规则并回填 canonical 数字等级。

---

# 5. Theory / Hypothesis Registry

## 5.1 目的

M4 新增一个轻量的理论 / 假设注册层，用于回答：

> 我们下一步值得研究什么，以及为什么值得研究？

它不是：

- alpha 自动生成器；
- 回测排名榜；
- 自动选股池；
- “论文显著所以 A 股也显著”的证据库。

它是：

> **Candidate Research Registry。**

---

## 5.2 候选来源

首期允许收录：

- 经典经济金融理论；
- 行为金融机制；
- 市场微观结构机制；
- 资产定价 anomaly；
- 公司金融与会计信号；
- 事件型规律；
- 用户真实观察。

优先来源：

1. 原始论文 / 作者公开稿；
2. 高质量 replication；
3. 教材；
4. 官方制度与数据方法文档；
5. 成熟公开研究项目。

---

## 5.3 Registry 状态

候选项至少区分：

```text
DISCOVERED
LITERATURE_REVIEWED
A_SHARE_FEASIBILITY_REVIEWED
NOT_TESTED
PRE_REGISTERED
DEVELOPMENT_EXECUTED
ROBUSTNESS_EXECUTED
OOS_EXECUTED
NOT_ESTABLISHED
ESTABLISHED
INCONCLUSIVE
DEFERRED
```

规则：

- `DISCOVERED` 不代表有效；
- `LITERATURE_REVIEWED` 不代表 A 股成立；
- `DEVELOPMENT_EXECUTED` 不代表 OOS 成立；
- `ESTABLISHED` 必须符合该研究预先冻结的 evidence rule；
- explicit gap 不自动成为 future task。

---

## 5.4 初始种子规模

M4 不应一开始收集 100 个 anomaly 并批量挖掘。

首期最多选择 3 个结构差异明显的代表性候选，用于验证通用框架的表达能力，例如：

1. 中期 momentum 类；
2. value / profitability 类；
3. behavioral / event 类（如 PEAD 类）。

初始目标不是证明它们能赚钱，而是验证：

> 通用研究器能否在不修改核心引擎的情况下表达不同研究类型。

任何真实 A 股 outcome 执行仍需单独授权。

---

# 6. 两个核心模块与 Registry 的关系

推荐流程：

```text
Theory / Literature / Observation
              ↓
       Candidate Registry
              ↓
       Feasibility Review
              ↓
     Frozen Research Contract
              ↓
        Mechanism Engine
              ↓
 Development → Robustness → OOS
              ↓
       Evidence Disposition
```

价值评估回答：

- 公司质量怎么样；
- 当前估值怎么样；
- 是否存在安全边际；
- 价值能否兑现；
- 长期风险是什么。

机制验证回答：

- 某种关系是否存在；
- 是否稳定；
- 是否能排除替代解释；
- 是否跨样本；
- 证据强度到什么程度。

Registry 回答：

- 值得验证的 hypothesis 从哪里来；
- 理论为什么认为它可能存在；
- 已知文献是否已经存在反证或衰减；
- A 股数据是否值得投入研究成本。

三者不能混用。

---

# 7. 免费优先的数据方案

## 7.1 数据源

### Baostock

用于：

- A 股历史日线；
- 交易日历；
- 股票基本信息；
- 部分财务数据；
- 少量按需分钟线。

### AKShare

用于：

- 指数；
- 行业；
- 板块；
- 商品；
- 期货；
- 原油；
- 汇率；
- 宏观；
- 估值补充；
- 公告和特色公开数据。

### 官方公开来源

用于核验：

- 上交所；
- 深交所；
- 巨潮资讯；
- 上市公司公告；
- 国家统计局；
- 中国人民银行；
- 期货交易所；
- 指数公司公开资料。

### 国际公开来源

当研究明确需要时，可在 contract 中授权：

- 官方商品 / 宏观数据；
- 公开研究数据库；
- 作者维护的可复现研究数据。

原则：

> 不把核心功能绑死在任何一个免费网页接口上。

但是：

> “可替换”不等于在 outcome 出现后可以随意换源。  
> 研究运行中的 source replacement 必须遵守 pre-outcome / post-outcome 治理。

---

## 7.2 本地存储

推荐：

```text
DuckDB + Parquet
```

DuckDB 保存：

- 股票基本信息；
- 数据任务；
- 数据血缘；
- 假设配置；
- candidate registry；
- value results；
- research results；
- report index；
- artifact identity。

Parquet 保存：

- 个股日线；
- 指数日线；
- 行业日线；
- 商品与宏观；
- 财务历史；
- 分钟行情；
- 因子结果。

---

# 8. 数据质量与研究完整性原则

免费数据的主要风险不是费用，而是：

- 稳定性；
- schema 变化；
- PIT；
- identity；
- survivorship；
- coverage；
- source revision。

每条或每批数据应尽可能记录：

```text
source_name
source_endpoint
fetched_at
source_version
schema_version
adjustment
raw_file_path
content_hash
quality_status
research_role
```

必须检查：

- 收盘价来源差异；
- 成交量单位；
- 前复权和不复权；
- 停牌日；
- 上市和退市日期；
- security identity 与 company identity；
- 股票代码变化；
- 交易日对齐；
- 财报公告日期；
- 股本变动；
- 分红实施日期；
- 期货换月方式；
- 接口字段变化；
- 历史数据是否被上游修订；
- universe membership 是否 PIT-aware；
- 缺失数据是否仍保留在 denominator；
- coverage gate 是否按冻结规则执行。

重要规则：

> 财务数据必须按照实际公告日期生效，不能按报告期直接回填。

重要规则：

> company code 不等于 security code。涉及 A/B/H、多证券类别、退市或代码变化时，必须在证券级 identity 上建立可审计映射。

重要规则：

> 不能为了让研究“可跑”而把真实 required missing 从 universe 或 coverage denominator 中静默删除。

---

# 9. 研究工程治理

M1–M3 的实际经验形成以下长期规则。

## 9.1 Fail closed

遇到以下情况应允许停止：

- source 不可信；
- schema 不明确；
- identity 冲突；
- PIT 无法证明；
- data coverage 未达到冻结门槛；
- research digest 不一致；
- required evidence 缺失。

停止是一种合法研究结果。

---

## 9.2 Pre-registration

正式 confirmatory research 必须先冻结：

- hypothesis；
- inputs；
- method；
- thresholds；
- success rule；
- robustness；
- OOS policy。

---

## 9.3 Artifact identity

重要研究输入、方法和输出应拥有稳定、路径无关的 identity：

- content hash；
- repository-relative digest；
- manifest；
- upstream refs。

禁止把绝对 checkout path 作为研究 identity 的有效组成部分。

---

## 9.4 Deterministic reproduction

正式研究核心应尽可能支持：

- A/B exact reproduction；
- clean clone；
- Windows / Ubuntu 一致性；
- fixed RNG / seed；
- frozen dependency contract。

---

## 9.5 Explicit evidence gaps

每个阶段应区分：

- 已建立事实；
- 未建立结论；
- 技术性 inconclusive；
- missing evidence；
- deferred future work。

`gap register` 不是自动 backlog。

---

## 9.6 Protected historical artifacts

已关闭阶段的 canonical artifact 默认不可重写。

修复应：

- 保留原失败证据；
- 新增 repair / supersession；
- 明确旧状态和新状态的关系。

不能为了让历史“看起来干净”而删除 blocker。

---

# 10. 代码结构建议

M4 之后建议逐步形成：

```text
src/
├── data/
│   ├── providers/
│   ├── normalize.py
│   ├── point_in_time.py
│   ├── quality_check.py
│   └── storage.py
│
├── value/
│   ├── profitability.py
│   ├── cashflow.py
│   ├── capital_return.py
│   ├── financial_safety.py
│   ├── governance.py
│   ├── valuation.py
│   ├── realization.py
│   ├── red_flags.py
│   └── report.py
│
├── mechanism/
│   ├── hypothesis.py
│   ├── contract.py
│   ├── engine.py
│   ├── market_proxy.py
│   ├── conditional_test.py
│   ├── event_study.py
│   ├── regression.py
│   ├── lead_lag.py
│   ├── contribution.py
│   ├── robustness.py
│   ├── holdout.py
│   └── evidence_grade.py
│
├── knowledge/
│   ├── registry.py
│   ├── provenance.py
│   └── feasibility.py
│
├── reports/
│   ├── renderer.py
│   └── templates/
│
└── web/
```

这只是方向，不要求为了目录整齐而重构已有稳定代码。

原则：

> M4 优先抽象 M3 已验证的最小公共接口，不进行无收益的大重构。

---

# 11. 可参考的成熟项目与研究设计

原则：组合参考，不直接 Fork 大型项目后删除功能。

## Open Source Asset Pricing（Chen & Zimmermann）

参考：

- 系统整理大量已发表 cross-sectional predictors；
- 将 predictor definition、数据与 replication 连接起来；
- 强调 original evidence 与 reproduction 的区别；
- 适合作为 Theory / Anomaly Registry 的 provenance 设计参考。

不直接采用：

- 不把美股 predictor 收益复制成 A 股结论；
- 不把其 predictor 全量导入后进行海量回测；
- 不把其原始样本显著性当成本项目 evidence。

## Alphalens

参考：

- factor / forward return 的标准化研究接口；
- grouped analysis；
- information coefficient；
- factor return；
- turnover / decay 等分析思想。

不直接采用：

- 当前不把它当生产策略引擎；
- 不因为 Alphalens 能生成 tear sheet 就自动进入 alpha/portfolio 层。

## Qlib

参考：

- config-driven research workflow；
- task / dataset / record 的模块化；
- 可替换的 workflow 组件；
- 研究任务与产物管理。

不直接采用：

- 第一阶段不接入自动 ML workflow；
- 不采用“批量模型 → 自动选最优回测”的方式替代研究合同；
- 不进入自动交易。

## Vibe-Trading

参考：

- 多数据源回退；
- DuckDB / Parquet；
- 假设注册；
- research task 结构；
- PIT 思想。

不直接采用：

- 自动交易；
- 多 Agent 交易；
- 非 A 股扩展。

## ZBS-Stock-Screener / daily_stock_analysis

继续只参考：

- 报告结构；
- 本地工作台；
- 数据源管理；
- 历史报告。

不采用：

- 黑箱荐股；
- AI 目标价；
- 每日买卖建议。

---

# 12. 推荐实施路线

## Milestone 0：项目骨架与研究契约

状态：

> 历史能力已由 M1–M3 实际工程吸收。

核心内容：

- 项目目录；
- 数据字段；
- 假设配置；
- value 输出；
- data lineage；
- testing baseline。

---

## Milestone 1：免费数据底座

状态：

> ✅ COMPLETED

完成：

- 股票列表；
- 交易日历；
- A 股日线；
- 指数日线；
- 原始数据留存；
- Parquet；
- DuckDB；
- 数据质量；
- provider abstraction；
- reproducibility baseline。

---

## Milestone 2：价值评估 MVP

状态：

> **CONDITIONALLY CLOSED**

已建立：

- PetroChina PIT value-profile vertical slice；
- 盈利 / 现金；
- ROE / ROA；
- 财务安全；
- 分红兑现；
- 风险 veto；
- 历史估值 descriptive evidence。

明确缺口：

- ROIC 在 strict evidence contract 下不可计算；
- PE / valuation numeric scoring 因 frozen validation 条件不可测试而保持 `null`；
- 不是生产评分、排名或交易信号。

---

## Milestone 3：机制验证 MVP

状态：

> **CONDITIONALLY CLOSED**

首个案例：

> 当剔除中国石油后的沪市明显下跌时，控制市场、原油与行业后，中国石油是否存在稳定正异常表现？

实际完成：

- preregistration；
- ex-target market proxy；
- PIT-aware universe；
- oil / industry controls；
- regression；
- bootstrap；
- registered robustness；
- holdout contract；
- post-unseal fail-closed recovery；
- security-level identity repair；
- explicit evidence-gap closeout。

最终结论：

> **M3_DAILY_MECHANISM_NOT_ESTABLISHED**

必须保留的边界：

- development primary 未建立稳定正效应；
- holdout 因 frozen coverage gate 未满足而 inconclusive；
- holdout accepted primary execution count = 0；
- 不能写成“证明护盘”；
- 也不能写成“holdout 已经证明不存在”。

M3 的价值之一是证明：

> 项目能够在结果不支持原观察时，保持冻结规则并接受 NOT_ESTABLISHED / INCONCLUSIVE。

---

## Milestone 4：通用研究器与假设注册层

状态：

> 🔲 NOT STARTED — 需先完成 M4 North-Star Preflight

### M4-A：Generic Mechanism Research Engine

目标：

把 M3 的单案例实现抽象为可配置研究框架。

示例：

```yaml
hypothesis_id: "example"
target: "601857.SH"

factor:
  type: "market_ex_target"

condition:
  operator: "<="
  threshold: -0.01

outcome:
  type: "abnormal_return"

controls:
  - "oil"
  - "industry"

development:
  start: "2015-01-01"
  end: "2022-12-31"

holdout:
  policy: "frozen"

robustness:
  bootstrap: true
```

通用引擎应能表达：

- target / universe；
- factor；
- condition；
- outcome；
- controls；
- development / holdout；
- data-quality gate；
- regression；
- bootstrap；
- robustness；
- evidence disposition。

### M4-A 验收

- 不修改核心引擎代码即可装载不同合法 hypothesis；
- 数据和方法缺失时 fail closed；
- 配置本身可 hash / version；
- research result 可追溯到 hypothesis + inputs + code；
- synthetic / test capsule 可以 cross-platform reproduction；
- 不因为“通用”而放宽 M3 建立的 PIT、coverage、identity、holdout 规则。

---

### M4-B：Theory / Hypothesis Registry

目标：

让项目能系统接收：

- 用户观察；
- 教材理论；
- 学术论文；
- anomaly；
- replication；
- 官方制度机制。

但候选项只能进入 `NOT_TESTED` 等状态，不自动执行真实研究。

M4-B 首期建议：

- registry schema；
- provenance；
- source / citation identity；
- A 股数据 feasibility；
- known replication / failure notes；
- 最多 3 个结构差异明显的示范 candidate。

### M4-B 验收

- registry 与 research outcome 完全分离；
- literature evidence 不自动变成 project evidence；
- candidate 可以明确保持 `NOT_TESTED`；
- 同一 hypothesis 的 source / version / theory 可追溯；
- 不实现 100-anomaly 自动扫描；
- 不按历史收益自动排序 candidate。

---

## Milestone 5：按需分钟研究

状态：

> 🔲 NOT AUTHORIZED

只对满足预先定义升级条件的日线机制研究：

- 5 分钟；
- 上午 / 下午；
- 尾盘；
- 集合竞价；
- volume；
- lead-lag；
- 次日回吐。

不下载全 A 长期分钟数据。

---

## Milestone 6：本地 Web 界面

状态：

> 🔲 NOT AUTHORIZED

页面建议：

1. 价值档案；
2. 估值与风险；
3. 因素关系；
4. 假设 / Theory Registry；
5. research contract；
6. 数据质量；
7. 历史报告。

界面不能先于研究语义稳定。

---

# 13. 未来研究方向：Economic Significance & Tradability

这不是 M4、M5、M6 的默认验收内容。

只有一个规律已经通过足够严格的：

```text
Development
→ Robustness
→ Independent OOS
```

之后，才允许另开 North-Star 授权研究：

- transaction cost；
- slippage；
- turnover；
- bid-ask；
- 涨跌停 / 停牌不可成交；
- capacity；
- factor exposure；
- beta；
- industry exposure；
- tail risk；
- Sharpe；
- Sortino；
- max drawdown；
- Calmar；
- strategy decay。

核心问题从：

> “规律存在吗？”

变为：

> “规律扣除现实摩擦后还有经济价值吗？”

这一阶段依然不等于自动交易。

---

# 14. 更远期方向：Portfolio / Alpha Research

只有多个 hypothesis 已独立通过前述研究，才可以评估：

- signal combination；
- factor redundancy；
- diversification；
- portfolio construction；
- risk budget；
- capacity；
- live paper evaluation。

正式进入这一阶段前：

> **必须重新修订北极星。**

不得在 M4 中通过“批量跑 anomaly”偷偷实现这一目标。

---

# 15. 防失焦原则

每增加一个功能、数据源、假设或研究前，必须回答：

1. 它服务于价值评估、机制验证还是 hypothesis discovery？
2. 它解决了什么明确研究问题？
3. 它是否能改变研究结论？
4. 数据能否免费或低成本稳定获得？
5. 结果能否解释和复现？
6. 是否会引入未来数据泄漏？
7. 是否存在幸存者偏差或 identity 问题？
8. 是否只是为了让页面看起来更复杂？
9. 是否把研究工具变成了荐股 / 参数挖掘工具？
10. 是否存在更简单的实现？
11. hypothesis 是在 outcome 之前定义的吗？
12. 是否因为看到了结果才增加本测试？
13. 是否存在 multiple testing / p-hacking 风险？
14. 缺口是真 blocker，还是只是“想把功能做全”？
15. 本阶段是否真的需要真实 outcome？
16. 如果结果是 NOT_ESTABLISHED，项目是否仍愿意接受？
17. 该功能是否会拖慢当前 milestone 的核心交付？

如果无法回答，应暂缓开发。

---

# 16. 项目核心原则

## 原则一：先研究，后展示

统计逻辑正确优先于界面漂亮。

## 原则二：先日线，后分钟

只有达到预定义升级条件后，才做分钟级验证。

## 原则三：先解释，后预测

当前首先研究关系为何存在以及是否稳定。

## 原则四：先分项，后总分

企业质量、估值、兑现和风险必须独立展示。

## 原则五：先排除替代解释

发现关系后，优先寻找它为何可能是错的。

## 原则六：免费数据可替换，但研究合同不可静默漂移

provider 可以被替换；已经读取 outcome 的研究不能为了结果而换源。

## 原则七：保存原始数据和研究版本

每次结果都应能追溯到：

- 数据来源；
- 下载时间；
- content hash；
- 数据版本；
- 参数；
- 代码版本；
- 样本期；
- 假设定义。

## 原则八：不把相关性写成因果

公开数据支持到什么程度，就写到什么程度。

## 原则九：先预注册，后看 outcome

Confirmatory research 必须冻结核心规格。

## 原则十：Fail closed 优于伪完整

没有可信数据时，宁可 `INCONCLUSIVE`，也不自动 fallback。

## 原则十一：文献是 hypothesis source，不是本地 evidence

经典规律必须重新在 A 股验证。

## 原则十二：NOT_ESTABLISHED 是有效研究结果

研究目的不是证明原观察正确。

## 原则十三：显著性不是盈利

必须把 statistical significance、economic significance 和 tradability 分开。

## 原则十四：少量高质量 hypothesis 优于 anomaly zoo 扫描

M4 不做大规模参数与因子挖掘。

## 原则十五：Explicit gap 不自动成为 TODO

是否继续取决于 North-Star review，而不是“有缺口就必须补”。

---

# 17. 一句话项目说明

> **一个使用免费数据、本地运行、面向 A 股的可解释研究平台：通过价值评估形成可追溯的企业档案，通过预注册机制研究检验市场关系，并把经济金融理论、论文与市场观察转化为可证伪的候选假设，而不是直接生成荐股或交易信号。**

---

# 18. 当前最优下一步

从已经合并并通过 CI 的 canonical main 开始：

1. **M4 North-Star Preflight**
   - 审查现有 M3 哪些组件值得抽象；
   - 明确哪些 PetroChina-specific 逻辑不能进入 generic core；
   - 冻结 M4-A / M4-B 的边界；
   - 不读取新的真实研究 outcome。

2. **M4-A Generic Mechanism Research Engine**
   - 配置 schema；
   - contract；
   - deterministic runner；
   - generic artifact identity；
   - synthetic / bounded test cases。

3. **M4-B Theory / Hypothesis Registry**
   - source provenance；
   - literature / theory metadata；
   - candidate status；
   - feasibility；
   - 最多 3 个代表性候选。

4. M4 完成后再进行一次 North-Star review：
   - 是否授权新的真实 A 股 hypothesis；
   - 是否有任何日线结果达到分钟级升级条件；
   - 是否值得设计 Economic Significance & Tradability 的独立 future milestone。

在 M4 核心能力完成前，不扩展：

- 自动交易；
- 100-anomaly 批量筛选；
- 自动 alpha 排名；
- portfolio optimization；
- 全市场分钟数据库；
- 深度学习预测；
- 大规模 Web UI。

---

# 19. v2.0 的核心变化摘要

相对于原北极星，v2.0：

1. 保留“价值评估 + 机制验证”双核心定位；
2. 把 M1–M3 的实际 fail-closed / preregistration / PIT / OOS 治理经验固化为长期规则；
3. 将教材、论文、经典 anomaly 正式纳入 **hypothesis source**；
4. 新增 **Theory / Hypothesis Registry**；
5. 将 M4 明确拆为：
   - M4-A 通用机制研究器；
   - M4-B 理论 / 假设注册层；
6. 明确不在 M4 做 anomaly zoo 自动挖掘；
7. 明确“文献规律 ≠ A 股证据”；
8. 明确“统计显著 ≠ 可交易 ≠ 盈利”；
9. 把 Economic Significance & Tradability、Portfolio / Alpha Research 放在未来独立授权边界；
10. 更新当前项目状态：M2、M3 均为条件关闭，下一步是 M4 North-Star Preflight。
