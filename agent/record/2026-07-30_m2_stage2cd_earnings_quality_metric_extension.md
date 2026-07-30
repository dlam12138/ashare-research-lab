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

最终正式 run 与全量门禁将在文档定稿提交中记录。
