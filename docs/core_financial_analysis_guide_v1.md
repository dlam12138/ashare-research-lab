<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->
<!-- AI provenance: action=modified; model=GPT-5; agent=Codex; date=2026-10-10 -->
<!-- AI provenance: action=modified; model=GPT-5; agent=Codex; date=2026-10-10 -->

# 任意标的多年度核心财务分析使用指南（v1）

## 定位与边界

`ashare_research.tools.financial_analysis` 在**调用者显式指定的只读 DuckDB 事实数据库**
上，为任意合格 A 股标的生成多年度 PIT 核心财务画像。它把此前绑定固定公司/固定概念快照的
重放能力推广为通用分析入口，并复用仓库**既有**的 12 个指标定义（4 成长 + 2 现金流 +
4 盈利质量 + 2 资本回报），不新增任何公式、口径或版本准入。

明确不做：不联网、不获取数据、不写数据库、不创建或迁移 schema、不读取默认数据库路径、
不生成评分/排名/资格/建议/目标价/估值结论，也不产生研究阶段结论。报告是离线读取模型，
`production_eligible` / `score_eligible` / `metric_publication_proven` 恒为 false。

## 快速开始

```powershell
# 统一研究入口（与 python -m 等价）
ashare-research research financial --help

# 单年度 Markdown 报告
python -m ashare_research.tools.financial_analysis `
  --database path/to/facts.duckdb --symbol 601857.SH --as-of 2024-03-31 --year 2023

# 多年度 JSON + 两时点重述对比
python -m ashare_research.tools.financial_analysis `
  --database path/to/facts.duckdb --symbol 601857.SH `
  --as-of 2024-03-31 --compare-with 2025-03-31 --year 2022 --year 2023 --json

# 导出确定性报告目录（report.md、report.json、manifest.json）
python -m ashare_research.tools.financial_analysis `
  --database path/to/facts.duckdb --symbol 601857.SH `
  --as-of 2024-03-31 --year 2023 --output tmp/my-financial-report
