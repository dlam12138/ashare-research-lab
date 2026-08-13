# M2 Stage 2B-B：中国石油现金流指标扩展正式验收报告

## 验收结论

> **M2 Stage 2B-B：PASS**
>
> **Cash-based free cash flow proxy metrics：TRUSTED**
>
> **Additional fact coverage：ALLOWED**
>
> **Scoring：NOT YET**

- Branch：`feat/m2-value-assessment-mvp`
- 起始提交：`a07c0d0b34062e28693f9edd66785e78ed4eabbd`
- 最终真实 run：
  `cashflow_metric_extension_601857_SH_2021_2025_20260730_135559_837294`
- Fact Schema：`2.1`
- Metric Schema / Definition Schema：`1.0 / 1.0`
- upstream facts / final Fact PIT / eligible versions：`75 / 20 / 25`
- transaction committed：`true`

## 两个新定义

两个定义位于独立 `CashFlowMetricDefinitionRegistry`。Stage 2A 的
`MetricDefinitionRegistry` 仍只包含原四项；新工具显式组合两个 registry，
最终定义数为六。

| Metric ID | 中文名称 | Version | Formula | Input roles | Unit |
|---|---|---:|---|---|---|
| `cash_based_free_cash_flow_proxy` | 现金口径自由现金流代理 | 1 | `operating_cash_flow - cash_paid_for_fixed_assets` | `operating_cash_flow` / `cash_paid_for_fixed_assets` | 万元 |
| `cash_paid_for_fixed_assets_to_revenue` | 购建长期资产现金支出/营业收入比率 | 1 | `cash_paid_for_fixed_assets / revenue` | `cash_paid_for_fixed_assets` / `revenue` | ratio |

计算使用 Decimal precision 28、`ROUND_HALF_EVEN` 和
`0.000000000001` quantum，不使用 float 计算、容差或显示字符串反算。
代理值允许为负；收入为零时状态为 `undefined_zero_denominator`，收入为负
时为 `not_comparable_negative_revenue`。既有
`not_comparable_non_positive_profit` 语义未改变。

### 代理指标语义限制

`cash_based_free_cash_flow_proxy` 只表示：

> 经营活动产生的现金流量净额
>
> 减去
>
> 购建固定资产、油气资产、无形资产和其他长期资产支付的现金

它不是完整自由现金流、FCFF、FCFE、所有者收益或经济资本开支模型。
`cash_paid_for_fixed_assets_to_revenue` 也只表示该特定长期资产购建现金
支出相对营业收入的比例，不无条件等同于完整资本开支强度。

## 2021—2025 最新值与完整输入

### 现金口径自由现金流代理

| 年度 | Value（万元） | Metric Result ID | Input Fact IDs |
|---:|---:|---|---|
| 2021 | 7,590,600.000000000000 | `bc3c6e2f5a71406b2269c85e33c9c2869a92cca61a25282ad30431b899eedef8` | OCF `932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2`<br>cash paid `8fc1ab550cae3ec8ad73de2a0328dcc730bb76ee9d1abe89c04eeb884b8cb0dd` |
| 2022 | 15,001,600.000000000000 | `14183943deb3dde3adcdd95673df5b5261b47b7a482126f70275cb7a0e88a0a5` | OCF `e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d`<br>cash paid `3ca12114806d0fc07bedfa0e78ee5c9b8c086d7d377aa27c2dfdb1d998bbd0e9` |
| 2023 | 17,433,900.000000000000 | `d77940b3b944eed7f7ab408abc4b60b0fcdf8abdd357fa369991a0d3914df4ae` | OCF v2 `109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`<br>cash paid v2 `b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510` |
| 2024 | 10,388,100.000000000000 | `e11e064a81b54fe510f82dd6de3d768732013e04ac64654e1ac25a3bf322ae7c` | OCF `3356c5c1cb02b386d2d6d0720c81109f13191aad4d453ead86553267ab3c2e43`<br>cash paid `c1f4119d6a60dd2e7d093e0d7f33c56603dcea3ea6cd3f9ea32bef6dc342db21` |
| 2025 | 11,972,100.000000000000 | `48c1ff6ceb5ad8906c78d41fa05ec12436fe2e5cbd516854d176b73141ff5483` | OCF `ad3b6e2a3675ce7e8a8e16bda427597b72d28e30808281e17cd4aa549949357a`<br>cash paid `5dc4c375138e6cac5a26866d2120fc9d6bc68b69a19dabd56902ae0a6660b34f` |

### 购建长期资产现金支出/营业收入比率

