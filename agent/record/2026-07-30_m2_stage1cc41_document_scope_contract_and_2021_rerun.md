# M2 Stage 1C-C.4.1 工作记录：文档范围合同与 2021 重新验收

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`2d0fb1c23cc15a7594d5ba27aa55e50fb740e170`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- Ruff：项目环境固定为 `0.13.2`
- 默认 `data/research.duckdb` 启动 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`
- 2022—2025 bundle 起始 blob：
  - 2022：`7076195f3532ead9f0278f97691fe552fdb2ff54`
  - 2023：`6612148ea91b2004605b98e0c8fe799a4d2686ea`
  - 2024：`03a2ec2813c31676aebed20e4df50042f42f140b`
  - 2025：`0ababb5262e6cbf1646e165ccfb3e7bfe2769670`

## 合同修正范围

- Acceptance contract：`annual_official_facts_v1` → `annual_official_facts_v1_1`
- Bundle schema：保持 `1.0`
- Fact Schema：保持 `2.1`
- 文档范围：
  - `full_annual_report`
  - `audited_financial_statements`
- 旧 bundle 缺少 `document_scope` 时规范化为 `full_annual_report`。
- 新关系：`audited_financial_statements_subset_of_full_annual_report`
- `independent_content_sources`：保持 `false`
- 不修改 Reconciliation、Fact Schema、SourceTier、Concept、单位、容差、PIT 或 canonical Fact ID 规则。

## 待完成

- 两份 2021 合规官方 PDF 重新下载
- 双遍目视核对三个事实与审计意见
- 2021 bundle、注册证据测试与真实 runner
- 全量门禁、正式报告、分步提交和远程核验

## 合同测试

- Runner 与合同测试：`107 passed in 6.12s`
- Ruff 0.13.2（本次生产文件与测试）：通过
- 已覆盖旧 bundle 缺省范围、新关系正例、范围错配、两份 audited statements、相同哈希、新旧关系和 manifest 规范化。
