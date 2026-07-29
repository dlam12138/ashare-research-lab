# M2 Stage 1C-C.2 正式验收证据：中国石油 2023 年官方事实

## 结论

**Conditional Pass。** 2023 年真实官方事实、Reconciliation、PIT、Audit、Lineage、隔离运行和全部 pytest 均通过；但当前 Ruff 0.12.0 对起始 commit 已存在的三个 `UP038` 报错，严格全仓 Ruff 门禁不是 clean。本阶段未修改 runner 或既有测试绕过该问题。

- 公司：中国石油天然气股份有限公司
- Symbol：`601857.SH`
- 财年：2023
- Period：`2023-01-01` 至 `2023-12-31`
- Context：`601857.SH|2023|annual|consolidated`
- Fact Schema：`2.1`
- Acceptance contract：`annual_official_facts_v1`
- Evidence commit：`709418d`
- run_id：`annual_official_601857_SH_2023_20260729_212055_855553`

## 官方文档

### 中国石油官网

- Landing URL：<https://www.petrochina.com.cn/petrochina/gsgg/202403/b539f133283f4ed59ccfd3abaf257ec7.shtml>
- 简体 A 股 PDF：<https://www.petrochina.com.cn/petrochina/gsgg/202403/b539f133283f4ed59ccfd3abaf257ec7/files/951707e943ab4b989219698aac0e29a1.pdf>
- 页面标题：`2023年度报告（A股）`
- 页面显示发布时间：`2024-03-25`
- retrieved_at：`2026-07-29T21:14:52.482+08:00`
- Content-Type：`application/pdf`
- 大小：`12,437,650` bytes
- 页数：`293`
- SHA-256：`b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692`

官网年度报告列表默认链接的 `842dad...pdf` 是繁体 H 股年度报告，未采用。本验收使用中国石油官网明确标注为 A 股的简体完整报告；封面明确标注《中国石油天然气股份有限公司2023年度报告》和 `A股股票代码：601857`。

### 上海证券交易所

- 601857 定期报告页：<https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857>
- 原 PDF URL：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2024-03-26/601857_20240326_9CKZ.pdf>
- Final PDF URL：<https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2024-03-26/601857_20240326_9CKZ.pdf>
- 公告标题：`中国石油天然气股份有限公司2023年度报告`
- 公告日期：`2024-03-26`
- retrieved_at：`2026-07-29T21:15:59.268+08:00`
- Content-Type：`application/pdf`
- 大小：`12,437,650` bytes
- 页数：`293`
- SHA-256：`b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692`

上交所同日还发布了年度报告摘要，本验收明确排除摘要，只采用完整年度报告。

`document_relationship = byte_identical`。两个正式发布路径的文件字节完全相同，因此不是两个独立编制的内容来源。

## 会计与审计口径

- 语言和版本：简体中文 A 股完整年度报告
- 会计准则：中国企业会计准则（CAS）
- 口径：合并
- 事实类型：年度 duration
- 审计机构：普华永道中天会计师事务所（特殊普通合伙）
- 审计意见：无保留意见
- 审计报告起始页：PDF page 107 / printed page 105

## 双遍人工复核事实

第一遍从公司官网副本目视读取；第二遍重新打开上交所副本相同报表页目视确认。没有使用 OCR 作为事实来源，没有使用 2022 比较列，也没有使用后续年度报告的 2023 比较列。

| Concept | 表名 | 行标签 | 列标签 | 页码 | 双方原始值（人民币百万元） | 规范化值（万元） |
|---|---|---|---|---|---:|---:|
| `revenue` | 2023年度合并及公司利润表 | 营业收入 | 2023年度合并 | PDF page 114 / printed page 112 | 3,011,012 | 301,101,200 |
| `net_profit_attributable_to_parent` | 2023年度合并及公司利润表 | 归属于母公司股东的净利润 | 2023年度合并 | PDF page 114 / printed page 112 | 161,144 | 16,114,400 |
| `operating_cash_flow` | 2023年度合并及公司现金流量表 | 经营活动产生的现金流量净额 | 2023年度合并 | PDF page 115 / printed page 113 | 456,596 | 45,659,600 |