```

参数：

- `--database PATH`（必填）：显式只读 DuckDB 事实数据库；必须已存在且不是符号链接。
- `--symbol SYMBOL`（必填）：`^\d{6}\.(SH|SZ)$`，如 `601857.SH`。
- `--as-of ISO_DATE`（必填）：PIT 时点；同时是所有选中需要的“可得性”下界。
- `--compare-with ISO_DATE`（可选）：对比时点，**不得早于** `--as-of`；同一只读事务内读取
  两个 PIT 视图。
- `--year YEAR`（必填，可重复）：有界年度窗口，最多 30 个不同年度，范围 1990–2100。
- `--metric METRIC_ID`（可选，可重复）：12 个既有指标之一；默认全部 12 个。
- `--scope consolidated|parent_company`（默认 `consolidated`）。
- `--json` 与 `--output NEW_DIR` 互斥；`--output` 目标必须是不存在的新目录。

## 指标集合（既有定义，无新增）

| metric_id | 角色绑定 |
| --- | --- |
| `revenue_yoy`、`operating_cash_flow_yoy`、`net_profit_attributable_to_parent_yoy`、`net_profit_excluding_non_recurring_yoy` | `current` 取当年、`prior` 取 FY-1 |
| `operating_cash_flow_to_attributable_net_profit`、`cash_paid_for_fixed_assets_to_revenue`、`gross_margin`、`operating_profit_margin`、`gross_profit` | 当年分子/分母（成本类为当年流量） |
| `cash_based_free_cash_flow_proxy` | 当年经营现金流 − 当年购建固定资产现金 |
| `return_on_average_equity_attributable_to_parent`、`return_on_average_total_assets` | `opening` 取 FY-1 年末时点余额、`closing` 取当年年末时点余额 |

## PIT 选择与绑定规则

- 先用公开门禁 `AsOfQuery.get_latest_available` 对每个事实键（symbol、concept、period_end、
  scope）选出 `available_at <= 查询时点` 的最新版本；仅 `verified`/`reconciled` 且
  `eligible_for_metrics` 的事实可见。未来版本一律不参与。
- 只绑定**年末**记录：年度流量要求 `period_end = YYYY-12-31` 且 `period_type = annual`；
  时点余额（`total_assets`、`equity_attributable_to_parent`）要求 `period_type = instant`。
  期间类型不符的记录不会以“最近可用”方式替代，而是显式记为缺失/排除。
- 事实与上下文必须属于同一公司、年度和合并范围，且两个 `period_end` 都为该年末。
  年度流量的上下文必须是 `duration`，从当年 1 月 1 日开始；时点余额必须是
  `instant`，`period_start` 可以为空或等于年末时点。违反这些条件的已选事实以
  `period_context_mismatch` 排除，相关指标保持缺失；不会回退到更早的事实版本。
- 年度窗口 `[Y..N]` 内部实际需要 `Y-1..N` 年的事实，以便计算首年同比与期初余额。

## 值精度边界（绝不四舍五入）

既有 DOUBLE 存储只按“有限整数且绝对值 ≤ 2^53−1”精确使用；单位必须恰为 `万元`，
`source_tier` 必须恰为 `reconciled_derived`。不满足的输入**逐条显式排除**，在
`excluded_inputs` 与对应角色绑定上给出稳定原因码：

`value_not_exact_integer`、`value_out_of_safe_integer_range`、`unit_not_wan_yuan`、
`source_tier_not_reconciled_derived`、`context_missing`、`period_context_mismatch`、
`period_end_invalid`。

排除不会被当作“缺失证据”，也不会触发插值、替代或回退。

NaN 和正负无穷值保持 `value_not_exact_integer` 排除原因，事实索引中的 `value`
与 `value_integer` 输出为 `null`；相关指标保持 `missing_input`，不会替换为零。
JSON 序列化拒绝非有限数字，导出报告可由严格 JSON 解析器读取。

## 输出结构

- `as_of` / `compare_with` 两个视图：`selected_fact_index`（全部选中事实）、
  `excluded_inputs`、`records`（每指标×年度：`status`、精确十进制 `value`、
  `missing_roles`、逐角色 `inputs`（来源引用、lineage、父事实解析状态）、
  `input_available_at_bound`）、`year_over_year`（相邻年度描述性算术差）。
- `comparison`（请求对比时点时）：按指标/年度键给出 `status_changed`、`value_changed`、
  `inputs_changed`、`unchanged`，数值比较用精确 Decimal；缺失保持 null/`—`，绝不当作 0。
- `selector_digest`：选择器与数据库 SHA256 的确定性摘要；报告不含绝对路径与当前时间戳。
- `--output` 目录：`report.md`、`report.json`、`manifest.json`（含渲染字节数与 SHA256、
  选中事实与结果 ID）。目录已存在时以 `OUTPUT_PATH_EXISTS` 拒绝，绝不覆盖。

`input_available_at_bound` 是所选输入中最大的 `available_at`，是输入可得性上界，
**不是**指标发布时间；`created_at` 只收到固定标记 `offline-analysis-not-a-publication-time`。

## 退出码与错误码

成功退出码 0；已净化的已知失败退出码 2，stdout 为空，stderr 输出 `error: <CODE>`：
`INVALID_SYMBOL`、`INVALID_AS_OF_DATE`、`INVALID_COMPARE_WITH`、`COMPARE_BEFORE_AS_OF`、
`INVALID_YEAR`、`INVALID_SCOPE`、`UNKNOWN_METRIC`、`INVALID_ARGUMENTS`、
`DATABASE_NOT_FOUND`、`DATABASE_OPEN_FAILED`、`DATABASE_READ_FAILED`、
`DATABASE_SCHEMA_UNEXPECTED`、`METRIC_REGISTRY_INCOMPLETE`、`METRIC_FACT_INVALID`、
`OUTPUT_PATH_EXISTS`、`OUTPUT_WRITE_FAILED`、`UNEXPECTED_FAILURE`。
选择器校验先于任何数据库访问；不存在的数据库不会被创建。

## 已知限制

- 调用者提供的数据库被当作事实输入：本工具不证明其来源、可得性或独立性，也不重新验证
  `available_at` 的真实性，只按公开 PIT 门禁使用。
- lineage 与父事实只来自数据库自身的 `fact_lineage` / `financial_facts`；父事实解析状态为
  `resolved_available_at_as_of`、`retained_not_available_at_as_of`、
  `absent_from_selected_database`。
- 相邻年度差值只是描述性算术差，不是趋势、显著性、评分或研究结论。
- 报告摘要只证明内容一致性，不构成生产、评分、执行或研究授权。

## 验收与测试

- 测试：`python -m pytest -q tests/test_financial_analysis.py`
- 任务合同：`agent/goals/2026-10-09_core_financial_analysis.md`
- 工作记录：`agent/record/2026-10-09_05-core-financial-analysis.md`
- 验收：`acceptance/2026-10-10_m2_core_financial_analysis.md`
