# M2 Stage 2A：中国石油最小透明指标底座正式验收报告

## 验收结论

> **M2 Stage 2A：PASS**
>
> **Minimal transparent metrics：TRUSTED**
>
> **Additional fact coverage：ALLOWED**
>
> **Scoring：NOT YET**

- Branch：`feat/m2-value-assessment-mvp`
- 起始提交：`5b79028e6cbfff2c9540dd852aa75b0b084ce4c2`
- 最终真实 run：
  `metric_foundation_601857_SH_2021_2025_20260730_120052_376281`
- Metric Schema：`1.0`
- Metric Definition Schema：`1.0`
- upstream Stage 1D-B：`passed`
- upstream facts / final Fact PIT：`57 / 15`
- transaction committed：`true`

本阶段只建立盈利与现金流的四个透明 ratio 指标。经营现金流/归母净利润
比率只是当前三项可信事实能够支持的现金利润质量代理指标，不等同于完整的
现金利润质量评价。

## 四个版本化定义

| Metric ID | 中文名称 | Definition version | Canonical formula | Unit |
|---|---|---:|---|---|
| `revenue_yoy` | 营业收入同比 | 1 | `(current / prior) - 1` | ratio |
| `net_profit_attributable_to_parent_yoy` | 归属于母公司股东的净利润同比 | 1 | `(current / prior) - 1` | ratio |
| `operating_cash_flow_yoy` | 经营活动产生的现金流量净额同比 | 1 | `(current / prior) - 1` | ratio |
| `operating_cash_flow_to_attributable_net_profit` | 经营现金流/归母净利润比率 | 1 | `numerator / denominator` | ratio |

计算使用 Decimal precision 28、量化 `0.000000000001`、
`ROUND_HALF_EVEN`。DuckDB value 为 `DECIMAL(38,12)`，JSON value 为
字符串；没有使用 float 完成除法，也没有从百分比显示值反算。

## 2021—2025 最新指标

表中 value 为 canonical ratio。同比的百分比显示可由 ratio × 100 得到，
但未作为 canonical value 存储。

| 年度 | Metric | Value | Status | Available at | Input Fact IDs |
|---:|---|---:|---|---:|---|
| 2021 | `revenue_yoy` | null | `insufficient_history` | 2022-04-01 | `1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6` |
| 2021 | `net_profit_attributable_to_parent_yoy` | null | `insufficient_history` | 2022-04-01 | `00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` |
| 2021 | `operating_cash_flow_yoy` | null | `insufficient_history` | 2022-04-01 | `932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2` |
| 2021 | `operating_cash_flow_to_attributable_net_profit` | 3.705135577956 | `computed` | 2022-04-01 | `932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2`<br>`00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` |
| 2022 | `revenue_yoy` | 0.238995635242 | `computed` | 2023-03-30 | `62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43`<br>`1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6` |
| 2022 | `net_profit_attributable_to_parent_yoy` | 0.613893078417 | `computed` | 2024-03-26 | `fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534`<br>`00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` |
| 2022 | `operating_cash_flow_yoy` | 0.153158851902 | `computed` | 2023-03-30 | `e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d`<br>`932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2` |
| 2022 | `operating_cash_flow_to_attributable_net_profit` | 2.647393403165 | `computed` | 2024-03-26 | `e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d`<br>`fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534` |
| 2023 | `revenue_yoy` | -0.069880620542 | `computed` | 2025-03-31 | `1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8`<br>`62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43` |
| 2023 | `net_profit_attributable_to_parent_yoy` | 0.085223681910 | `computed` | 2025-03-31 | `0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129`<br>`fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534` |
| 2023 | `operating_cash_flow_yoy` | 0.160193311798 | `computed` | 2025-03-31 | `109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`<br>`e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d` |
| 2023 | `operating_cash_flow_to_attributable_net_profit` | 2.830281140422 | `computed` | 2025-03-31 | `109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`<br>`0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129` |
| 2024 | `revenue_yoy` | -0.024837593584 | `computed` | 2025-03-31 | `edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196`<br>`1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8` |
| 2024 | `net_profit_attributable_to_parent_yoy` | 0.020208903813 | `computed` | 2025-03-31 | `d082020ffd54095ac923e545c0c540449a7b8a3b7b1c78872b184423b9af065f`<br>`0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129` |
| 2024 | `operating_cash_flow_yoy` | -0.110135340716 | `computed` | 2025-03-31 | `3356c5c1cb02b386d2d6d0720c81109f13191aad4d453ead86553267ab3c2e43`<br>`109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4` |
| 2024 | `operating_cash_flow_to_attributable_net_profit` | 2.468677888703 | `computed` | 2025-03-31 | `3356c5c1cb02b386d2d6d0720c81109f13191aad4d453ead86553267ab3c2e43`<br>`d082020ffd54095ac923e545c0c540449a7b8a3b7b1c78872b184423b9af065f` |
| 2025 | `revenue_yoy` | -0.025021264603 | `computed` | 2026-03-30 | `460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1`<br>`edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196` |
| 2025 | `net_profit_attributable_to_parent_yoy` | -0.044778838446 | `computed` | 2026-03-30 | `9009dbb2ddaf6981e33d68fafd2cce681c0c87e591d30a1fa366d0051b38df6c`<br>`d082020ffd54095ac923e545c0c540449a7b8a3b7b1c78872b184423b9af065f` |
| 2025 | `operating_cash_flow_yoy` | 0.014704869481 | `computed` | 2026-03-30 | `ad3b6e2a3675ce7e8a8e16bda427597b72d28e30808281e17cd4aa549949357a`<br>`3356c5c1cb02b386d2d6d0720c81109f13191aad4d453ead86553267ab3c2e43` |
| 2025 | `operating_cash_flow_to_attributable_net_profit` | 2.622407852411 | `computed` | 2026-03-30 | `ad3b6e2a3675ce7e8a8e16bda427597b72d28e30808281e17cd4aa549949357a`<br>`9009dbb2ddaf6981e33d68fafd2cce681c0c87e591d30a1fa366d0051b38df6c` |

