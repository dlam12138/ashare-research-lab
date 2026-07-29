# M2 Stage 1C-C.3 正式验收证据：中国石油 2022 年官方事实

## 结论

**Pass。** 2022 年真实官方事实、Reconciliation、PIT、Audit、Lineage 和隔离运行均通过；两份官方 PDF 已分别渲染并完成双遍目视核对。

- 公司：中国石油天然气股份有限公司
- Symbol：`601857.SH`
- 财年：2022
- Period：`2022-01-01` 至 `2022-12-31`
- Context：`601857.SH|2022|annual|consolidated`
- Fact Schema：`2.1`
- Acceptance contract：`annual_official_facts_v1`
- Evidence commit：`50714bb`
- run_id：`annual_official_601857_SH_2022_20260729_220453_793407`

## 官方文档

### 中国石油官网

- Landing URL：<https://www.petrochina.com.cn/petrochina/gsgg/202303/c19b382ed0784b67a77de51a42a0ca3d.shtml>
- 简体 A 股 PDF：<https://www.petrochina.com.cn/petrochina/gsgg/202303/c19b382ed0784b67a77de51a42a0ca3d/files/d780ae64c9d0404d882a02dfd201e162.pdf>
- 页面标题：`公司2022年度报告（A股）`
- 页面显示发布时间：`2023-03-29`
- retrieved_at：`2026-07-29T21:57:22.200+08:00`
- Content-Type：`application/pdf`
- 大小：`12,261,788` bytes
- 页数：`285`
- SHA-256：`fea19e9033bbcff24357575d02da3e9b8ddda7d5bbcdd7cabfb018a7e35615c1`

### 上海证券交易所

- 601857 定期报告页：<https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857>
- 原 PDF URL：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2023-03-30/601857_20230330_LSV2.pdf>
- Final PDF URL：<https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2023-03-30/601857_20230330_LSV2.pdf>
- 公告标题：`中国石油天然气股份有限公司2022年度报告`
- 公告日期：`2023-03-30`
- retrieved_at：`2026-07-29T21:58:32.148+08:00`
- Content-Type：`application/pdf`
- 大小：`12,257,199` bytes
- 页数：`285`
- SHA-256：`da64c67d9e575c3cfcfbd892ce5e8c19d4cf8ca07d51c47df01be2fa4587d861`

上交所同日的年度报告摘要已排除；繁体 H 股版、英文版、业绩公告和第三方转载均未采用。

`document_relationship = same_report_different_bytes`。两份文件的哈希和大小不同，但封面、审计报告、目标报表、页数、表名、行列和目标值一致。因此，这是同一报告的两条官方发布路径，不是两个独立编制的内容来源。

## 会计与审计口径

- 语言和版本：简体中文 A 股完整年度报告
- 会计准则：中国企业会计准则（CAS）
- 口径：合并
- 事实类型：年度 duration
- 审计机构：普华永道中天会计师事务所（特殊普通合伙）
- 审计意见：无保留意见
- 审计报告起始页：PDF page 106 / printed page 104

## 双遍人工复核事实

第一遍从公司官网副本渲染后目视读取；第二遍重新打开并渲染上交所副本相同报表页目视确认。没有使用 OCR 作为事实来源，没有使用后续年度报告的 2022 比较列。

| Concept | 表名 | 行标签 | 列标签 | 页码 | 双方原始值（人民币百万元） | 规范化值（万元） |
|---|---|---|---|---|---:|---:|
| `revenue` | 2022年度合并及公司利润表 | 营业收入 | 2022年度合并 | PDF page 113 / printed page 111 | 3,239,167 | 323,916,700 |
| `net_profit_attributable_to_parent` | 2022年度合并及公司利润表 | 归属于母公司股东的净利润 | 2022年度合并 | PDF page 113 / printed page 111 | 149,375 | 14,937,500 |
| `operating_cash_flow` | 2022年度合并及公司现金流量表 | 经营活动产生的现金流量净额 | 2022年度合并 | PDF page 114 / printed page 112 | 393,768 | 39,376,800 |

