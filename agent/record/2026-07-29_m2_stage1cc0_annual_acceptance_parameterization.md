# M2 Stage 1C-C.0 工作记录：年度官方事实验收合同参数化

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`c16b7d0d2dbf61182ebb08d4c3a4bb53a1cc192f`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状

## 启动时硬编码

- `EXPECTED_SYMBOL = "601857.SH"`
- 固定 fiscal year、自然年度起止日期和报告标题
- 固定 `stage1cb_` run_id 前缀
- 固定 `stage1cb` 输出目录
- 测试要求第二 symbol 和上一年度失败

## 范围

- 目标：从 bundle 读取并交叉校验 symbol、company_name、fiscal_year、period_start、period_end；参数化 Context、Fact、run_id、输出目录和 Manifest。
- 非目标：真实历史报告、季度、IFRS、母公司口径、多语言、更多 Concept、更多来源、网络发现、PDF 解析或 OCR。
- 北极星对齐：复用最小年度验收链路，保持官方证据、公告日、PIT 与 lineage 可追溯，不复制年度专属代码。
- 不下载、搜索或录入真实历史年度报告。
- 不修改 Fact Schema 2.1。
- 不修改 Reconciliation Engine、规则或语义。
- 不修改 PDF 处理边界；runner 仍只校验人工登记的本地文件。

## 完成后填写

- 参数化代码 commit：待完成
- 记录定稿 commit：待完成
- 测试、静态检查与远程哈希：待实际执行后填写
- C.1：只有 C.0 全部门禁通过并完成远程复审后才允许
