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

## 合同测试

- Runner 与合同测试：`107 passed in 6.12s`
- Ruff 0.13.2（本次生产文件与测试）：通过
- 已覆盖旧 bundle 缺省范围、新关系正例、范围错配、两份 audited statements、相同哈希、新旧关系和 manifest 规范化。

## 2021 官方文档

### company_official

- 标题：`中国石油天然气股份有限公司截至2021年12月31日止年度财务报表及审计报告`
- document_scope：`audited_financial_statements`
- Landing：`https://www.petrochina.com.cn/petrochina/gsgg/xwgg_list_42.shtml`
- PDF：`https://www.petrochina.com.cn/petrochina/gsgg/202203/b39500c66f3b40f5b1a97c5b37f1f75f/files/f066f8223a454855ae08d97d1f3bf0cb.pdf`
- 公告日期：`2022-03-31`
- retrieved_at：`2026-07-30T08:20:08.701+08:00`
- SHA-256：`badab8f25c48184e16469f4ac542ff5ac5087b2a376ae3c95cd31b3793cd7a99`
- 大小：`4,714,421` bytes
- 页数：`95`

### exchange_official

- 标题：`中国石油天然气股份有限公司2021年度报告`
- document_scope：`full_annual_report`
- Landing：`https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857`
- 原 PDF：`https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf`
- Final PDF：`https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf`
- 公告日期：`2022-04-01`
- retrieved_at：`2026-07-30T08:26:28.000+08:00`
- SHA-256：`939de04e6502dc61be1a1fd3b12a4b9faaa0eb52e3996134810581391a93841f`
- 大小：`5,115,948` bytes
- 页数：`282`

文档关系为 `audited_financial_statements_subset_of_full_annual_report`。两份文件范围和字节不同，但包含同一套 CAS 合并财务报表；不是独立编制的数据来源。

## 双遍目视核对

- 第一遍：公司官网审计财务报表，利润表 PDF page 10 / printed page 8；现金流量表 PDF page 11 / printed page 9。
- 第二遍：上交所完整年报，利润表 PDF page 114 / printed page 112；现金流量表 PDF page 115 / printed page 113。
- 两份文件的表名、行标签、`2021年度合并` 列和人民币百万元单位一致。

| Concept | 原始值（人民币百万元） | 规范化值（万元） |
|---|---:|---:|
| revenue | 2,614,349 | 261,434,900 |
| net_profit_attributable_to_parent | 92,161 | 9,216,100 |
| operating_cash_flow | 341,469 | 34,146,900 |

- 审计机构：普华永道中天会计师事务所（特殊普通合伙）。
- 审计报告号：普华永道中天审字（2022）第10001号。
- 审计意见：无保留意见。
- 公司审计报告起始：PDF page 3 / audit printed page 1。
- 上交所年报审计报告起始：PDF page 107 / printed page 105。
- 2022 年报的 2021 比较列三值与 2021 original facts 一致；未使用该比较列建立事实或覆盖 original。

## 真实离线验收

- run_id：`annual_official_601857_SH_2021_20260730_083333_624931`
- status：passed
- transaction committed：true
- source hash validation：passed
- Acceptance contract：`annual_official_facts_v1_1`
- Bundle Schema / Fact Schema：`1.0 / 2.1`
- company originals / exchange originals：`3 / 3`
- matched / reconciled：`3 / 3`
- financial_facts：`9`
- PIT before / on availability：`0 / 3`
- Audit / Lineage：`9 / 9`
- latest_available_at：`2022-04-01`
- Manifest scopes：`audited_financial_statements / full_annual_report`
- Manifest independent content sources：`false`

## Canonical Fact ID

公司原始：

- revenue：`dcccf0526fd2d52cf0c791615035d62938c6d68bf8b563788ef661bae5048850`
- net profit attributable：`65c656bcac5d2efc9d5e79e30891e7daeb1d6c0c7ab952890db33b665a60b1b9`
- operating cash flow：`bff27442c19c115839326e362696bda86003bb00f81ada5740d6c8dc44fe96f1`

上交所原始：

- revenue：`3a337163978075c730e517bfee5f4faad8a4ddcbd7ea578b5e3187bfc82b2e71`
- net profit attributable：`38ec7019d25dededf58d5dc046f346ec91e1441a2b78b6b5c398a25f0201aa1a`
- operating cash flow：`5429fd7e648f4d3d06217e57e1e8344baab06ab7328fd41595a029992501b5bc`

Reconciled：

- revenue：`1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6`
- net profit attributable：`00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4`
- operating cash flow：`932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2`

三个 reconciliation output 的 parent_fact_ids 均严格等于各自 company/exchange 原始 fact_id。

## 注册证据测试

- Runner、2021—2025 注册 bundle targeted pytest：`160 passed in 5.26s`
- 2021 新增测试 Ruff 0.13.2：通过

## 全量门禁

- Ruff：`py -3.13 -m ruff check src tests`，版本 `0.13.2`，通过。
- compileall：`python -m compileall -q src tests`，通过。
- import：`ashare_research` 与 `official_fact_acceptance` 导入通过，合同版本为 `annual_official_facts_v1_1`。
- 全量 pytest：`482 passed, 2 warnings in 38.66s`。
- `git diff --check`：通过。
- 2022—2025 bundle 内容与基线逐字节 JSON 等价，Git blob 保持：
  - 2022：`7076195f3532ead9f0278f97691fe552fdb2ff54`
  - 2023：`6612148ea91b2004605b98e0c8fe799a4d2686ea`
  - 2024：`03a2ec2813c31676aebed20e4df50042f42f140b`
  - 2025：`0ababb5262e6cbf1646e165ccfb3e7bfe2769670`
- 2022—2025 每年六个 original canonical Fact ID 与基线完全一致。
- 默认 `data/research.duckdb` 结束 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`，与启动值一致。
- PDF、渲染 PNG、DuckDB 和 runner output 均未进入 Git；临时渲染目录和浏览器缓存已清理。
- `stash@{0}` 未读取、未应用、未弹出。

## 提交边界

- `b50dcfb fix: support scoped official document evidence`
  - runner 合同、合同测试、工作记录初稿。
- `add075e test: register PetroChina 2021 official fact evidence`
  - 2021 bundle、注册证据测试、实际证据工作记录。
- 正式报告与最终工作记录在第三个独立 docs 提交中定稿。
