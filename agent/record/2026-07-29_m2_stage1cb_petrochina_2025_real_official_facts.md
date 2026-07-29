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

- 工具 commit：待实际提交
- 证据 commit：待实际提交
- Acceptance run_id：待实际运行
- 测试结果：待实际运行
- 最终状态：不得在真实 Acceptance Run 与全部门禁通过前填写 Pass
