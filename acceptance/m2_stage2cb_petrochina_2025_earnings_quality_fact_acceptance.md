# M2 Stage 2C-B：中国石油 2025 盈利质量最小官方事实验收

日期：2026-07-30

分支：`feat/m2-value-assessment-mvp`

起始提交：`9d73a41d93b6dcf625a718c64f686b8e760c0f11`

真实 run ID：`earnings_quality_601857_SH_2025_20260730_145900`

## 1. 结论

```text
M2 Stage 2C-B: PASS
2025 earnings-quality official facts: TRUSTED
2021—2025 earnings-quality expansion: ALLOWED
New earnings-quality metrics: NOT YET
Scoring: STILL NOT YET
```

本阶段仅新增中国石油 2025 年三个盈利质量 Concept 的双官方 raw v1 和 Rule 003 reconciled v1，共九条事实。未扩展 2021—2024，未创建模糊 `non_recurring_gain_loss` Fact，未计算新指标、利润率、ROE、估值或评分。

## 2. 三个 Concept 的语义

| Concept | 中文语义 | 证据边界 |
|---|---|---|
| `net_profit_excluding_non_recurring` | 归属于母公司股东的扣除非经常性损益的净利润 | A 股年度报告直接披露的官方指标，不是经审计合并利润表标准行项目 |
| `operating_cost` | 营业成本 | 经审计合并利润表“减：营业成本”，按成本金额正值登记 |
| `operating_profit` | 营业利润 | 经审计合并利润表标准行；不以“经营利润”或分部利润替代 |

Concept Registry 原已注册上述三项。本阶段没有修改 Concept、Fact Schema 2.1 或 Metric Schema 1.0。

## 3. 两个官方来源与缓存

| 来源 | source_id | 公告日 | URL | SHA-256 | 大小 / 页数 |
|---|---|---|---|---|---|
| company_official | `company_ir:601857.SH:2025:annual:zh-cn` | 2026-03-29 | `https://www.petrochina.com.cn/petrochina/rdxx/202603/77efc25cfdc14bad83525f05cf092454/files/e3eab58b4de94a8aa43abf7ec9a40123.pdf` | `0eba96bd4e815187e7b64645f523f2b5d363ca3fea8168a63ec930f624715f8d` | 10,608,680 bytes / 273 |
| exchange_official | `sse:601857.SH:2025:annual:zh-cn` | 2026-03-30 | `https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-03-30/601857_20260330_6PPK.pdf` | `840b15aa4dc38745a6b86a3656063e6a73081ce87407acb0ca93554f4e836e65` | 9,416,509 bytes / 273 |

两份缓存均从 `D:\量化分析-cache\official-pdfs\<sha256>.pdf` 读取，重新验证 `%PDF-` 文件头、登记大小和 SHA-256。没有联网：

```text
cache_hit = 2
cache_miss = 0
downloaded = 0
hash_verified = 2
```

两条路径承载同一正式年报内容，不是两个独立编制的数据来源；PDF 字节不同。

## 4. 逐来源视觉核验

两份 PDF 均分别渲染并检查相关页面，结果一致。

| Concept | PDF / 印刷页 | 表名 | 完整标签 | 2025 列 | 原始显示 | 原始登记 | 单位 | 规范化万元 |
|---|---|---|---|---|---:|---:|---|---:|
| `net_profit_excluding_non_recurring` | 8 / 6 | 按中国企业会计准则编制的主要财务数据：主要会计数据及财务指标 | 归属于母公司股东的扣除非经常性损益的净利润 | 2025年 | 161,671 | 161,671 | 人民币百万元 | 16,167,100 |
| `operating_cost` | 109 / 107 | 2025年度合并及公司利润表 | 减：营业成本 | 2025年度合并 | (2,246,121) | 2,246,121 | 人民币百万元 | 224,612,100 |
| `operating_profit` | 109 / 107 | 2025年度合并及公司利润表 | 营业利润 | 2025年度合并 | 234,579 | 234,579 | 人民币百万元 | 23,457,900 |

营业成本以括号表示利润表扣减项目；本项目按“成本金额正值”登记，与方法论路线图中 `revenue - operating_cost` 的透明语义一致。显示符号和登记约定均保留在 evidence。

## 5. 非经常性损益桥

报告 PDF 9 / 印刷 7 的主要财务数据部分，以及 PDF 191 / 印刷 189 的管理层补充资料，均披露同一桥接表，单位为人民币百万元：

| 桥接项目 | 金额 |
|---|---:|
| 非流动性资产处置损益 | -8,632 |
| 计入当期损益的政府补助 | 1,687 |
| 与正常经营业务无关的金融资产和金融负债产生的损益 | 1,514 |
| 应收款项减值准备转回 | 55 |
| 其他营业外收入和支出 | -60 |
| 其他符合非经常性损益定义的损益项目 | 385 |
| 项目小计 | -5,051 |
| 所得税影响额 | 766 |
| 少数股东损益影响额 | -84 |
| 报告最终净影响 | -4,369 |

精确勾稽：

```text
157,302 - 161,671 = -4,369
-5,051 + 766 - 84 = -4,369
```

sign convention：正数增加归母利润，括号表示负数，税与少数股东影响按报告显示符号相加。

```text
bridge_status = reconciled
exact_tie_out = true
```

桥只作为证据，不是 `financial_facts` 输入，也没有创建模糊非经常性损益 Fact。

## 6. Rule 003

新增独立规则：

```text
rule_id = RECON_OFFICIAL_NUMERIC_003
version = 1
supported concepts:
  - net_profit_excluding_non_recurring
  - operating_cost
  - operating_profit
```

