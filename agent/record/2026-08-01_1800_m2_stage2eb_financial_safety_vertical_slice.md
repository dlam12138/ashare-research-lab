# 工作记录：M2 Stage 2E-B 财务安全事实、透明指标与五年纵向切片

## 基本信息

- 日期：2026-08-01
- Agent：Codex
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`957ab91fd8c5a43495c9715661c2d89777ce170e`
- 任务来源：goal objective `M2 Stage 2E-B`
- 对应模块：价值评估 / 数据底座 / 工程治理

## 任务目标与范围

- 以本地已缓存的公司正式年报/交易所正式年报为双官方来源，建立 2021—2025 财务安全七项直接 Fact。
- 新增 Rule `RECON_OFFICIAL_NUMERIC_006`，不改变 Rule 001—005 语义。
- 新增四类财务安全 Metric（不实现 interest coverage），回放 PIT、重列、lineage 和五年趋势。
- 正式 runner 只读已登记 evidence JSON 与临时 run-scoped foundation；不访问网络、PDF、共享 cache 或默认 DB。
- 非目标：ROIC、interest coverage、评分、阈值、评级、投资建议、Schema/Identity 破坏、旧 201 Fact/77 Result 变化。

## 开始前状态与保护

- worktree clean；local/origin 均为 `957ab91fd8c5a43495c9715661c2d89777ce170e`。
- stash 保留既有 `protect pre-existing Stage 1B.4 record edit before Stage 1C`，未修改。
- 默认 DB 初始 SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。
- Stage 2D-F 基线：201 Fact、77 Result、12 definitions；既有 ROE/ROA、Rule 001—005 与受保护产物冻结。
- 已阅读 `agent/agent.md`、`agent/record/README.md`、北极星、financial safety v1 JSON/文档、Stage 2E-A/2D-B/2D-F 报告与 runner、Fact/Metric Engine/Identity/Repository/AsOfQuery、Rule 001—005 和 2021—2025 annual bundles。

## 官方证据检查

- 复用 `D:\量化分析-cache\official-pdfs\<sha256>.pdf`；五年 company/exchange 共 10 份 PDF 的 SHA-256、文件大小与页数均与 annual bundle 一致。
- 2021 company audited financial statements 为扫描版；已用 PDF 页面视觉核验资产负债表（PDF p8）、负债表续（p9）、现金流量表（p11）。
- 2021 exchange：负债表续 p113、现金流量表 p115；2022 exchange p112/p114；2023 p113/p115；2024 p114/p116；2025 p108/p110。
- 五项债务构成均为合并报表直接列示；不得将 total_liabilities 或 generic interest_bearing_debt 作为替代。
- 已发现并登记的后续比较列变化：FY2022 total_liabilities；FY2023 total_liabilities、current portion、lease liabilities。其余七项年度输入比较列保持不变；暂未发现双源冲突。

## 实施计划

1. 先提交本记录，再新增七项 evidence JSON 与四份 financial-safety restatement JSON。
2. 添加 current-portion Concept、Rule006、financial-safety definition registry、最小 role-binding Metric Engine 扩展和离线 vertical-slice runner。
3. 添加 Rule006/evidence/engine/integration/PIT/幂等/保护测试与五年事实性报告、验收文件。
4. 运行 targeted/full pytest、ruff、compileall、diff/污染/默认 DB/stash/受保护基线门禁。
5. 按三次提交逐个 push，更新本记录并做最终 local/origin/worktree 验证。

## 决策记录

- Rule006 作为 additive `NumericReconciliationRule`，复用既有精确 Decimal、万元归一化、双源比较、Fact ID 与 lineage 服务；不扩展 Rule001—005 的 supported concepts。
- 2021 company 扫描 PDF 的证据页按实际 PDF 页码记录；文字抽取不足时保留 visual verification 状态，不以 OCR 单独生成 Fact。
- 财务安全指标通过独立 registry 使用既有 `MetricDefinition` 字段；Metric Engine 增加可选 role map，旧 positional compute 接口保持兼容。
- 普通缺口按 evidence-backed missing 继续运行；只有双源冲突、口径不可区分、重复债务或治理破坏才停止。

## 实际操作与验证

待继续记录：新增文件、命令、测试、动态计数、报告状态、提交与 push 结果。

## 遗留问题

截至记录建立时，尚未写入本阶段 Fact/Metric/evidence 代码；动态结果计数尚未计算。

## 继续记录：已完成实施与离线验证

- 已新增七项直接概念证据合同、四份 FY2021—FY2024 后续比较列重列证据、Rule006、四项 `score_eligible=false` Metric 定义、可选 role-map Metric Engine 扩展与正式离线 runner。
- 已修正 FY2022 annual bundle/evidence SHA 记录为实际 64 位 SHA；runner 启动时冻结并验证 prior 77 Result ID 集合与 Result 语义摘要。
- runner 通过一次完整离线回放：Fact `11/318/212/106/57/318/318`（contexts/facts/raw/reconciled/fact_links/lineage/audit）；重列 `R=4`。
- 财务安全 Metric：`definitions=4/results=25/computed=25/insufficient=0/links=5/lineage=116/final_latest=20/final_computed=20`。
- 组合 Metric：`definitions=16/results=102/computed=98/insufficient=4/links=22/lineage=280/final_latest=80/final_computed=76`；PIT latest `0/16/32/48/64/80`，computed `0/12/28/44/60/76`，historical insufficient `0/4/4/4/4/4`。
- 已验证：四项安全指标的五年最新值、FY2022/FY2023 真实重列链、无假版本、2025 `not_yet_reviewable`、显式债务组件 lineage、零/负/缺失边界、无 interest coverage/ROIC/score 输出、重跑幂等。
- 已新增 `reports/petrochina_financial_safety_2021_2025.md`、`acceptance/m2_stage2eb_petrochina_financial_safety_vertical_slice.md` 与 `tests/test_official_financial_safety_vertical_slice.py`。
- 目前 targeted Stage 2E-B + capital-return/ROA tests 已通过；全量门禁、污染/哈希复核、三次提交与逐个 push 尚待完成。
