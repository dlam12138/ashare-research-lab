# M2 Stage 2C-D 工作记录

## 冻结基线

- branch：`feat/m2-value-assessment-mvp`
- start：`e89b8020cb9e28c6132714c4caf80d5e9c625a08`
- facts / eligible / Fact PIT：`132 / 44 / 35`
- existing definitions / results：`6 / 38`
- existing result ID digest：
  `730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`
- default database SHA-256：
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`
- stash：`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`

## 设计审查

Metric Schema 与 Definition Schema 1.0 足够。现有 Engine 已支持同比、一般除法、
现金流减法和资本开支/收入；本阶段只需三个显式公式分支。新定义保留在独立
Registry，旧六个定义、Identity、Repository 与 Schema 不变。

本阶段只使用 PIT 可得的 eligible reconciled facts，不创建 Financial Fact，
不访问网络/PDF/cache，不计算 ROE/ROA/ROIC、估值或评分。

## 状态

集成试运行 `stage2cd_trial` 已通过：

- upstream facts / eligible / Fact PIT / Fact links：`132 / 44 / 35 / 27`
- definitions / result versions：`10 / 63`
- computed / insufficient / links / lineage：`59 / 4 / 13 / 122`
- final latest / computed / insufficient：`50 / 46 / 4`
- 新指标 versions / links / lineage：`25 / 5 / 49`
- Metric PIT：`0/10/20/30/40/50`
- 原 38 Metric Result ID digest 不变
- 原 132 Fact ID digest 不变
- upstream DuckDB 前后哈希一致
- 默认数据库哈希不变

## 正式验收与门禁

- run_id：
  `earnings_quality_metric_extension_601857_SH_2021_2025_20260730_172000`
- result：`PASS`
- upstream facts / eligible / Fact PIT / Fact links：`132 / 44 / 35 / 27`
- definitions / results / computed / insufficient：`10 / 63 / 59 / 4`
- links / lineage / final latest：`13 / 122 / 50`
- Metric PIT latest：`0 / 10 / 20 / 30 / 40 / 50`
- Metric PIT computed：`0 / 6 / 16 / 26 / 36 / 46`
- Metric PIT insufficient：`0 / 4 / 4 / 4 / 4 / 4`
- 原 38 Metric Result ID digest：
  `730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`
- 原 38 Result 完整语义 digest：
  `f665e33775c40a1b8e092c1345978f5f8fd5650cec90c5a87a931dfba2726890`
- upstream DuckDB 前后 hash：一致
- 默认数据库 hash：不变

首次全量门禁捕获到 Stage 2C-A 的冻结 blob 断言仍指向扩展前
`MetricEngine`。本阶段明确批准了三个新公式分支；旧公式的 38 个 Result 完整
语义 digest 与回归测试均保持不变，因此只更新冻结断言到批准后的 Engine blob，
并同步更新其上层保护测试的 blob。没有修改旧 Definition、Identity、Repository
或 Schema，也没有放宽数值、PIT 或身份断言。

门禁结果：

- Ruff `0.13.2`：通过
- compileall / imports：通过
- targeted pytest：`91 passed`
- full pytest：`678 passed, 2 warnings`
- `git diff --check`：通过
- network / PDF / cache：均未访问
- scoring / investment advice：均未产生

最终状态：`M2 Stage 2C-D: PASS`。
