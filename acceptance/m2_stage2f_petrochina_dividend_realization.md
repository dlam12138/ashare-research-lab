# M2 Stage 2F：PetroChina 2021—2025 现金分红兑现与覆盖指标

## 结论

Stage 2F 离线 vertical slice 已通过 targeted runner、定义/引擎边界测试和重跑幂等门禁。
正式 run-scoped 输出：

`tmp/stage2f_runs/value_assessment/601857.SH/dividend_realization_vertical_slice/2021_2025/stage2f_validation_20260801e/`

该目录包含 `metrics.duckdb`、`definitions/results/latest/PIT/transitions/lineage`、
事件台账、事实覆盖、回购登记、`run_manifest.json` 与 `summary.md`。正式 runner 只读
提交的 JSON 与临时 foundation；不访问网络、PDF、共享 cache 或默认数据库。

## 事件与事实合同

- 事件合同：`dividend_event_record_v1`；2021—2025 每年 interim/final 两条，合计 10 条。
- 事件身份：`build_dividend_event_id()` canonical SHA-256 ID；链条保留 proposal、
  shareholder_approved、implementation_announced、paid/implemented 四阶段。
- 只有已实施现金分红进入兑现计算；范围固定为 `A_H_ordinary_combined`、CNY、普通股。
- 每条事件同时登记公司官网/公司官方镜像与上交所官方披露定位，金额、每股金额、记录日、
  除息日和发放日作为 source evidence；Rule 007 要求一公司官方 + 一交易所官方且精确相等。
- Rule 007：`RECON_OFFICIAL_NUMERIC_007 v1`。10 条事件 × 3 个数值概念 × 3 层 Fact，
  新增 90 个 run-scoped Fact，其中 30 个 `reconciled_derived` eligible Fact；不生成回购零值。
- 回购扫描为 `bounded_search_no_event_found`，并明确其边界，不把缺口解释为零。

## 指标

新增四个 `score_eligible=false`、version 1 的透明指标：

1. `cash_dividend_payout_ratio`
2. `operating_cash_flow_dividend_coverage`
3. `free_cash_flow_proxy_dividend_coverage`
4. `implemented_cash_dividend_per_share`

事件列表按 declared role 绑定；CNY 事件金额与基础财务事实的万元口径显式换算，使用
Decimal prec28、ROUND_HALF_EVEN、1e-12 量化。缺少事件/事实为 `missing_input`，零现金分红
为 `undefined_no_dividend`；不使用 raw/ineligible Fact。

最新可用回放生成 20 个年度 Result、20 个 computed Result、60 行 lineage；FY2025
`revision_review_status=not_yet_reviewable`。五个年报 PIT 日的分红指标 computed 数为
`0/4/8/12/16`；2026-03-30 时 FY2025 final 尚未可用，后续离线 latest 才完整。

## 冻结与门禁

正式 runner 重建并验证：旧 354 Fact、16 definitions、102 个既有 Metric Result 的 ID 与语义
保持不变；默认 `data/research.duckdb` SHA-256 前后均为
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；ROIC 和 scoring 均未
计算或输出。Stage 2D-B/C/D/E、Rule 001—006、ROE/ROA 与 stash 由 foundation gate
重新验证。没有 DB/PDF/PNG 进入变更集。

已覆盖：事件 canonical ID 与完整链、Rule 007 精确对账/错误单位拒绝、公式与事实绑定、
lineage 一一对应、零/缺失/raw 输入边界、metric canonical ID、最新/年报 PIT、2025 状态、
无 ROIC/score 输出、runner 幂等重跑。

## Gate results

- Targeted Stage 2F：`9 passed`；保护/历史 runner targeted：`77 passed`。
- Full pytest：`920 passed, 2 warnings`。
- 全仓 Ruff、compileall/import、`git diff --check`：通过。
- 默认 DB SHA-256、stash、旧 Fact/Metric/ROE/ROA 与 Stage 2D-B/C/D/E protected blobs：通过；
  roadmap 仅新增本 Stage 2F append-only 状态，并同步更新保护断言。
- 污染检查：变更集无 `.duckdb`、PDF 或 PNG；run-scoped DuckDB 只位于离线输出目录。

## 官方 evidence 定位

完整 URL 与日期/数值保存在 `events/dividend_events_2021_2026.json`；来源为 PetroChina
官网、上交所官方披露及官方公告索引。仓库不提交 PDF，正式 runner 不读取 PDF/cache。

## 最终状态

- Dividend implementation facts: `TRUSTED`
- Payout and cash-flow coverage metrics: `TRUSTED`
- Repurchase evidence: `DOCUMENTED`
- Dividend realization layer: `COMPLETE`
- Valuation PIT foundation: `ALLOWED`
- ROIC: `NOT YET`
- Scoring: `STILL NOT YET`
- Next-stage selection: `NORTH-STAR REVIEW REQUIRED`
