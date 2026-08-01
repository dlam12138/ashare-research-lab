# M2 Stage 2D-F：中国石油 2021—2025 ROA 透明 Metric

## 结论

Stage 2D-F 已通过离线 runner、Metric Engine 边界测试、PIT/重列验收、既有基线不变性检查和
全量测试（`899 passed, 2 warnings`；warning 为既有日期解析 warning）。

```text
M2 Stage 2D-F: PASS
ROA transparent metric: TRUSTED
ROE/ROA capital-return layer: COMPLETE
ROIC: NOT YET
Scoring: STILL NOT YET
Next-stage selection: NORTH-STAR REVIEW REQUIRED
```

## 方法与输入

- 唯一新增定义：`return_on_average_total_assets`，version `1`，unit `ratio`，
  `input_roles=(numerator, opening, closing)`，`score_eligible=false`。
- 公式：`net_profit / ((opening_total_assets + closing_total_assets) / 2)`。
- 分子是经 Rule 005 对账的合并 `net_profit` duration Fact；分母是相邻
  12-31、CAS、consolidated、万元、`reconciled_derived` 且 eligible 的
  `total_assets` instant Facts。
- 2020 `comparison_only_opening_baseline` 仅作为 FY2021 opening；不产生 FY2020 ROA。
- 平均值由 Metric Engine 以 Decimal `prec=28`、`ROUND_HALF_EVEN` 计算并量化 `1e-12`；
  不生成平均余额 Fact。`available_at=max(三输入)`。
- 零平均资产为 `undefined_zero_denominator`，负平均资产为
  `not_comparable_negative_denominator`，任一输入缺失为 `missing_input`。

## 计算验收

生产代码不嵌入验收数值；测试从 Stage 2D-E run-scoped DuckDB 的 Fact 重新计算并比较。

| FY | latest ROA |
|---:|---:|
| 2021 | 0.045958140492 |
| 2022 | 0.063149706787 |
| 2023 | 0.066506160423 |
| 2024 | 0.066668674318 |
| 2025 | 0.061639226063 |

过渡版本也由 Fact 计算验证：FY2022 v1=`0.063357033733`、FY2023 v1=`0.066486631205`。

两条真实重列链为：

- FY2022：v1 `2023-03-30` → v2 `2024-03-26`；
- FY2023：v1 `2024-03-26` → v2 `2025-03-31`，opening 直接使用 2022 assets v2；
- FY2024 首次生成直接使用 2023 assets v2；unchanged 年度无假版本；
- FY2025 `revision_review_status=not_yet_reviewable`。

ROA 自身计数：`definition=1`、`result_versions=7`、`computed=7`、`links=2`、
`lineage=21`、`final_latest=5`。

组合计数：`definitions=12`、`results=77`、`computed=73`、`insufficient=4`、
`links=17`、`lineage=164`、`final_latest=60`、`final_computed=56`。

Metric PIT（day-before-first + 五个年报可用日）：

- latest：`0/12/24/36/48/60`；
- computed：`0/8/20/32/44/56`；
- insufficient：`0/4/4/4/4/4`。

## 不变性与边界

- Stage 2D-E foundation：201 Fact、67 reconciled eligible、PIT 52、45 Fact links；
- Stage 2D-D：既有 70 Metric Result、63 旧 Result ID/语义、7 个 ROE 版本均保持不变；
- Rule 001—005、Stage 2D-B/C/D/E 事实/方法论产物、默认数据库和 stash 保持不变；
- Stage 2D-C 方法论 JSON 未修改；ROE 定义的 ID、文本和顺序语义保留；
- runner 只访问临时 run-scoped foundation，未访问网络、PDF、shared cache 或默认 DB；
- 未生成 ROIC、评分、投资建议或平均余额 Fact；输出只包含定义、结果、PIT、transitions、
  lineage、manifest、summary 和 run-scoped `metrics.duckdb`。

## 工程验证

`tests/test_official_roa_metric_extension.py` 覆盖定义合同、非归母分子禁令、三角色与 lineage、
零/负平均资产、缺失输入、canonical ID、真实重列链、FY2024 opening、FY2025 状态、
幂等重跑、旧结果/201 Fact/无 ROIC 或 score 输出。targeted runner tests 已通过；最终门禁结果记录于
Stage 2D-F 工作记录。
