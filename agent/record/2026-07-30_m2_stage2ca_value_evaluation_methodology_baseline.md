# M2 Stage 2C-A 工作记录：价值评价方法论基线

日期：2026-07-30

起点：`feat/m2-value-assessment-mvp@5c9f0f7e0ed2e0ae1db6c8dab6f1a7f89825f524`

状态：正式验收定稿

## 阶段边界

本阶段只建立方法论、六指标解释合同、机器可读注册表、事实覆盖路线图和评分准入门禁。未下载或核验公司年报，未新增 Financial Fact，未计算新 Metric，未更改 Fact / Metric Schema、公式、ID、runner 或默认数据库，也未设计分值、权重、阈值和投资建议。

## 基线审查

已审查：

- 项目北极星与李大霄投资思想增补稿；
- Stage 2A、2B-A、2B-B 正式报告；
- `metrics/definitions.py`、`cashflow_definitions.py`、`models.py`、`engine.py`；
- Concept Registry 与 Stage 2B-B gap inventory；
- 仓库内不存在 `AGENTS.md`。

确认六项定义：

1. `revenue_yoy = current revenue / prior revenue - 1`，ratio；
2. `net_profit_attributable_to_parent_yoy = current / prior - 1`，ratio；
3. `operating_cash_flow_yoy = current / prior - 1`，ratio；
4. `operating_cash_flow_to_attributable_net_profit = OCF / attributable net profit`，ratio；
5. `cash_based_free_cash_flow_proxy = OCF - cash paid for fixed assets`，万元；
6. `cash_paid_for_fixed_assets_to_revenue = cash paid for fixed assets / revenue`，ratio。

Fact Schema 2.1 与 Metric Schema 1.0 无需修改。缺口为扣非净利润、毛利率和一般净利率、非经常性损益、ROE / ROA / ROIC、财务安全、分红与回购、估值。

## 参考研究

核验财政部企业会计准则、证监会/上交所披露规则、IFRS IAS 7 和 CFA Institute 公开 FSA 材料。书籍仅登记 Penman、Damodaran、McKinsey、CFA 和本地李大霄增补稿的可靠书目信息与公开方法定位，不复制正文。

开源架构参考 FinanceToolkit、OpenBB、Qlib PIT、OpenLineage、Great Expectations 和 Pandera；只借鉴显式公式、标准模型、PIT、输入输出血缘和结构化门禁，不引入平台、服务、数据源或运行时依赖。

## 产物与决定

- 方法论：`ashare_value_evaluation_v1` / 1.0；
- 六项指标均为描述性证据，`score_eligible=false`；
- 推荐下一事实阶段：盈利质量最小事实覆盖；
- 评分准入：BLOCKED；
- 固定 ID 摘要：
  - 75 Fact IDs：`7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1`
  - Stage 2A 26 个既有 Metric Result IDs：`671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf`
  - Stage 2B-B 38 个 Metric Result IDs：`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`

## 第一提交

`a70a82c` — `docs: add value evaluation methodology baseline`

HTTPS push 的前三次尝试因本机到 `github.com:443` 连接超时而失败，随后一次连接被重置。SSH over 443 身份验证成功后，使用同一 GitHub 仓库的 SSH URL 推送成功；`origin` 配置未改变，远程分支已到 `a70a82c`。

## 门禁

第一提交前结果：

- Ruff 0.13.2：`All checks passed!`
- compileall：通过
- targeted pytest：`9 passed`
- `git diff --check`：通过

正式验收结果：

- Ruff 0.13.2：`All checks passed!`
- compileall：通过
- targeted pytest：`9 passed`
- full pytest：`612 passed, 2 warnings`
- `git diff --check`：通过
- 75 Fact ID 与 38 Metric Result ID 集合摘要不变
- Stage 2B-B 正式报告 blob：`1e6ae316c8a79b0a48deaa2b2316b17f559f543e`
- `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`
- 未下载公司年报，未生成新的 PDF、PNG、DuckDB 或 output 产物
- `stash@{0}` 未动

正式结论：M2 Stage 2C-A PASS；方法论 TRUSTED；推荐事实扩展 ALLOWED；评分 STILL NOT YET。