| 年度 | Value | Metric Result ID | Input Fact IDs |
|---:|---:|---|---|
| 2021 | 0.101579016421 | `a421c21dc191c6d863cfeaa162096928c623f83ed0174268e22ac6a2cb3585bb` | cash paid `8fc1ab550cae3ec8ad73de2a0328dcc730bb76ee9d1abe89c04eeb884b8cb0dd`<br>revenue `1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6` |
| 2022 | 0.075251445819 | `5d4be733ecd99d1d8f54e6bdb98f7295ad4f67cb8bc8213a30c6d5b0affe5bdc` | cash paid `3ca12114806d0fc07bedfa0e78ee5c9b8c086d7d377aa27c2dfdb1d998bbd0e9`<br>revenue `62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43` |
| 2023 | 0.093768877713 | `bed174da6a448f2bb253f8eaac75287fc1931f236604e08d72051e74d4e0c7a3` | cash paid v2 `b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510`<br>revenue v2 `1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8` |
| 2024 | 0.103013259786 | `a8a6fd4ec2e0418210b5d86db71c1d483935ac95c528c7ac11103d89828b74a8` | cash paid `c1f4119d6a60dd2e7d093e0d7f33c56603dcea3ea6cd3f9ea32bef6dc342db21`<br>revenue `edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196` |
| 2025 | 0.102214057824 | `17f3e14a51779d206185983b491c3cb3421f9c650e140f0cf98b7bc24a583997` | cash paid `5dc4c375138e6cac5a26866d2120fc9d6bc68b69a19dabd56902ae0a6660b34f`<br>revenue `460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1` |

2025 两个结果的 `revision_review_status` 均为
`not_yet_reviewable`。

## 2023 两条版本链

### 现金口径自由现金流代理

- v1 ID：
  `bbf634d18a6f5eefc70643e54d48cdc69370a05ec8f170ce3080ac5557c5e7b3`
- v1 value：`17407700.000000000000`
- v1 inputs：
  `7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289`
  与
  `5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55`
- v2 ID：
  `d77940b3b944eed7f7ab408abc4b60b0fcdf8abdd357fa369991a0d3914df4ae`
- v2 value：`17433900.000000000000`
- v2 inputs：
  `109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`
  与
  `b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510`

### 购建长期资产现金支出/营业收入比率

- v1 ID：
  `48e9da039b775136e3170cf53088c2cd89aeba0d4b4a5c26bea3268c8c255ca3`
- v1 value：`0.093828586535`
- v1 inputs：
  `5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55`
  与
  `9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7`
- v2 ID：
  `bed174da6a448f2bb253f8eaac75287fc1931f236604e08d72051e74d4e0c7a3`
- v2 value：`0.093768877713`
- v2 inputs：
  `b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510`
  与
  `1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8`

两个 v2 均为 result version 2，严格 supersede 对应 v1。2025-03-30 的
Metric PIT 仍返回 v1，2025-03-31 才切换到 v2。2021、2022、2024、
2025 没有为两个新指标创建额外版本。

## 六指标计数与 Metric PIT

| 项目 | 实际 |
|---|---:|
| Metric definitions | 6 |
| Metric result versions | 38 |
| Computed result versions | 35 |
| Insufficient-history result versions | 3 |
| Metric result version links | 8 |
| Metric lineage rows | 73 |
| Final latest metrics | 30 |
| Final latest computed | 27 |
| Final latest insufficient history | 3 |

| Snapshot | Latest | Computed | Insufficient history |
|---:|---:|---:|---:|
| 2022-03-31 | 0 | 0 | 0 |
| 2022-04-01 | 6 | 3 | 3 |
| 2023-03-30 | 12 | 9 | 3 |
| 2024-03-26 | 18 | 15 | 3 |
| 2025-03-31 | 24 | 21 | 3 |
| 2026-03-30 | 30 | 27 | 3 |

全部 lineage 输入均来自 eligible `reconciled_derived` facts；没有使用
company/exchange raw facts。Metric `available_at` 取实际输入的最晚
available_at，没有公告日前泄漏。

## 不变性与只读证据

- Stage 2A 原四指标结果版本恰好 26；ID 集合摘要保持
  `671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf`。
  所有 value、status、input Fact IDs 与六条原版本链均未改变。
- Stage 2B-A 75 个 Fact ID 集合摘要保持
  `7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1`；
  最终 Fact PIT 仍为 20。
- upstream DuckDB 读取前后 SHA-256 均为
  `24e4b142a39c04ba02e59016e0a7990a1a7f57ae4ed16d95765351dd97bdc6e3`。
- Stage 2A runner / 报告、Stage 2B-A runner / evidence / 报告、
  annual bundles 和全部 restatement evidence 的冻结 blob 均未改变。
- 默认 `data/research.duckdb` SHA-256 保持
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- `network_access = false`、`pdf_access = false`、
  `cache_access = false`、`downloaded = 0`。

## 仍缺失的事实覆盖

- 扣非净利润
- 毛利率和一般净利率
- 非经常性损益
- ROE / ROA / ROIC
- 财务安全
- 分红与回购
- 估值

本阶段没有 score 表、评分、阈值、评级、颜色等级或投资建议。单独的代理
值或现金支出/收入比率不能机械解释为企业质量、估值或买卖结论。

## 最终状态

```text
M2 Stage 2B-B: PASS
Cash-based free cash flow proxy metrics: TRUSTED
Additional fact coverage: ALLOWED
Scoring: NOT YET
```
