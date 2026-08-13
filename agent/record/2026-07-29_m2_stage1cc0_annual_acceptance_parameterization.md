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

- 参数化代码 commit：`5f11df8b528500a5bbd528304153b179402e2305`
- 变更文件：
  - `src/ashare_research/tools/official_fact_acceptance.py`
  - `tests/test_official_fact_acceptance.py`
  - 本工作记录
- 删除的绑定：`EXPECTED_SYMBOL`、固定年度/起止日期/报告标题、`stage1cb_` run_id 和 `stage1cb` 目录。
- 年度合同：A 股 symbol 格式、1990—9999 整数年度、自然年度 duration、annual/CAS/consolidated/zh-CN。
- 不变合同：company + exchange、三个既有 Concept、人民币百万元到万元的 Decimal X100、Reconciliation v1、Fact Schema 2.1。
- run_id：`annual_official_{symbol_token}_{fiscal_year}_{timestamp}`
- 输出目录：`<output_root>/<symbol>/annual_official_facts/<fiscal_year>/<run_id>/`
- Manifest 版本区分：
  - `bundle_schema_version = 1.0`
  - `acceptance_contract = annual_official_facts_v1`
  - `fact_schema_version = 2.1`
- 2025 正式 bundle：保持原文件不变并通过兼容回归。
- 历史年度测试：仅使用测试内合成 bundle 与临时 PDF；未创建真实历史年度证据。
- 第二 symbol：仅合成合同测试；未创建公司配置或真实证据。
- 源码硬编码检查：`No matches found`。
- Targeted：`182 passed in 10.77s`。
- 全量 pytest：`418 passed, 2 warnings in 40.22s`。
- Ruff：`All checks passed!`，exit 0。
- compileall：exit 0。
- import：OK。
- `git diff --check`：exit 0。
- 主提交远程哈希：`5f11df8b528500a5bbd528304153b179402e2305`。
- 污染检查：无被跟踪的 `output/**`、PDF、DuckDB 或 `data/raw/official/**`。
- 正式 evidence fixture 仍只有已验收的 `601857.SH/2025_annual.json`。
- `stash@{0}`：保持原状，未 pop。
- 主提交推送后 worktree：clean。
- 后续风险：真实历史报告若使用不同单位或结构，必须在 C.1 停止并单独评估；C.0 未预扩展单位或解析框架。
- 最终状态：**M2 Stage 1C-C.0 Pass**。
- C.1：技术前置门禁已满足；在本次远程提交完成复审前不得启动真实报告工作。