规范化规则为 `RMB_MILLION_TO_CNY_10K_X100`：使用 `Decimal(raw_value) × Decimal("100")`，不经过 float、不舍入、不使用容差。

## Canonical Fact ID

公司官网原始事实：

- `revenue`：`232c4c512fff424f993bd03535036d2b2b57669da0cc6a2508df15a0d1d050b9`
- `net_profit_attributable_to_parent`：`8c0ad69221674ff45505d199b7d6711510d7db2ed91c0dae72ad705a691b2a79`
- `operating_cash_flow`：`efc9b7157781c64a7b992200d1c17a967defa9752ae556f856ff5d6429c95d9a`

上交所原始事实：

- `revenue`：`70a20f6c1b415cda930100ce6af2324c70ad08bce0984baedc7aaa199da72572`
- `net_profit_attributable_to_parent`：`21d6b20c8886ccdecc5783258b8b2a4d6c0990459a799a80ddfb97f14928f973`
- `operating_cash_flow`：`dd37a724277e9cceb6c05c50c78b14d7c53690700dc8a43cad094298a8b7b76a`

六条原始事实均为 canonical、`verified`、`eligible_for_metrics=false`。

## Reconciliation、PIT、Audit 与 Lineage

三个 `RECON_OFFICIAL_NUMERIC_001` v1 结果均为 `matched`：

| Concept | Reconciled fact_id | available_at | eligible |
|---|---|---|---|
| `revenue` | `9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7` | `2024-03-26` | true |
| `net_profit_attributable_to_parent` | `d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4` | `2024-03-26` | true |
| `operating_cash_flow` | `7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289` | `2024-03-26` | true |

真实 run 结果：

- source hash validation：passed
- transaction committed：true
- fact_contexts：1
- company originals：3
- exchange originals：3
- reconciled facts：3
- financial_facts：9
- latest_available_at：`2024-03-26`
- PIT before（`2024-03-25`）：0
- PIT on availability（`2024-03-26`）：3
- Audit：9
- Lineage：9；每个 reconciled fact 均有 company input、exchange input 和 output 三个角色，并引用实际两个输入 fact_id

验收数据库只存在于 `output/value_assessment/601857.SH/annual_official_facts/2023/<run_id>/acceptance.duckdb`。默认 `data/research.duckdb` 运行前后 SHA-256 均为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。

## 后续重列与证据限制

- 两条路径提供同一字节文件，不构成独立内容交叉验证。
- 2024 年度报告因同一控制下企业合并重列了 2023 比较数据：营业收入 `3,012,812`、归母净利润 `161,414`、经营现金流净额 `456,847`。
- 上述后续比较数据与 2023 原始披露 `3,011,012`、`161,144`、`456,596` 不同；本验收未使用后续比较列，也未覆盖 2023 original facts。
- 本阶段不创建 restated 版本；后续重列需要单独契约和复审。

## 质量门禁

- Registered bundle + annual runner tests：`122 passed in 4.95s`
- Reconciliation regression：`86 passed in 6.64s`
- Full pytest：`444 passed, 2 warnings in 43.53s`
- compileall：exit 0
- import validation：OK
- git diff check：exit 0
- 本轮新增测试 Ruff：All checks passed
- `ruff check src tests --ignore UP038`：All checks passed
- 严格 `ruff check src tests`（Ruff 0.12.0）：失败；起始 commit 已有 3 条 `UP038`，位于 runner 两处和既有测试一处
- PDF、DuckDB、output 和 `data/raw/official/**` 均无 Git 跟踪文件
- 2024、2025 bundle 与正式验收报告未修改

最终判定：**M2 Stage 1C-C.2 Conditional Pass**。2023 官方事实验收链路本身通过；在严格全仓 Ruff 基线问题被单独处置或复审明确接受前，不进入 2022 年验收。
