# M2 Stage 1C-C.1 正式验收证据：中国石油 2024 年官方事实

## 结论

**Pass。** 使用中国石油官网和上海证券交易所两个正式发布路径所提供的同一份简体 A 股完整年度报告，完成三个经审计合并财务事实的离线验收。

- 公司：中国石油天然气股份有限公司
- Symbol：`601857.SH`
- 财年：2024
- Period：`2024-01-01` 至 `2024-12-31`
- Context：`601857.SH|2024|annual|consolidated`
- Fact Schema：`2.1`
- Acceptance contract：`annual_official_facts_v1`
- Evidence commit：`9574c6c3474ac878205eced5fe634ca19e0cc5f8`
- run_id：`annual_official_601857_SH_2024_20260729_205819_354458`

## 官方文档

### 中国石油官网

- Landing URL：<https://www.petrochina.com.cn/petrochina/rdxx/202503/b8750418435d4da380a6b13d5725ebe9.shtml>
- 简体 A 股 PDF：<https://www.petrochina.com.cn/petrochina/rdxx/202503/b8750418435d4da380a6b13d5725ebe9/files/4ed3388fde7b4f4a922b2de43d6225d6.pdf>
- 页面显示发布时间：`2025-03-30`
- retrieved_at：`2026-07-29T20:52:48.462+08:00`
- Content-Type：`application/pdf`
- 大小：`11,167,845` bytes
- 页数：`280`
- SHA-256：`15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba`

官网报告列表默认链接的 `92270...pdf` 是繁体 H 股年度报告，未采用。本验收使用同一官网发布目录中的简体 A 股完整报告；封面明确标注《中国石油天然气股份有限公司2024年度报告》和 `A股股票代码：601857`。

### 上海证券交易所

- 601857 定期报告页：<https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857>
- 原 PDF URL：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-03-31/601857_20250331_9OUT.pdf>
- Final PDF URL：<https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-03-31/601857_20250331_9OUT.pdf>
- 公告标题：`中国石油天然气股份有限公司2024年度报告`
- 公告日期：`2025-03-31`
- retrieved_at：`2026-07-29T20:53:33.569+08:00`
- Content-Type：`application/pdf`
- 大小：`11,167,845` bytes
- 页数：`280`
- SHA-256：`15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba`

`document_relationship = byte_identical`。两个正式发布路径的文件字节完全相同，因此不是两个独立编制的内容来源。

## 会计与审计口径

- 语言和版本：简体中文 A 股完整年度报告
- 会计准则：中国企业会计准则（CAS）
- 口径：合并
- 事实类型：年度 duration
- 审计机构：毕马威华振会计师事务所（特殊普通合伙）
- 审计意见：无保留意见
- 审计报告起始页：PDF page 107 / printed page 105

## 双遍人工复核事实

第一遍从公司官网副本目视读取；第二遍重新打开上交所副本相同报表页目视确认。没有使用 OCR 作为事实来源，没有使用 2023 比较列。

| Concept | 表名 | 行标签 | 列标签 | 页码 | 双方原始值（人民币百万元） | 规范化值（万元） |
|---|---|---|---|---|---:|---:|
| `revenue` | 2024年度合并及公司利润表 | 营业收入 | 2024年度合并 | PDF page 115 / printed page 113 | 2,937,981 | 293,798,100 |
| `net_profit_attributable_to_parent` | 2024年度合并及公司利润表 | 归属于母公司股东的净利润 | 2024年度合并 | PDF page 115 / printed page 113 | 164,676 | 16,467,600 |
| `operating_cash_flow` | 2024年度合并及公司现金流量表 | 经营活动产生的现金流量净额 | 2024年度合并 | PDF page 116 / printed page 114 | 406,532 | 40,653,200 |

规范化规则为 `RMB_MILLION_TO_CNY_10K_X100`：使用 `Decimal(raw_value) × Decimal("100")`，不经过 float、不舍入、不使用容差。

## Canonical Fact ID

公司官网原始事实：

- `revenue`：`de04cf1a1ad6319926e7fac0324ca7107b137c1e2ccac8b043ab3113111bf8d7`
- `net_profit_attributable_to_parent`：`c68c5eb457d7a7fda556fd8f3ab7330deefa333a5d43862068773adaa58afffc`
- `operating_cash_flow`：`7477571542e7336afa3532d8c0957904cd923b02af9087ae8a334c817cfc9867`

上交所原始事实：

- `revenue`：`741a6ee18c719382ab9616c28ee9816a71e5a7e8653c695c21e1581045de2911`
- `net_profit_attributable_to_parent`：`1e5f7988349e6e1f0914417ed91a90dab3edbd3fa3ad6c9f0b42d1658af18eb6`
- `operating_cash_flow`：`da3c485c75ffb34fdfa15afeec8b19bc2b76d8755ad54f96bb3f1e88afe95164`

六条原始事实均为 canonical、`verified`、`eligible_for_metrics=false`。

## Reconciliation、PIT、Audit 与 Lineage

三个 `RECON_OFFICIAL_NUMERIC_001` v1 结果均为 `matched`：

| Concept | Reconciled fact_id | available_at | eligible |
|---|---|---|---|
| `revenue` | `edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196` | `2025-03-31` | true |
| `net_profit_attributable_to_parent` | `d082020ffd54095ac923e545c0c540449a7b8a3b7b1c78872b184423b9af065f` | `2025-03-31` | true |
| `operating_cash_flow` | `3356c5c1cb02b386d2d6d0720c81109f13191aad4d453ead86553267ab3c2e43` | `2025-03-31` | true |

真实 run 结果：

- source hash validation：passed
- transaction committed：true
- fact_contexts：1
- company originals：3
- exchange originals：3
- reconciled facts：3
- financial_facts：9
- latest_available_at：`2025-03-31`
- PIT before（`2025-03-30`）：0
- PIT on availability（`2025-03-31`）：3
- Audit：9
- Lineage：9；每个 reconciled fact 均有 company input、exchange input 和 output 三个角色，并引用实际两个输入 fact_id

验收数据库只存在于 `output/value_assessment/601857.SH/annual_official_facts/2024/<run_id>/acceptance.duckdb`。默认 `data/research.duckdb` 运行前后 SHA-256 均为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。

## 证据限制与比较检查

- 两条路径提供同一字节文件，不构成独立内容交叉验证。
- 2025 年度报告中的 2024 比较列仅用于人工 sanity check；三项数值与本次 2024 原始报告一致，未发现差异。
- 2025 比较列没有被用作来源事实，也没有覆盖 2024 original fact。

## 质量门禁

- Registered bundle + runner tests：`109 passed in 5.22s`
- Reconciliation regression：`86 passed in 6.86s`
- Full pytest：`431 passed, 2 warnings in 40.88s`
- Ruff：All checks passed，exit 0
- compileall：exit 0
- import validation：OK
- git diff check：exit 0
- PDF、DuckDB、output 和 `data/raw/official/**` 均无 Git 跟踪文件
- 2025 bundle 与正式验收报告未修改

最终判定：**M2 Stage 1C-C.1 Pass**。进入 2023 年验收前仍需完成远程复审。