2021 三个 YoY 的缺失说明均明确记录 2020 prior；value 为 null，不是零。
2025 四个结果均为 `revision_review_status = not_yet_reviewable`，仍可基于
当前 original facts 计算，但可能被下一年度报告修订。

## 六条 Metric Result 版本链

| 年度 / Metric | v1 ID / value / inputs | v2 ID / value / inputs |
|---|---|---|
| 2022 NP YoY | `1f7a11f22c0ad04e36c41625bc6ced02a01994fc878f8558d5bb0abf5550c4c9`<br>0.620804895780<br>`d3f70991ddb193324747fd7673274da61d56ffbfbac9a8a813ef3a1467072603`<br>`00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` | `12f4c0ee03b03065424e1be87c931fbb4209ba000595d53360c42f7df4f29b3a`<br>0.613893078417<br>`fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534`<br>`00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` |
| 2022 OCF/NP | `22d0b1ab9ab096671b0719591f8ec7666d5c9308aa453a442851976b87fa4491`<br>2.636103765690<br>`e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d`<br>`d3f70991ddb193324747fd7673274da61d56ffbfbac9a8a813ef3a1467072603` | `ca89d9b6bb2bd0ff53bf540045df504fa8663b49d8e884ec6cdbe34b4fe78a88`<br>2.647393403165<br>`e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d`<br>`fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534` |
| 2023 revenue YoY | `2d7884e7b16fa153dd03c6860f05c0e9c4257d1341d512f493985688f20ddff3`<br>-0.070436318967<br>`9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7`<br>`62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43` | `98b6a63aa04a019035d0242dfbfe2f33658abba60c5d4737a92a7aafcd32d1a7`<br>-0.069880620542<br>`1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8`<br>`62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43` |
| 2023 NP YoY | `e8f74e1de986062013b5404149607bc64b8b4b27b2715994380e3e618a01a3c8`<br>0.083408409418<br>`d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4`<br>`fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534` | `d9ec017203deab7fe048940820cb73eb64b94db4f4c0cf9bc59368a8229b8308`<br>0.085223681910<br>`0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129`<br>`fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534` |
| 2023 OCF YoY | `31b2d6c01e45ca9db730577d48c8b25fa1fc8c0f9d844582e93f0c6f6adc1ab8`<br>0.159555880620<br>`7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289`<br>`e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d` | `6901e59496073d337a65dd4ad9928f0d177fb7f370222b864053ea104c9b603a`<br>0.160193311798<br>`109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`<br>`e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d` |
| 2023 OCF/NP | `191d012b1bf8e574a7a995efce9efb9a5957583965131cc842aac51fbe385e73`<br>2.833465720101<br>`7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289`<br>`d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4` | `bf0052f8d7b1b8101aecf7b4179d0ea4aadd9a5b867d5c1efa245b700a7bbda4`<br>2.830281140422<br>`109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`<br>`0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129` |

