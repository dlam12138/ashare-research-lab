# M2 Stage 1C-C.2 工作记录：中国石油 2023 年官方事实

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`be8a15046075461e29b82dfc669d882d9ba9a7e9`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- 目标年度：2023（`2023-01-01` 至 `2023-12-31`）
- Concept：`revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`
- 来源要求：中国石油官网简体 A 股完整年报 + 上交所正式完整年报
- 目标：登记两条正式发布路径，人工双遍复核六条原始事实，并以既有 runner 完成 Reconciliation、PIT、Audit 与 Lineage 验收。
- 非目标：2022—2021、季度、其他公司、其他 Concept、自动发现、PDF 解析/OCR 入库、估值或荐股。
- 北极星对齐：确定性官方证据、公告日 PIT、事实身份和 lineage 可追溯。
- PDF、DuckDB、截图及 output 不进入 Git。
- 使用 run-scoped 隔离数据库，不修改默认 `data/research.duckdb`。
- 不修改 runner 合同、Fact Schema 或 Reconciliation 语义。

## 待确认

- 无

## 来源发现与人工复核

- 中国石油官网年度报告列表默认链接的 `842dad...pdf` 为繁体 H 股年度报告，已明确排除。
- 使用中国石油官网明确标注为《2023年度报告（A股）》的正式页面和简体完整 PDF；页面发布时间为 `2024-03-25`。
- 上交所 601857 定期报告接口返回完整年报和摘要两条记录；选择标题为《中国石油天然气股份有限公司2023年度报告》的完整年报，公告日期 `2024-03-26`，排除摘要。
- 公司 PDF retrieved_at：`2026-07-29T21:14:52.482+08:00`；上交所 PDF retrieved_at：`2026-07-29T21:15:59.268+08:00`。
- 两条正式路径下载的简体 A 股 PDF 均为 `12,437,650` bytes、`293` 页，SHA-256 均为 `b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692`。
- `document_relationship = byte_identical`；这是两个正式发布路径，不是独立编制的内容来源。
- 审计报告从 PDF page 107 / printed page 105 开始；普华永道中天按企业会计准则出具标准无保留意见。
- 第一遍从公司副本目视读取，第二遍重新打开上交所副本目视确认；两遍结果一致：
  - 营业收入：`3,011,012` 人民币百万元；
  - 归属于母公司股东的净利润：`161,144` 人民币百万元；
  - 经营活动产生的现金流量净额：`456,596` 人民币百万元。
- 利润表：PDF page 114 / printed page 112；现金流量表：PDF page 115 / printed page 113。
- 未使用 2022 比较列；未使用后续年度报告的 2023 比较列作为原始事实。
- 2024 年报因同一控制下企业合并重列 2023 比较数据：三项为 `3,012,812`、`161,414`、`456,847`；与 2023 原始披露不同，仅记录为后续重列证据，不覆盖本次 original facts。

## 真实离线运行

- run_id：`annual_official_601857_SH_2023_20260729_212055_855553`
- status：passed
- transaction committed：true
- source hash validation：passed
- 计数：1 context、9 facts、3 company、3 exchange、3 reconciled、9 lineage
- PIT：before 0，on availability 3；Audit 9
- latest_available_at：`2024-03-26`
- 默认 research DB 运行前后 SHA-256 均为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。

## 门禁状态

- Evidence commit：`709418d`
- Ruff toolchain commit：`07ff3a825f5a90d2db253ad4b54e05953cf2606b`
- Ruff：固定为 `0.13.2`；严格全仓检查 All checks passed，exit 0
- Registered bundle + annual runner tests：`122 passed in 5.24s`
- Reconciliation regression：`86 passed in 6.89s`
- Full pytest：`444 passed, 2 warnings in 42.53s`
- compileall：exit 0
- import：OK
- diff check：exit 0
- 原条件：Ruff 0.12.0 在起始 commit 已存在的 runner 两处和既有测试一处报告 `UP038`。
- 后续收口：Ruff 0.13.2 已删除该规则；未修改三处 `isinstance`，未添加 ignore/noqa。
- 2023 bundle、六个原始 fact_id、三个 reconciled fact_id、PIT、Audit 和 Lineage 均未改变。
- 2024、2025 bundle 和正式验收报告：未修改。
- PDF、DuckDB、output、截图和下载中间文件：均未进入 Git。
- `stash@{0}`：保持原状，未 pop。
- 最终状态：**M2 Stage 1C-C.2 Pass**
- 2022：允许进入 M2 Stage 1C-C.3。
