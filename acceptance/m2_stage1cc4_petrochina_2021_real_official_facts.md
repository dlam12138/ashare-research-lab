# M2 Stage 1C-C.4 正式验收报告：中国石油 2021 年官方事实

## 结论

**Fail。**

在事实登记和 runner 执行前，`company_official` 文档合同已经失败：中国石油官网没有找到同时满足“2021 年、简体中文、A 股、完整年度报告”的正式文档。

## 已核验的中国石油官网文档

### 官网年度报告栏目中的完整报告

- 年度报告列表：<https://www.petrochina.com.cn/petrochina/ndbg/reportnd_list.shtml>
- 标题：`2021年年度报告`
- PDF：<https://www.petrochina.com.cn/petrochina/ndbg/202204/e5a5109dcf70405d8509e27040125ade/files/a2fdc43b19c547788f5149bf41840698.pdf>
- retrieved_at：`2026-07-29T22:25:37+08:00`
- SHA-256：`ea054145d5bcaf0f3fce9c3b0dab6927461cd231480e99b419bd646584244090`
- 大小：`4,582,111` bytes
- 页数：`276`
- 加密：否

通过 Poppler 分别渲染封面和 CAS 审计报告页并目视检查：

- 封面为 `中國石油天然氣股份有限公司 2021年度報告`；
- 封面同时列出香港、纽约和上海交易代码，不是明确的简体 A 股专版；
- 审计报告正文使用 `審計報告`、`中國`、`財務報表`、`準則`、`編製`、`為` 等繁体字。

该文档是完整年度报告，但属于本阶段明确禁止采用的繁体版本。

### 官网简体 A 股审计报告

- 公司公告栏目：<https://www.petrochina.com.cn/petrochina/gsgg/xwgg_list_42.shtml>
- 标题：`会计师审计报告（A股）`
- PDF：<https://www.petrochina.com.cn/petrochina/gsgg/202203/b39500c66f3b40f5b1a97c5b37f1f75f/files/f066f8223a454855ae08d97d1f3bf0cb.pdf>
- 公告日期：`2022-03-31`
- 页数：`95`

该文档是简体 A 股财务报表及审计报告，但不是完整年度报告，不能替代合同要求的公司官网简体 A 股完整年度报告。

## 上交所记录

- 601857 定期报告页：<https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857>
- 完整报告标题：`中国石油天然气股份有限公司2021 年度报告`
- 公告日期：`2022-04-01`
- 完整报告 PDF：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf>
- 同日年度报告摘要：`601857_20220401_5_sJDm4LL5.pdf`，已排除

上交所存在完整 A 股年度报告记录，但不能据此补足缺失的合规 `company_official` 完整年报，也不能把同一交易所文档同时登记为两个来源。

## 未执行项目

按照“文档语言、版本或来源不符合合同即停止”的规则，本轮没有：

- 读取或登记 `revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`；
- 使用后续年报中的 2021 比较列；
- 创建 `acceptance/fixtures/official_facts/601857.SH/2021_annual.json`；
- 新增 2021 注册证据测试；
- 运行 `python -m ashare_research.tools.official_fact_acceptance`；
- 生成 reconciled facts、PIT、Audit 或 Lineage；
- 修改 runner、Fact Schema、Reconciliation、单位规则或容差；
- 修改 2022—2025 已验收证据或 `data/research.duckdb`。

因此成功计数不适用，不应伪造为 `3/3`、`9` 或 `0/3`。

Ruff、compileall、import、targeted/full pytest 也未运行：本阶段在创建 bundle、生产代码或测试变更前已经按来源合同立即停止。`git diff --check` 通过；默认 `data/research.duckdb` 结束 SHA-256 仍为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。下载的 PDF、渲染 PNG、浏览器缓存和中间文件均已清理，未进入 Git。

## 阶段状态

```text
M2 Stage 1C-C.4: FAIL

blocker:
  company_official simplified-Chinese A-share full annual report not found

company full report:
  traditional Chinese -> excluded

company simplified A-share document:
  audited financial statements only -> not a full annual report

bundle created: false
runner executed: false
database written: false
Stage 1C-C.4 completed: false
multi-year integration allowed: false
```

若未来中国石油官网提供可核验的 2021 年简体 A 股完整年度报告正式路径，应从本阶段重新验收；在此之前不得用繁体版、审计报告、上交所副本或第三方转载绕过来源合同。

---

# M2 Stage 1C-C.4.1 复验定稿：文档范围合同修正

## 历史 Fail 的处理

上述 Stage 1C-C.4 初次 Fail 记录是当时合同与证据状态的真实历史，予以完整保留，不追溯改写为“从未失败”。

初次验收要求 company_official 与 exchange_official 都必须是简体 A 股完整年度报告。该要求把“来源文件的覆盖范围”错误地绑定到了“事实是否由官方文件直接证明”：中国石油官网发布的简体 A 股《截至2021年12月31日止年度财务报表及审计报告》直接包含同一套经审计 CAS 合并财务报表和全部三个目标事实，但仅因不是完整年报而被排除。

Stage 1C-C.4.1 将文档范围与事实证据分离：

- Acceptance contract 从 `annual_official_facts_v1` 升级为 `annual_official_facts_v1_1`；
- Bundle schema 保持 `1.0`，Fact Schema 保持 `2.1`；
- 新增 `full_annual_report` 和 `audited_financial_statements` 两种文档范围；
- 新增关系 `audited_financial_statements_subset_of_full_annual_report`；
- 2022—2025 未填写 `document_scope` 的旧 bundle 规范化为 `full_annual_report`；
- `independent_content_sources` 保持 `false`；
- Reconciliation、SourceTier、Concept、单位、容差、PIT 和 canonical Fact ID 规则均未修改。

