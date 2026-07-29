# M2 Stage 1C-C.1 工作记录：中国石油 2024 年官方事实

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`b32421451a58e785038bcc3bd070152263c2286d`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- 目标年度：2024（`2024-01-01` 至 `2024-12-31`）
- Concept：`revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`
- 来源要求：中国石油官网简体 A 股完整年报 + 上交所正式完整年报
- 目标：登记两条正式发布路径，人工双遍复核六条原始事实，并以既有 runner 完成 Reconciliation、PIT、Audit 与 Lineage 验收。
- 非目标：2023—2021、季度、其他公司、其他 Concept、自动发现、PDF 解析/OCR 入库、估值或荐股。
- 北极星对齐：确定性官方证据、公告日 PIT、事实身份和 lineage 可追溯。
- PDF、DuckDB、截图及 output 不进入 Git。
- 默认 `data/research.duckdb` 启动哈希：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`
- 使用 run-scoped 隔离数据库，不修改默认数据库。
- 不修改 runner 合同、Fact Schema 或 Reconciliation 语义。

## 待确认

- 最终结论、测试数量和提交哈希：待实际执行

## 来源发现与人工复核

- 中国石油官网 landing page 显示 `2024年度报告`，发布时间 `2025-03-30`。
- 官网报告列表默认链接的 `92270...pdf` 为繁体 H 股年度报告，已明确排除。
- 使用同一官网发布目录中的简体 A 股完整年度报告 `4ed338...pdf`；封面明确为简体、A 股代码 `601857`。
- 上交所 601857 定期报告接口返回完整年报和摘要两条记录；选择标题为《中国石油天然气股份有限公司2024年度报告》的完整年报，日期 `2025-03-31`，排除摘要。
- 两条正式路径下载的简体 A 股 PDF 均为 `11,167,845` bytes、`280` 页，SHA-256 均为 `15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba`。
- `document_relationship = byte_identical`；这是两个正式发布路径，不是独立编制的内容来源。
- 审计意见：毕马威华振按企业会计准则出具无保留意见。
- 第一遍从公司副本目视读取，第二遍重新打开上交所副本目视确认；两遍结果一致：
  - 营业收入：`2,937,981` 人民币百万元；
  - 归属于母公司股东的净利润：`164,676` 人民币百万元；
  - 经营活动产生的现金流量净额：`406,532` 人民币百万元。
- 利润表：PDF page 115 / printed page 113；现金流量表：PDF page 116 / printed page 114。
- 未使用 2023 比较列；未使用 2025 报告作为 2024 原始事实。

## 真实离线运行

- run_id：`annual_official_601857_SH_2024_20260729_205819_354458`
- status：passed
- transaction committed：true
- source hash validation：passed
- 计数：1 context、9 facts、3 company、3 exchange、3 reconciled、9 lineage
- PIT：before 0，on availability 3；Audit 9
- latest_available_at：`2025-03-31`
- 默认 research DB 运行后哈希与启动哈希一致。
