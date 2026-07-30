# M2 Stage 2C-D：中国石油盈利质量透明指标扩展

## 结论

**PASS。** 本阶段在冻结的 132 个 Financial Fact 上新增四个透明、非评分 Metric，
没有新增或修改 Fact、Reconciliation Rule、Metric Schema、旧 Definition 或旧
Metric Result。

- run_id：`earnings_quality_metric_extension_601857_SH_2021_2025_20260730_172000`
- contract：`earnings_quality_metric_extension_v1`
- offline / network / PDF / cache：`true / false / false / false`
- downloaded：`0`
- scoring：`not_implemented`
- investment advice：`not_produced`

## 四个 Definition

| Metric | 中文名称 | 公式 | 单位 |
|---|---|---|---|
| net_profit_excluding_non_recurring_yoy | 扣非归母净利润同比 | `(current / prior) - 1` | ratio |
| gross_profit | 毛利润（营业收入减营业成本） | `revenue - operating_cost` | 万元 |
| gross_margin | 毛利率 | `(revenue - operating_cost) / revenue` | ratio |
| operating_profit_margin | 营业利润率 | `operating_profit / revenue` | ratio |

全部为 Definition Schema 1.0、version 1、Decimal precision 28、
quantum `0.000000000001`、`ROUND_HALF_EVEN`、`score_eligible=false`。
方法论依据包括 CFA FSA/Reporting Quality、财政部企业会计准则和 Penman。
指标必须结合多年趋势、周期与行业背景，单年变化不能评价企业好坏。

## 五年最新值

| 年度 | 扣非归母净利润同比 | 毛利润（万元） | 毛利率 | 营业利润率 |
|---:|---:|---:|---:|---:|
| 2021 | insufficient_history | 54284500.000000000000 | 0.207640601924 | 0.069684651896 |
| 2022 | 0.710622821031 | 71123200.000000000000 | 0.219572501202 | 0.074884684859 |
| 2023 | 0.100604957124 | 70980700.000000000000 | 0.235596180578 | 0.084147965422 |
| 2024 | -0.075255217756 | 66275800.000000000000 | 0.225582806696 | 0.086891644296 |
| 2025 | -0.067033303133 | 61834800.000000000000 | 0.215868281346 | 0.081892664923 |

2025 四项均为 `not_yet_reviewable`。2021 同比缺少 2020 官方事实，保持
`insufficient_history`，没有把缺失写成零。

## PIT 与重列传播

五条新版本链严格为：

1. 2022 扣非归母净利润同比：`0.717022837106 → 0.710622821031`，
   PIT 于 `2024-03-26` 切换；
2. 2023 扣非归母净利润同比：`0.099083754258 → 0.100604957124`，
   PIT 于 `2025-03-31` 切换；
3. 2023 毛利润：`70862700 → 70980700`，同日切换；
4. 2023 毛利率：`0.235345126489 → 0.235596180578`，同日切换；
5. 2023 营业利润率：`0.084032876654 → 0.084147965422`，同日切换。

所有链均为 result version 1→2，v2 指向 v1，输入 Fact ID 同步切换。2024
扣非同比第一次生成即使用 2023 reconciled v2 Fact
`9f2609b8f35229fe86048373b66236ce10a5e1c5eddc91588703dceab481d5c9`，
没有制造使用 2023 v1 的假版本，也不存在公告日前泄漏。

Metric PIT：

- latest：`0 / 10 / 20 / 30 / 40 / 50`
- computed：`0 / 6 / 16 / 26 / 36 / 46`
- insufficient history：`0 / 4 / 4 / 4 / 4 / 4`

## 固定计数与不变性

- 新 Definitions / results / computed / insufficient：`4 / 25 / 24 / 1`
- 新 links / lineage / final latest：`5 / 49 / 20`
- 总 Definitions / results / computed / insufficient：`10 / 63 / 59 / 4`
- 总 links / lineage / final latest：`13 / 122 / 50`
- final computed / insufficient：`46 / 4`

原 38 个 Metric Result 的 ID、value、status、input Fact ID 和 supersedes
保持不变；ID 集合 SHA-256：
`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`。
完整语义集合 SHA-256：
`f665e33775c40a1b8e092c1345978f5f8fd5650cec90c5a87a931dfba2726890`。

upstream facts / eligible / Fact PIT / Fact links：
`132 / 44 / 35 / 27`。132 Fact ID 集合 SHA-256：
`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`。

upstream DuckDB 前后 SHA-256 均为：
`092cef835804bf7fa3d5024b375669fcadbf56ceac5a51f88def8a2b86e464ea`。

默认 `data/research.duckdb` 前后 SHA-256 均为：
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。

## Gap inventory

已关闭：扣非归母净利润事实覆盖、毛利润、毛利率、营业利润率。

仍缺失且没有置零：非经常性损益独立 Fact、ROE/ROA/ROIC、财务安全、
分红与回购、估值、治理与风险否决项、行业与同行基准。

## 工程门禁