## 修正后的双官方证据

### company_official：经审计财务报表及审计报告

- 标题：`中国石油天然气股份有限公司截至2021年12月31日止年度财务报表及审计报告`
- document_scope：`audited_financial_statements`
- 公告日期：`2022-03-31`
- retrieved_at：`2026-07-30T08:20:08.701+08:00`
- PDF：<https://www.petrochina.com.cn/petrochina/gsgg/202203/b39500c66f3b40f5b1a97c5b37f1f75f/files/f066f8223a454855ae08d97d1f3bf0cb.pdf>
- SHA-256：`badab8f25c48184e16469f4ac542ff5ac5087b2a376ae3c95cd31b3793cd7a99`
- 大小：`4,714,421` bytes
- 页数：`95`

### exchange_official：完整年度报告

- 标题：`中国石油天然气股份有限公司2021年度报告`
- document_scope：`full_annual_report`
- 公告日期：`2022-04-01`
- retrieved_at：`2026-07-30T08:26:28.000+08:00`
- SSE PDF：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf>
- Final PDF：<https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf>
- SHA-256：`939de04e6502dc61be1a1fd3b12a4b9faaa0eb52e3996134810581391a93841f`
- 大小：`5,115,948` bytes
- 页数：`282`

两份文件不是字节相同的副本，文档范围也不同；它们直接承载同一套经审计 CAS 合并财务报表，因此构成充分的 company_official 与 exchange_official 双官方直接事实证据，但不是两个独立编制的数据来源。

## 人工双遍核验

两份本地 PDF 均重新下载、校验哈希、渲染关键页并分别目视核对。未直接采用初次回答中的数字，也未使用后续年报的比较列建立或覆盖 original facts。

- 公司文档：利润表 PDF page 10 / printed page 8；现金流量表 PDF page 11 / printed page 9。
- 上交所年报：利润表 PDF page 114 / printed page 112；现金流量表 PDF page 115 / printed page 113。
- 表名：`2021年度合并及公司利润表`、`2021年度合并及公司现金流量表`。
- 取值列：`2021年度合并`。
- 原始单位：人民币百万元。

| Concept | 行标签 | 两份文档原始值（百万元） | 规范化值（万元） |
|---|---|---:|---:|
| revenue | 营业收入 | 2,614,349 | 261,434,900 |
| net_profit_attributable_to_parent | 归属于母公司股东的净利润 | 92,161 | 9,216,100 |
| operating_cash_flow | 经营活动产生的现金流量净额 | 341,469 | 34,146,900 |

审计机构为普华永道中天会计师事务所（特殊普通合伙），审计报告号为普华永道中天审字（2022）第10001号，审计意见为无保留意见。公司文档审计报告从 PDF page 3 / printed page 1 开始，上交所年报审计报告从 PDF page 107 / printed page 105 开始。

## 真实离线验收结果

- Bundle：`acceptance/fixtures/official_facts/601857.SH/2021_annual.json`
- run_id：`annual_official_601857_SH_2021_20260730_083333_624931`
- status：`passed`
- transaction committed：`true`
- source hash validation：`passed`
- latest_available_at：`2022-04-01`
- company originals / exchange originals：`3 / 3`
- matched / reconciled：`3 / 3`
- financial_facts：`9`
- PIT before / on availability：`0 / 3`
- Audit / Lineage：`9 / 9`
- Manifest document scopes：`audited_financial_statements / full_annual_report`
- Manifest independent content sources：`false`

### Canonical Fact ID

| Role | revenue | net_profit_attributable_to_parent | operating_cash_flow |
|---|---|---|---|
| company original | `dcccf0526fd2d52cf0c791615035d62938c6d68bf8b563788ef661bae5048850` | `65c656bcac5d2efc9d5e79e30891e7daeb1d6c0c7ab952890db33b665a60b1b9` | `bff27442c19c115839326e362696bda86003bb00f81ada5740d6c8dc44fe96f1` |
| exchange original | `3a337163978075c730e517bfee5f4faad8a4ddcbd7ea578b5e3187bfc82b2e71` | `38ec7019d25dededf58d5dc046f346ec91e1441a2b78b6b5c398a25f0201aa1a` | `5429fd7e648f4d3d06217e57e1e8344baab06ab7328fd41595a029992501b5bc` |
| reconciled | `1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6` | `00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` | `932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2` |

三个 reconciliation output 的 parent_fact_ids 均严格等于对应的 company/exchange original fact_id。

## 门禁与不变性

- Ruff 0.13.2：通过。
- compileall：通过。
- import：通过。
- Runner、2021—2025 注册证据 targeted pytest：`160 passed`。
- 全量 pytest：`482 passed, 2 warnings`。
- `git diff --check`：通过。
- 2022—2025 四个 bundle 的 Git blob 与 24 个 original canonical Fact ID 均保持不变。
- 默认 `data/research.duckdb` 验收前后 SHA-256 均为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- PDF、PNG、DuckDB、output 和 `data/raw/official` 均未进入 Git。
- `stash@{0}` 保持不动。

## 复验结论

```text
M2 Stage 1C-C.4.1: PASS
M2 Stage 1C-C.4: PASS

initial failure history: PRESERVED
document relationship:
  audited_financial_statements_subset_of_full_annual_report
company direct official evidence: ACCEPTED
exchange direct official evidence: ACCEPTED
independent content sources: false
transaction committed: true
2021—2025 multi-year fact integration: ALLOWED
```
