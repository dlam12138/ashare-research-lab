# M2 Stage 1C-B 正式验收证据：中国石油 2025 年官方事实

## 结论

**Pass。** 已用《中国石油天然气股份有限公司2025年年度报告》的两个正式发布路径完成三项经审计合并财务事实的离线核验。两个路径承载同一份年度报告，不构成两个独立编制的内容来源。

- Symbol：`601857.SH`
- 期间：`2025-01-01` 至 `2025-12-31`
- Context：`601857.SH|2025|annual|consolidated`
- 会计准则：CAS
- Fact Schema：`2.1`
- Acceptance run_id：`stage1cb_20260729_200911_593537`
- 隔离数据库：run 目录内 `acceptance.duckdb`
- 工具 commit：`0b1f8679d75a87d615d03675403c5d72983d2f02`

## 官方文档登记

### 中国石油公司官网

- Landing URL：<https://www.petrochina.com.cn/petrochina/rdxx/202603/77efc25cfdc14bad83525f05cf092454.shtml>
- PDF URL / final PDF URL：<https://www.petrochina.com.cn/petrochina/rdxx/202603/77efc25cfdc14bad83525f05cf092454/files/e3eab58b4de94a8aa43abf7ec9a40123.pdf>
- 官网页面标题：`2025年度报告`
- 官网页面显示发布时间：`2026-03-29`
- retrieved_at：`2026-07-29T19:44:10+08:00`
- HTTP content type：`application/pdf`
- 文件大小：`10,608,680` bytes
- 页数：`273`
- SHA-256：`0eba96bd4e815187e7b64645f523f2b5d363ca3fea8168a63ec930f624715f8d`

### 上海证券交易所

- 601857 定期报告页：<https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857>
- 原 PDF URL：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-03-30/601857_20260330_6PPK.pdf>
- final PDF URL：<https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-03-30/601857_20260330_6PPK.pdf>
- 公告标题：`中国石油天然气股份有限公司2025年年报`
- 公告页显示日期：`2026-03-30`
- retrieved_at：`2026-07-29T19:50:48+08:00`
- HTTP content type：`application/pdf`
- 文件大小：`9,416,509` bytes
- 页数：`273`
- SHA-256：`840b15aa4dc38745a6b86a3656063e6a73081ce87407acb0ca93554f4e836e65`

`document_relationship = same_report_different_bytes`。两份文件哈希与大小不同；封装或元数据差异是可能解释，但本验收不把原因写成已确认事实。人工复核确认两份文件的标题、股票代码、报告期、总页数、审计报告、目标财务报表页面和三个目标值一致；目标页渲染结果逐字节一致。诚实性限制是：这是两个正式发布路径，不是两个独立内容来源。

## 人工复核事实

所有值来自经审计合并财务报表的 `2025年度 合并` 列，不取摘要页。原始单位均为`人民币百万元`，确定性规范化规则均为 `RMB_MILLION_TO_CNY_10K_X100`，即 `Decimal(raw_value) × Decimal("100")`，不经过 float、不舍入。

| Concept | 表名 | 正式行标签 | 页码 | 公司原始值 | 上交所原始值 | 规范化值（万元） |
|---|---|---|---|---:|---:|---:|
| `revenue` | 2025年度合并及公司利润表 | 营业收入 | PDF page 109 / printed page 107 | 2,864,469 | 2,864,469 | 286,446,900 |
| `net_profit_attributable_to_parent` | 2025年度合并及公司利润表 | 归属于母公司股东的净利润 | PDF page 109 / printed page 107 | 157,302 | 157,302 | 15,730,200 |
| `operating_cash_flow` | 2025年度合并及公司现金流量表 | 经营活动产生的现金流量净额 | PDF page 110 / printed page 108 | 412,510 | 412,510 | 41,251,000 |

审计报告位于 PDF page 101—106；审计意见覆盖按中国企业会计准则编制的财务报表。

## Canonical Fact ID

公司官网原始事实：

- `revenue`：`73ed6cf1ddce425e2d51a54272336ee8f2891f54b31a020d8922157de068e6cf`
- `net_profit_attributable_to_parent`：`16d823106e9f4a4538ce81f9113b0fb4b13314e0469a9a224bde8521db114626`
- `operating_cash_flow`：`a1578249e0cb33585398a5b924ae26896968f563dac7a685f804f32bbec4c86d`

上交所原始事实：

- `revenue`：`a33a051d1ee4aa12b5930aefa1aa70b8bc8e8c72c8ebe7b236f4eaebb618c37b`
- `net_profit_attributable_to_parent`：`32de1c06a68c8030fe1526d71ada3c25b315dce8b1cf6f19d34ef977b0826e50`
- `operating_cash_flow`：`01e3aa3597616feff38621837057a3619400f3d29be72285e1e0ec231ffef47e`

三条公司事实和三条交易所事实均为 `verification_status=verified`、`eligible_for_metrics=false`、`is_derived=false`。

## Reconciliation、PIT、Audit 与 Lineage

`RECON_OFFICIAL_NUMERIC_001` v1 的三组结果均为 `matched`：

| Concept | Reconciled fact_id | available_at | eligible |
|---|---|---|---|
| `revenue` | `460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1` | `2026-03-30` | true |
| `net_profit_attributable_to_parent` | `9009dbb2ddaf6981e33d68fafd2cce681c0c87e591d30a1fa366d0051b38df6c` | `2026-03-30` | true |
| `operating_cash_flow` | `ad3b6e2a3675ce7e8a8e16bda427597b72d28e30808281e17cd4aa549949357a` | `2026-03-30` | true |

真实 run 结果：

- source hash validation：passed
- `fact_contexts`：1
- 公司原始事实：3
- 上交所原始事实：3
- reconciled 事实：3
- `financial_facts`：9
- PIT before（`2026-03-29`，默认查询）：0
- PIT on availability（`2026-03-30`，默认查询）：3，且全部 reconciled / eligible
- Audit：9（3 company + 3 exchange + 3 reconciled）
- Lineage：9 行；每个核验 run 各有 `reconciliation_input_company`、`reconciliation_input_exchange`、`reconciliation_output` 三个角色
- 每个 output 的 `parent_fact_ids` 等于实际两个输入 fact_id；三类角色均记录 `RECON_OFFICIAL_NUMERIC_001` 和版本 `1`
- transaction committed：true

## 隔离与质量门禁

- Runner 全程离线，不导入或调用网络客户端。
- 验收库位于 `output/value_assessment/601857.SH/stage1cb/<run_id>/acceptance.duckdb`；未读取或修改 `data/research.duckdb`。
- PDF 位于 `data/raw/official/...` 的 Git 忽略目录。
- `ruff check src tests`：exit 0。
- `python -m compileall -q src tests`：exit 0。
- import validation：OK。
- `pytest -q`：`361 passed, 2 warnings in 40.58s`。
- `git diff --check`：exit 0。
- 警告来自既有日期解析测试，不影响本验收。

最终判定：**Pass**。允许进入固定下一阶段 `M2 Stage 1C-C：扩展中国石油2021—2024年度官方事实`；先扩展年度报告，不立即录入季度数据。