- Ruff `0.13.2`、compileall、imports：通过
- targeted pytest：`91 passed`
- full pytest：`678 passed, 2 warnings`
- `git diff --check`：通过
- Stage 2A、Stage 2B-B、Stage 2C-C.1、Reconciliation regressions：通过
- Stage 2C-C.1 evidence / runner / report：blob 不变
- Stage 2C-A 方法论 v1.0：blob 不变
- output、PDF、PNG、DuckDB、`data/raw/official`：未进入 Git

盈利质量透明指标已经可信，但评分仍缺少跨周期历史、同行基准、资本回报、
财务安全及正式阈值/权重合同，因此 scoring readiness 仍为 blocked。本阶段没有
产生评分、企业好坏结论或投资建议。

## 全部新 Metric Result、输入与版本链

下表记录本阶段 25 个 Result version 的 ID、输入 Fact ID 和 supersedes。

| 年度 | Metric | v | status/value | Metric Result ID | input Fact IDs | supersedes |
|---:|---|---:|---|---|---|---|
| 2021 | gross_margin | 1 | 0.207640601924 | 01b002a5b641b1025dfcb1886c61cd273b786474f29a57632f786149bb1afd91 | 1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6<br>d5a4f5b08bc3f11b23764a97369540feffacd66ec5781b254fa723dbaf7dcd4a |  |
| 2021 | gross_profit | 1 | 54284500.000000000000 | 569419e0c11e57da4e8e7116e37e921ee93789f0dd5d0ce55b7cd539f637414b | 1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6<br>d5a4f5b08bc3f11b23764a97369540feffacd66ec5781b254fa723dbaf7dcd4a |  |
| 2021 | net_profit_excluding_non_recurring_yoy | 1 | insufficient_history | 2d9a332085930384393613c820897cd92ecd835aa66a3cd9d22ad489c15a0920 | e68bcc53b319bc8212045b96dd2fc9f11dbbbeeeebe112da2323ad75e9c6bb51 |  |
| 2021 | operating_profit_margin | 1 | 0.069684651896 | 4b27f4116cbbb2793a92240fc420b5ebd978337e6cc45ba43983ebd7ea6dc80c | 252fe65ca6d3f9fc14578fe9333eeeace10c51f43058fb4846d58b15306942f0<br>1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6 |  |
| 2022 | gross_margin | 1 | 0.219572501202 | d9ae6e7e7e02d2f492a804266d4e9dc1ebeac9ba990903d76a8a0d8dc2623fd4 | 62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43<br>584cd6073e7043e12b71c14ef692c4610447f442c58623a57b6fbc18494e8459 |  |
| 2022 | gross_profit | 1 | 71123200.000000000000 | 06a7927467d2cd2782dc9caae59eb32d51ce698b3f9c3dbc451f1adf3fd647c5 | 62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43<br>584cd6073e7043e12b71c14ef692c4610447f442c58623a57b6fbc18494e8459 |  |
| 2022 | net_profit_excluding_non_recurring_yoy | 1 | 0.717022837106 | 69c8c5b1787a319e0d9e6cb537cbf7e2e44586ea17bdbb0cc08f8b2f38c996f4 | eedb8d79f49b41b09e2a12ee0a0829f6a718dbc61c5951fbc7a4e6abfb4559c6<br>e68bcc53b319bc8212045b96dd2fc9f11dbbbeeeebe112da2323ad75e9c6bb51 |  |
| 2022 | operating_profit_margin | 1 | 0.074884684859 | 8199c4378cd4f788126683fe3b63c1c040f61839126743b777943cd9f7690dec | 707e35066ae15b6558a8f59c470bebf01f10820829553133543945e8ee992974<br>62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43 |  |
| 2022 | net_profit_excluding_non_recurring_yoy | 2 | 0.710622821031 | ef93109b8c546ac3c74226d9a19616bd2037c9b0cd7d16821ff79bade0ef2c2e | 26b44e1d6f26ba1c55aa491e14428729a43e5853a3e1457af70b6cc5bdf06e77<br>e68bcc53b319bc8212045b96dd2fc9f11dbbbeeeebe112da2323ad75e9c6bb51 | 69c8c5b1787a319e0d9e6cb537cbf7e2e44586ea17bdbb0cc08f8b2f38c996f4 |
| 2023 | gross_margin | 1 | 0.235345126489 | 608af950c36404906d5898dcbb60598ee89482f6352bd7fcd6dcf9fa129eba74 | 9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7<br>1023ed94b6a7230f239bca84632e58c14fc0a9bb8f9851c276638d98f0828c14 |  |
| 2023 | gross_profit | 1 | 70862700.000000000000 | 98b2d85432e69fa26c17e80c6aa06c53ad86a0fcf13441c7f293386237f76d52 | 9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7<br>1023ed94b6a7230f239bca84632e58c14fc0a9bb8f9851c276638d98f0828c14 |  |
| 2023 | net_profit_excluding_non_recurring_yoy | 1 | 0.099083754258 | 3e7a28073bf7407719f1251938e83440a8d38750a1749c42ba41b9155cd99373 | 8ef5a9f44891e977d06b5cc6a37aa537c6cffe8bd08d71d8e552cf14b8c8bff8<br>26b44e1d6f26ba1c55aa491e14428729a43e5853a3e1457af70b6cc5bdf06e77 |  |
| 2023 | operating_profit_margin | 1 | 0.084032876654 | caa6181c9ed2a9455817cbcf3ee293b3f09f9520f623600175c7c79cde5f55a5 | bd07502f296ce6f80bcbffee8e35b3b56b0833d08baf098e43a345edd614a252<br>9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7 |  |
| 2023 | gross_margin | 2 | 0.235596180578 | 775be2a1f4016444ab70920e4b998083398851dffdc2be5cfcbc0f2b06d058c5 | 1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8<br>66a584865ba4be80644644fc2e26cd41cfdf8d34385102d48b3ee261e9e49409 | 608af950c36404906d5898dcbb60598ee89482f6352bd7fcd6dcf9fa129eba74 |
| 2023 | gross_profit | 2 | 70980700.000000000000 | c10946c0c6af15f0f96595e61f9e27fae1c4772e09d2790ac02e69ba9d9d0880 | 1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8<br>66a584865ba4be80644644fc2e26cd41cfdf8d34385102d48b3ee261e9e49409 | 98b2d85432e69fa26c17e80c6aa06c53ad86a0fcf13441c7f293386237f76d52 |
| 2023 | net_profit_excluding_non_recurring_yoy | 2 | 0.100604957124 | 342baf16483867e8ac1d9c6637701d88e7708d80f43b8c0f28c975edebdfda39 | 9f2609b8f35229fe86048373b66236ce10a5e1c5eddc91588703dceab481d5c9<br>26b44e1d6f26ba1c55aa491e14428729a43e5853a3e1457af70b6cc5bdf06e77 | 3e7a28073bf7407719f1251938e83440a8d38750a1749c42ba41b9155cd99373 |
| 2023 | operating_profit_margin | 2 | 0.084147965422 | dd2f0304a7d3da8a3de21dc9c9c62714fef7c5b334f41fc95bce7f88df0ae2f6 | b2b38471ceb24e6225c8e0fa91e8fa7585ec5d4104596d913bc91900f7034e4a<br>1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8 | caa6181c9ed2a9455817cbcf3ee293b3f09f9520f623600175c7c79cde5f55a5 |
| 2024 | gross_margin | 1 | 0.225582806696 | fe350fdb6325c89b17f521462b1f3a411cfc213e3db32d2f67e779ef97cdefa3 | edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196<br>244f0f5ff7d60542c5f070d6085afda52cf07229d00a5aa411425a5df76a448d |  |
| 2024 | gross_profit | 1 | 66275800.000000000000 | 4712c97a9833b480279e33b6f57c5c23cd740488dcedbbeadc6be9adb45b7f7e | edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196<br>244f0f5ff7d60542c5f070d6085afda52cf07229d00a5aa411425a5df76a448d |  |
| 2024 | net_profit_excluding_non_recurring_yoy | 1 | -0.075255217756 | 623ddb3f3c8f456ccdccbd4cbdf57d0f10fb2d185ac13304b607b0c0632e8ee1 | 7e45367d9ee46515ba1ac054d7fd0b6654f75a13ffb20c31ce6136353507a824<br>9f2609b8f35229fe86048373b66236ce10a5e1c5eddc91588703dceab481d5c9 |  |
| 2024 | operating_profit_margin | 1 | 0.086891644296 | 6854648280e0c4a93858133f96c0ac8b617dcdc0e44af4dc76850c73ee2cd825 | 53fc036f99690397a46995970845868c8b4ad53a9321d7656edd025aacd6123f<br>edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196 |  |
| 2025 | gross_margin | 1 | 0.215868281346 | f6d5eb30675336dcc7b598f19bf68bbfb20b4df82264c0f25ecb5a452c819951 | 460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1<br>be615c237d0c328a531cc420fe1e7c9a96d7b748d07539ea3540c704f8f896a5 |  |
| 2025 | gross_profit | 1 | 61834800.000000000000 | 31083cf676e91abd13f2d42c6c4040c39d959330cbea0f291f52e02255792cfe | 460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1<br>be615c237d0c328a531cc420fe1e7c9a96d7b748d07539ea3540c704f8f896a5 |  |
| 2025 | net_profit_excluding_non_recurring_yoy | 1 | -0.067033303133 | 278b78a536290ebf892087f4d0e386a0208ca38d0f028eb93b889636c5cdd3bb | 06f703c7e956f3d78e341be57478b9a9c1c67214f1da942645f77d8f41dc8077<br>7e45367d9ee46515ba1ac054d7fd0b6654f75a13ffb20c31ce6136353507a824 |  |
| 2025 | operating_profit_margin | 1 | 0.081892664923 | c4eeed3ce046243856efe3cc18f1dc1214909947465c0073e6bccfc28a0de0c7 | 2a98f29f9c371c6d52fed66efdcd9bb5a0bf6acec95752d699cfea135c3b469c<br>460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1 |  |

## 最终状态

```text
M2 Stage 2C-D: PASS
Earnings-quality transparent metrics: TRUSTED
ROE / ROA fact foundation: ALLOWED
Scoring: STILL NOT YET
```
