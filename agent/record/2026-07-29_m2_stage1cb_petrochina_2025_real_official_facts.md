# M2 Stage 1C-B 工作记录：真实中国石油 2025 年官方事实

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`9886eaace264115adf8ad19fa06281bc16b208fc`
- 启动时 worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- 目标报告：《中国石油天然气股份有限公司2025年年度报告》
- 官方路径：中国石油公司官网、上海证券交易所定期报告公告页
- 目标 Concept：`revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`
- 目标：以手工复核证据注册六条原始事实，离线运行三组双官方来源核验，验证 PIT、Audit 与 lineage。
- 非目标：批量抓取、通用 PDF 解析/OCR、2021—2024 扩展、季度事实、估值或荐股。
- 北极星对齐：确定性官方证据、公告日可用性、PIT 与来源追溯；不扩建通用基础设施。
- 本地 PDF 仅位于 Git 忽略目录，不得提交。
- 不读取或修改 `data/research.duckdb`；使用 run-scoped 隔离验收数据库。

## 证据复核

- 两份文件均为完整 A 股简体中文年度报告，均为 273 页。
- 审计报告位于 PDF 物理页 101—106；财务报表按中国企业会计准则编制。
- 合并利润表位于 PDF 物理页 109 / 印刷页 107。
- 合并现金流量表位于 PDF 物理页 110 / 印刷页 108。
- 两份 PDF 字节哈希不同，但上述关键页面的渲染内容和三项事实一致。

## 完成后填写

- 公司官网公告日：`2026-03-29`
- 上交所公告日：`2026-03-30`
- 公司 PDF SHA-256：`0eba96bd4e815187e7b64645f523f2b5d363ca3fea8168a63ec930f624715f8d`
- 上交所 PDF SHA-256：`840b15aa4dc38745a6b86a3656063e6a73081ce87407acb0ca93554f4e836e65`
- `document_relationship`：`same_report_different_bytes`
- 原始值（人民币百万元）：营业收入 `2,864,469`；归母净利润 `157,302`；经营活动现金流量净额 `412,510`
- 规范化值（万元）：`286,446,900`、`15,730,200`、`41,251,000`
- 工具 commit：`0b1f8679d75a87d615d03675403c5d72983d2f02`
- 证据 commit：由本记录与正式验收报告提交后记录在 Git 历史及最终回报
- Acceptance run_id：`stage1cb_20260729_200911_593537`
- Acceptance exit code：`0`
- Acceptance 计数：1 context、6 original、3 reconciled、9 facts、9 lineage
- PIT：`2026-03-29` 返回 0；`2026-03-30` 返回 3
- Audit：9
- 针对性门禁：`125 passed in 9.13s`
- 全量测试：`361 passed, 2 warnings in 40.58s`
- Ruff：exit 0
- compileall / import：exit 0 / OK
- diff check：exit 0
- 后续事项：两份 PDF 是同一报告的两个正式发布路径，不是独立编制的内容来源；不得将其表述为独立内容交叉验证。
- 最终状态：**Pass**
- 下一阶段：仅允许进入 `M2 Stage 1C-C`，先扩展 2021—2024 年度报告，不立即录入季度数据。