2022 两条链在 2024-03-25 仍返回 v1，于 2024-03-26 切换到 v2。
2023 四条链在 2025-03-30 仍返回 v1，于 2025-03-31 切换到 v2。每个
v2 的 `supersedes_metric_result_id` 均指向表中对应 v1。

## 2024 prior 输入与 PIT

2024 三个 YoY 首次生成于 2025-03-31，并直接使用：

- revenue prior：
  `1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8`
  （2023 reconciled v2）
- NP prior：
  `0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129`
  （2023 reconciled v2）
- OCF prior：
  `109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`
  （2023 reconciled v2）

不存在引用 2023 v1 的 2024 Metric Result。

| Snapshot | Latest results | Computed | Insufficient history |
|---:|---:|---:|---:|
| 首个年度可用日前 | 0 | 0 | 0 |
| 2022-04-01 | 4 | 1 | 3 |
| 2023-03-30 | 8 | 5 | 3 |
| 2024-03-26 | 12 | 9 | 3 |
| 2025-03-31 | 16 | 13 | 3 |
| 2026-03-30 | 20 | 17 | 3 |

所有 Metric `available_at` 均等于实际输入 Fact 的最晚 available_at，没有
在公告日前暴露结果。

## Repository、Lineage 与动态计数

| 项目 | 实际 |
|---|---:|
| Metric definitions | 4 |
| Metric result versions | 26 |
| Computed result versions | 23 |
| Insufficient-history result versions | 3 |
| Metric version links | 6 |
| Metric lineage rows | 49 |
| Final latest results | 20 |
| Final latest computed | 17 |
| Final latest insufficient history | 3 |

YoY lineage 角色为 current/prior，比率角色为 numerator/denominator。2021 三个
YoY 只记录 current Fact lineage，并在结果中明确记录缺失的 2020 prior。
Repository 对同 ID 不同语义、断链、跨 Metric/年度 predecessor、非严格
版本递增和部分事务写入均有可证伪测试。

## 指标缺口

以下内容因事实覆盖尚不足而未支持，未写成零或“不适用”：

- 扣非净利润增长
- 毛利率与一般净利率
- 非经常性损益占比
- 自由现金流与资本开支强度
- ROE / ROA / ROIC
- 财务安全指标
- 分红、回购
- 估值指标

本阶段没有任何评分输出。中国石油属于周期性企业，单一同比或单一年份的
经营现金流/归母净利润比率不能机械解释为企业质量结论。

## 不变性与门禁

- upstream restatement DuckDB 读取前后 SHA-256：
  `156bc8e48b1a9d3cd2c53f58910e381029591dff10002f13f60eac577fefc3a2`
  / `156bc8e48b1a9d3cd2c53f58910e381029591dff10002f13f60eac577fefc3a2`。
- Stage 1D-B 基线与本 run 的 57 个 Fact ID 集合逐一相等；排序集合摘要：
  `e2afd5d39ae97f2488f5e9a713fda578174c38c5ea13e37d12e8844a8f29d829`。
- 五个 annual bundle、四个 restatement evidence、Stage 1D-A/1D-B
  工具与报告、Derivation 源码均未修改。
- 默认 `data/research.duckdb` SHA-256 保持：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- PDF、PNG、DuckDB、output、raw official artifact 未进入 Git；
  `stash@{0}` 未操作。
- Ruff 0.13.2、compileall、imports、Metric targeted、Stage 1D-B、
  multi-year、Reconciliation、full pytest 与 `git diff --check` 均通过。

## 最终状态

```text
M2 Stage 2A: PASS
Minimal transparent metrics: TRUSTED
Additional fact coverage: ALLOWED
Scoring: NOT YET
```