规范化规则为 `RMB_MILLION_TO_CNY_10K_X100`：使用既有确定性十进制转换，不修改单位或容差。

## Canonical Fact ID

公司官网原始事实：

- `revenue`：`80817b56628836a4f6dabf2b57682a06f4724667648fc42876f1a6530ca8f693`
- `net_profit_attributable_to_parent`：`e40af899cb646df7f3c16cd458bd4d991be7822fc39c3890797d4024fc5b70fa`
- `operating_cash_flow`：`b31644176365f6c0e1d1bb1dd3d4caaffc28aae57feedcf1bd2cb0f93db53728`

上交所原始事实：

- `revenue`：`3342b40b4e9ef4931e993a7aede1697ade1bffee1e74ba632eeee9bbcb6eb5ae`
- `net_profit_attributable_to_parent`：`9b70bf5e7b5c98059910449752931a4cbbbd9cf8047fdbf92fcea53b72a56b1e`
- `operating_cash_flow`：`4b202de9d788c0137de7a453a35a7e1ad4bbe5069f964513d67037b3b43e71b6`

六条原始事实均为 canonical、`verified`、`eligible_for_metrics=false`。

## Reconciliation、PIT、Audit 与 Lineage

三个 `RECON_OFFICIAL_NUMERIC_001` v1 结果均为 `matched`：

| Concept | Reconciled fact_id | available_at | eligible |
|---|---|---|---|
| `revenue` | `62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43` | `2023-03-30` | true |
| `net_profit_attributable_to_parent` | `d3f70991ddb193324747fd7673274da61d56ffbfbac9a8a813ef3a1467072603` | `2023-03-30` | true |
| `operating_cash_flow` | `e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d` | `2023-03-30` | true |

真实 run 结果：

- source hash validation：passed
- transaction committed：true
- fact_contexts：1
- company originals：3
- exchange originals：3
- reconciliation matched：3
- reconciled facts：3
- financial_facts：9
- latest_available_at：`2023-03-30`
- PIT before（`2023-03-29`）：0
- PIT on availability（`2023-03-30`）：3
- Audit：9
- Lineage：9；每个 reconciled fact 均有 company input、exchange input 和 output 三个角色，并引用实际两个输入 fact_id

验收数据库只存在于 `output/value_assessment/601857.SH/annual_official_facts/2022/<run_id>/acceptance.duckdb`。默认 `data/research.duckdb` 的运行前后 SHA-256 均为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。

## 后续重列与证据限制

- 两条路径承载同一报告，不构成独立内容交叉验证；本阶段核验的是两个官方发布路径的事实一致性。
- 2023 年度报告中的 2022 比较数为营业收入 `3,239,167`、归母净利润 `148,738`、经营现金流净额 `393,768`（人民币百万元）。
- 后续比较列的归母净利润与 2022 原始披露 `149,375` 不同，记录为潜在重列；本验收未使用后续比较列，也未覆盖 2022 original facts。
- 本阶段不创建 restated 版本；后续重列需要单独契约和复审。

## 质量门禁

- Ruff toolchain：`ruff==0.13.2`
- Strict Ruff：`python -m ruff check src tests`，All checks passed，exit 0
- Registered bundle + annual runner tests：`135 passed in 5.67s`
- Reconciliation regression：`92 passed in 8.27s`
- Full pytest：`457 passed, 2 warnings in 41.43s`
- compileall：exit 0
- import validation：OK
- git diff check：exit 0
- PDF、PNG、DuckDB、output 和 `data/raw/official/**` 均无 Git 跟踪文件
- 2023、2024、2025 bundle 与正式验收报告未修改
- runner、Fact Schema、Reconciliation 和单位规则未修改
- `stash@{0}` 保持原状，未 pop

最终判定：**M2 Stage 1C-C.3 Pass**。
