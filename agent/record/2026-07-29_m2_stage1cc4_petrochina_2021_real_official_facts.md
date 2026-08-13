# M2 Stage 1C-C.4 工作记录：中国石油 2021 年官方事实

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`0f466c5983c2178f4a8f2255bcc33e0b75769f7d`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- Ruff：项目环境固定为 `0.13.2`
- 默认 `data/research.duckdb` 启动 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`
- 目标年度：2021（`2021-01-01` 至 `2021-12-31`）
- Concept：`revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`
- 来源要求：中国石油官网简体 A 股完整年报 + 上交所正式完整年报
- 目标：登记两条正式发布路径，人工双遍复核六条原始事实，并以既有 runner 完成 Reconciliation、PIT、Audit 与 Lineage 验收。
- 非目标：2020 及更早年度、季度、其他公司、其他 Concept、自动发现、PDF 解析/OCR 入库、估值或荐股。
- PDF、PNG、DuckDB、截图及 output 不进入 Git。
- 使用 run-scoped 隔离数据库，不修改默认 `data/research.duckdb`。
- 不修改 runner、Fact Schema、Reconciliation、单位规则或容差。

## 来源发现

### 中国石油官网年度报告栏目

- 列表：`https://www.petrochina.com.cn/petrochina/ndbg/reportnd_list.shtml`
- 列表中唯一标题为 `2021年年度报告` 的完整报告：
  `https://www.petrochina.com.cn/petrochina/ndbg/202204/e5a5109dcf70405d8509e27040125ade/files/a2fdc43b19c547788f5149bf41840698.pdf`
- retrieved_at：`2026-07-29T22:25:37+08:00`
- SHA-256：`ea054145d5bcaf0f3fce9c3b0dab6927461cd231480e99b419bd646584244090`
- 大小：`4,582,111` bytes
- 页数：`276`
- 未加密。

该 PDF 经 Poppler 渲染并目视检查：

- 封面为 `中國石油天然氣股份有限公司 2021年度報告`；
- 封面同时列出香港、纽约和上海交易代码，并非明确的简体 A 股专版；
- CAS 审计报告正文使用 `審計報告`、`中國`、`財務報表`、`準則`、`編製`、`為` 等繁体字；
- 因此属于本阶段明确排除的繁体完整报告。

### 中国石油官网 A 股审计报告

- 公司公告栏目同时提供 `会计师审计报告（A股）`：
  `https://www.petrochina.com.cn/petrochina/gsgg/202203/b39500c66f3b40f5b1a97c5b37f1f75f/files/f066f8223a454855ae08d97d1f3bf0cb.pdf`
- 公告日期：`2022-03-31`
- 页数：`95`
- 该文档是简体 A 股财务报表及审计报告，但不是完整年度报告，不能替代用户要求的简体 A 股完整年度报告。

### 上海证券交易所

- 定期报告页：`https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857`
- 官方接口记录的完整报告标题：`中国石油天然气股份有限公司2021 年度报告`
- 公告日期：`2022-04-01`
- 官方 PDF：
  `https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf`
- 同日摘要 `601857_20220401_5_sJDm4LL5.pdf` 已排除。

上交所存在合规的完整 A 股报告记录，但公司官网没有同时满足“简体、A 股、完整年度报告”的公司来源文档。因此双来源合同在进入事实读取前已经失败，无需也不得以交易所文档、第三方转载或公司 A 股审计报告充当公司官网完整年报。

## 停止点

- 未读取或登记三个目标值。
- 未使用任何后续年报的 2021 比较列。
- 未新增 `2021_annual.json`。
- 未新增注册证据测试。
- 未运行 `official_fact_acceptance`。
- 未创建 DuckDB、PIT、Audit 或 Lineage 结果。
- 未修改 runner、Schema、Reconciliation、单位规则或容差。
- 未修改 2022—2025 已验收证据。
- Ruff、compileall、import、targeted/full pytest 未运行：本阶段在创建 bundle 或代码/测试变更前因来源合同失败而立即停止。
- git diff check：exit 0。
- 默认 `data/research.duckdb` 结束 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`，与启动值一致。
- PDF、PNG、浏览器缓存和下载中间文件已清理；Git 中无 PDF、PNG、DuckDB、output 或 `data/raw/official/**` 跟踪文件。
- `stash@{0}` 保持原状，未 pop。

## 最终判定

**M2 Stage 1C-C.4 Fail。**

阻塞项：`company_official` 没有找到符合现有合同的 2021 年简体 A 股完整年度报告。官网完整报告为繁体；官网简体 A 股文档仅为审计报告，不是完整年报。

Stage 1C-C.4 未完成；不得据此进入 2021—2025 多年度事实整合与重列版本处理。若未来公司提供可核验的简体 A 股完整年报正式路径，可从本基线重新验收。
