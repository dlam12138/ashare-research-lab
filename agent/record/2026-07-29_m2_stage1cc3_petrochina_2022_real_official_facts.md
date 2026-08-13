# M2 Stage 1C-C.3 工作记录：中国石油 2022 年官方事实

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`d8c241b18d4fd741d0c7de6c93aa581676a7e874`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- Ruff：项目环境固定为 `0.13.2`
- 目标年度：2022（`2022-01-01` 至 `2022-12-31`）
- Concept：`revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`
- 来源要求：中国石油官网简体 A 股完整年报 + 上交所正式完整年报
- 目标：登记两条正式发布路径，人工双遍复核六条原始事实，并以既有 runner 完成 Reconciliation、PIT、Audit 与 Lineage 验收。
- 非目标：2021、季度、其他公司、其他 Concept、自动发现、PDF 解析/OCR 入库、估值或荐股。
- 北极星对齐：确定性官方证据、公告日 PIT、事实身份和 lineage 可追溯。
- PDF、PNG、DuckDB、截图及 output 不进入 Git。
- 使用 run-scoped 隔离数据库，不修改默认 `data/research.duckdb`。
- 不修改 runner、Fact Schema、Reconciliation 或单位规则。

## 官方文档登记

### 中国石油官网

- Landing URL：`https://www.petrochina.com.cn/petrochina/gsgg/202303/c19b382ed0784b67a77de51a42a0ca3d.shtml`
- PDF URL：`https://www.petrochina.com.cn/petrochina/gsgg/202303/c19b382ed0784b67a77de51a42a0ca3d/files/d780ae64c9d0404d882a02dfd201e162.pdf`
- 页面标题：`公司2022年度报告（A股）`
- 公告日期：`2023-03-29`
- retrieved_at：`2026-07-29T21:57:22.200+08:00`
- SHA-256：`fea19e9033bbcff24357575d02da3e9b8ddda7d5bbcdd7cabfb018a7e35615c1`
- 大小：`12,261,788` bytes
- 页数：`285`

### 上海证券交易所

- 定期报告页：`https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857`
- 原 PDF URL：`https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2023-03-30/601857_20230330_LSV2.pdf`
- Final PDF URL：`https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2023-03-30/601857_20230330_LSV2.pdf`
- 公告标题：`中国石油天然气股份有限公司2022年度报告`
- 公告日期：`2023-03-30`
- retrieved_at：`2026-07-29T21:58:32.148+08:00`
- SHA-256：`da64c67d9e575c3cfcfbd892ce5e8c19d4cf8ca07d51c47df01be2fa4587d861`
- 大小：`12,257,199` bytes
- 页数：`285`

两份文件哈希和大小不同，但封面、审计报告、目标报表、页数、表名、行列与目标值一致，登记为 `same_report_different_bytes`；它们是同一报告的两条官方发布路径，不是两份独立编制的内容来源。繁体 H 股版、英文版、年报摘要、业绩公告及第三方转载均未采用。

## PDF 目视双遍复核

- 第一遍：渲染并目视检查中国石油官网 PDF 的封面、审计报告、合并利润表和合并现金流量表。
- 第二遍：独立渲染并目视检查上交所 PDF 的相同页面。
- 封面：简体中文、`2022年度报告`、`A股股票代码：601857`。
- 会计口径：中国企业会计准则，合并口径。
- 审计机构：普华永道中天会计师事务所（特殊普通合伙）。
- 审计意见：无保留意见。
- 审计报告：PDF page 106 / printed page 104。

| Concept | 表名 | 行标签 | 列标签 | 页码 | 原始值（人民币百万元） | 规范化值（万元） |
|---|---|---|---|---|---:|---:|
| `revenue` | 2022年度合并及公司利润表 | 营业收入 | 2022年度合并 | PDF page 113 / printed page 111 | 3,239,167 | 323,916,700 |
| `net_profit_attributable_to_parent` | 2022年度合并及公司利润表 | 归属于母公司股东的净利润 | 2022年度合并 | PDF page 113 / printed page 111 | 149,375 | 14,937,500 |
| `operating_cash_flow` | 2022年度合并及公司现金流量表 | 经营活动产生的现金流量净额 | 2022年度合并 | PDF page 114 / printed page 112 | 393,768 | 39,376,800 |

转换继续使用既有 `RMB_MILLION_TO_CNY_10K_X100`，未修改单位或容差。

## 后续比较列检查

2023 年报中的 2022 比较数为营业收入 `3,239,167`、归母净利润 `148,738`、经营现金流净额 `393,768`（人民币百万元）。归母净利润与 2022 原始披露 `149,375` 不同，属于后续比较数据重列线索。本阶段严格采用 2022 年报原始列，不创建 restated 事实，也不覆盖 original。

## 真实离线验收

- 命令：`python -m ashare_research.tools.official_fact_acceptance`
- run_id：`annual_official_601857_SH_2022_20260729_220453_793407`
- status：`passed`
- transaction committed：`true`
- source hash validation：`passed`
- Fact Schema：`2.1`
- contexts：1
- company originals：3
- exchange originals：3
- matched / reconciled：3 / 3
- financial_facts：9
- PIT before / on availability：0 / 3
- Audit：9
- Lineage：9
- latest_available_at：`2023-03-30`
- 隔离数据库：`output/value_assessment/601857.SH/annual_official_facts/2022/<run_id>/acceptance.duckdb`
- 默认 `data/research.duckdb` 运行前后 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## Canonical Fact ID

公司原始：

- revenue：`80817b56628836a4f6dabf2b57682a06f4724667648fc42876f1a6530ca8f693`
- net profit attributable：`e40af899cb646df7f3c16cd458bd4d991be7822fc39c3890797d4024fc5b70fa`
- operating cash flow：`b31644176365f6c0e1d1bb1dd3d4caaffc28aae57feedcf1bd2cb0f93db53728`

上交所原始：

- revenue：`3342b40b4e9ef4931e993a7aede1697ade1bffee1e74ba632eeee9bbcb6eb5ae`
- net profit attributable：`9b70bf5e7b5c98059910449752931a4cbbbd9cf8047fdbf92fcea53b72a56b1e`
- operating cash flow：`4b202de9d788c0137de7a453a35a7e1ad4bbe5069f964513d67037b3b43e71b6`

Reconciled：

- revenue：`62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43`
- net profit attributable：`d3f70991ddb193324747fd7673274da61d56ffbfbac9a8a813ef3a1467072603`
- operating cash flow：`e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d`

## 测试与门禁

- Ruff 0.13.2 严格全仓检查：All checks passed，exit 0。
- 年度 runner 与 2022—2025 注册证据 targeted pytest：`135 passed in 5.67s`。
- Reconciliation regression：`92 passed in 8.27s`。
- Full pytest：`457 passed, 2 warnings in 41.43s`。
- compileall：exit 0。
- import validation：OK。
- git diff check：exit 0。
- 仅新增 2022 bundle、2022 注册证据测试、工作记录和正式报告；未修改 runner、Fact Schema、Reconciliation、单位规则或 2023—2025 验收证据。
- PDF、PNG、DuckDB、output 与 `data/raw/official/**` 无 Git 跟踪文件。
- `stash@{0}` 保持原状。

## 最终判定

**M2 Stage 1C-C.3 Pass。** 待独立提交与远程哈希核验。