Rule 003 复用既有 `NumericReconciliationRule`、Decimal 单位换算、安全整数和精确相等逻辑。无容差、平均或来源优先级。Rule 001 / 002 常量和支持范围未修改。

三组结果均为：

```text
company_official verified/ineligible
+ exchange_official verified/ineligible
→ exact match
→ reconciled_derived eligible
```

## 7. Fact ID 与 reconciliation

| Concept | Company raw Fact ID | Exchange raw Fact ID | Reconciled Fact ID | 结果 |
|---|---|---|---|---|
| `net_profit_excluding_non_recurring` | `466e5df9f080d6ab4a04027accaaa6d526408347083cdf094270360ef4fd22a6` | `501c9be93d1adf72b20f51f67629be409804bd66bd0e300dff888ff35811ec81` | `06f703c7e956f3d78e341be57478b9a9c1c67214f1da942645f77d8f41dc8077` | matched |
| `operating_cost` | `5e9d6710fbd703ac4d2e405fbbd108569cbed3ee0f368aca8933aa57bd4f52f0` | `e9d0c5718d11592a955a8a411ef089f6be2c514c2a7cc5cf8ff9ece419dc463c` | `be615c237d0c328a531cc420fe1e7c9a96d7b748d07539ea3540c704f8f896a5` | matched |
| `operating_profit` | `af27da38cd6915d0b4bc7a2fb148b12b3335e7afa5058c6e8e01120d37d7f0c8` | `d6bac004cd48573d5609453e4bfc0d12a2a80bc82e171c32e0bf83a0611fbed5` | `2a98f29f9c371c6d52fed66efdcd9bb5a0bf6acec95752d699cfea135c3b469c` | matched |

全部 Fact ID 由 `FactIdentity` 生成；reconciled value、Fact ID 和三角色 lineage 均由 Rule 003 与 Service 生成，没有手写。

## 8. 版本与 PIT

九条新事实均为：

```text
fact_version = 1
restatement_version = original
supersedes_fact_id = ""
revision_review_status = not_yet_reviewable
```

较晚官方公告日为 2026-03-30：

- 2026-03-29：三个新 Concept 的 latest eligible PIT 为 0；
- 2026-03-30：三个 Rule 003 reconciled facts 可见；
- raw facts 始终不进入 eligible snapshot；
- final latest Fact PIT 从 upstream 20 增至 23。

按年度 Concept 数：

```text
2021 = 4
2022 = 4
2023 = 4
2024 = 4
2025 = 7
total = 23
```

PIT 验收通过 `AsOfQuery.get_latest_available()` 完成。

## 9. 固定计数

| 项目 | 结果 |
|---|---:|
| Contexts | 5 |
| Upstream facts | 75 |
| New company raw | 3 |
| New exchange raw | 3 |
| New reconciled | 3 |
| Financial facts | 84 |
| Raw / ineligible | 56 |
| Reconciled / eligible | 28 |
| Rule 003 matched | 3 |
| New version-chain links | 0 |
| Total version-chain links | 15 |
| Audit | 84 |
| Lineage | 84 |
| Final latest PIT | 23 |

Rule 003 lineage 为 9 行：每组 company input、exchange input、output 各一行。

## 10. 不变性

| 冻结对象 | 结果 |
|---|---|
| 原 75 Fact IDs | 集合 SHA-256 `7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1`，不变 |
| 原 38 Metric Result IDs | 集合 SHA-256 `730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`，不变且 runner 未访问 metric artifacts |
| Rule 001 | 57 lineage rows、rule ID/version、既有输出身份不变 |
| Rule 002 | 18 lineage rows、rule ID/version、既有输出身份不变 |
| Stage 2A / 2B-A / 2B-B | runners 与正式报告 Git blob 不变 |
| Stage 2C-A | 方法论文档、注册表、测试与正式报告 Git blob 不变 |
| 2025 annual bundle | Git blob `0ababb5262e6cbf1646e165ccfb3e7bfe2769670`，不变 |
| 默认数据库 | SHA-256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`，前后相同 |

本阶段没有运行或重算 Metric Result。

## 11. 离线与污染边界

正式 runner manifest：

```text
offline = true
network_access = false
pdf_access = false
cache_access = false
downloaded = 0
transaction_committed = true
```

PDF 仅在 evidence preparation 阶段从仓库外缓存读取；正式 runner 只读取 committed JSON。PDF、渲染 PNG、DuckDB 和 output 均未进入 Git。

## 12. 门禁

固定环境 Ruff 0.13.2：

```text
python -m ruff check src tests
All checks passed!

python -m compileall -q src tests
PASS

python -c "import ashare_research.reconciliation.engine;
import ashare_research.tools.official_earnings_quality_2025_acceptance"
PASS

required targeted regression
137 passed

pytest -q
642 passed, 2 warnings

git diff --check
PASS
```

两条 warning 来自既有日期格式异常路径测试，与本阶段无关。

## 13. 提交

前两条独立提交：

1. `98ab0a1` — `feat: add earnings quality reconciliation rule`
2. `a7fdb04` — `test: register PetroChina 2025 earnings quality evidence`

正式报告和工作记录定稿由第三条独立提交承载。未 merge main，未创建 Tag / Release，未 force push。

## 14. 最终状态

```text
M2 Stage 2C-B:
PASS

2025 earnings-quality official facts:
TRUSTED

2021—2025 earnings-quality expansion:
ALLOWED

New earnings-quality metrics:
NOT YET

Scoring:
STILL NOT YET

North-star drift:
FALSE
```
