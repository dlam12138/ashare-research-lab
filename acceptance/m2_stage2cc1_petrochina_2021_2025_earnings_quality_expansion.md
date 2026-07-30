# M2 Stage 2C-C.1：中国石油 2021—2025 盈利质量官方事实验收

## 结论

**PASS。** Stage 2C-C 初次执行曾因“公司侧扣非归母净利润必须来自公司官网简体 A 股完整年度报告”这一过度约束而 Fail；该历史结论保留。本次把稳定年度官方 `source_id`、实际承载事实的正式文档和每 Fact 页面证据分离，没有降低双官方路径、数值全等、PIT、版本链或 lineage 标准。

- run_id：`m2_stage2cc1_20260730_164500`
- Rule 003：`RECON_OFFICIAL_NUMERIC_003 v1`
- transaction committed：`true`
- runner offline；network / PDF / cache access：`false / false / false`
- 新 Metric：未计算；scoring：未实现

## 2021 文档范围纠正

公司侧以稳定来源身份 `company_ir:601857.SH:2021:annual:zh-cn` 绑定两份正式披露：

1. 《截至2021年12月31日止年度财务报表及审计报告》，`audited_financial_statements`，支持营业成本和营业利润；
2. 《二零二一年度业绩公告（年度报告摘要）》，`annual_results_announcement`，支持扣非归母净利润和桥接所需归母净利润。

上交所 2021 年完整年度报告支持三项事实及逐项桥。两条路径不是独立编制的数据来源，故 `independent_content_sources=false`。

公司直接披露差额 `92,161 - 99,531 = -7,370` 百万元；上交所直接差额和逐项、所得税、少数股东权益桥同为 `-7,370`。状态 `reconciled_cross_document`；公司逐项桥不可用且未伪造，交易所逐项桥可用。

## 五年事实与桥

单位均为人民币百万元，公司与交易所原值全等。

| 年度 | 扣非归母净利润 | 营业成本（绝对值） | 营业利润 | bridge |
|---:|---:|---:|---:|---|
| 2021 | 99,531 | 2,071,504 | 182,180 | reconciled_cross_document |
| 2022 | 170,897 | 2,527,935 | 242,564 | reconciled |
| 2023 | 187,130 | 2,302,385 | 253,024 | reconciled |
| 2024 | 173,287 | 2,275,223 | 255,286 | reconciled |
| 2025 | 161,671 | 2,246,121 | 234,579 | reconciled |

## 后续比较与版本链

- 2021 reviewed by 2022：三项 unchanged。
- 2022 reviewed by 2023：扣非归母净利润 `170,897 → 170,260` changed；其余 unchanged（Interpretation 16 / IAS 12 修订）。
- 2023 reviewed by 2024：扣非 `187,130 → 187,389`、营业成本 `2,302,385 → 2,303,005`、营业利润 `253,024 → 253,522` changed（同一控制下合并中国石油集团电能有限公司）。
- 2024 reviewed by 2025：三项 unchanged。
- 2025：`not_yet_reviewable`。

`R=4`。仅 changed Concept-Year 创建三角色 v2，均为 `fact_version=2`、`restatement_version=restated_1` 并连接 v1。完整 48 个本阶段新增 Fact ID 和全部 27 条版本链记录在正式 run 的 `run_manifest.json`。

## 计数、PIT 与不变性

- contexts / upstream facts：`5 / 84`
- new v1 / restatement facts：`36 / 12`
- financial facts：`132`
- company / exchange / reconciled：`44 / 44 / 44`
- raw ineligible / reconciled eligible：`88 / 44`
- version-chain links：`27`
- Audit / Lineage：`132 / 132`
- Rule 003 reconciliations / lineage：`19 / 57`
- annual cumulative PIT：`0 / 7 / 14 / 21 / 28 / 35`
- final PIT：`35`，每年恰好七个 Concept

原 84 Fact ID 逐 ID 保留，集合 SHA-256 `020835fc129658059f680a3a854aa59b3ace199704c6cd70c3815dca29e29b87`。原 38 个 Metric Result 未读取、未重算，冻结 ID 集合 SHA-256 `730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`。Rule 001 / 002 / 003 身份和语义未改。

默认数据库前后 SHA-256 均为 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。

## 缓存

已登记的 10 个年度来源注册均从共享缓存复核（8 个唯一 PDF）。2021 公司年度业绩公告首次缺失，只下载一次并原子写入缓存。

- annual registrations cache_hit：10
- unique annual PDFs hash_verified：8
- announcement cache_miss / downloaded / hash_verified：`1 / 1 / 1`
- populated_from_existing_local：0
- announcement SHA-256：`555a24ed0ace306ebb249faefd2d131e960cd008ad22df8929993c40183e4786`
- content_length / page_count：`1,195,800 / 44`

## 本阶段全部新增 Fact ID 与 supersedes

| 年度 | Concept | role | v | fact_id | supersedes_fact_id |
|---:|---|---|---:|---|---|
| 2021 | net_profit_excluding_non_recurring | company_official | 1 | 3f441070049fbf5b9ee61397ae04867a3e87216eff847b6890e517b36d15f7e0 |  |
| 2021 | net_profit_excluding_non_recurring | exchange_official | 1 | 0f595395fc341a6d1c8e959a5644fe762015320fb5c98da3dbe3d3df82316c1a |  |
| 2021 | net_profit_excluding_non_recurring | reconciled_derived | 1 | e68bcc53b319bc8212045b96dd2fc9f11dbbbeeeebe112da2323ad75e9c6bb51 |  |
| 2021 | operating_cost | company_official | 1 | 1ce3e4328cec1b4426774c7a9235aa76c2bd598d1f4045d6dd9e77ce6fac97ae |  |
| 2021 | operating_cost | exchange_official | 1 | 4115267bb98f22446d78c8054d6beb8ab6f50921358f07d7789c66c29889f480 |  |
| 2021 | operating_cost | reconciled_derived | 1 | d5a4f5b08bc3f11b23764a97369540feffacd66ec5781b254fa723dbaf7dcd4a |  |
| 2021 | operating_profit | company_official | 1 | ec6acee844894ce9571a4ff4e381a4530e0d5a0986f44356bf8c5385126f474c |  |
| 2021 | operating_profit | exchange_official | 1 | 77304cbce61bec9a449e372127e5cb936d28adcc984f256c408a997b3c34ddf4 |  |
| 2021 | operating_profit | reconciled_derived | 1 | 252fe65ca6d3f9fc14578fe9333eeeace10c51f43058fb4846d58b15306942f0 |  |
| 2022 | net_profit_excluding_non_recurring | company_official | 1 | c8996e6517c35783ff00ea0e4ccd15901dd5b35872c5c7f6954e0b46c57e15c0 |  |
| 2022 | net_profit_excluding_non_recurring | company_official | 2 | e9b7c9e567c42670ea361c96de84d5549648efabb355433e2984726e56558a2f | c8996e6517c35783ff00ea0e4ccd15901dd5b35872c5c7f6954e0b46c57e15c0 |
| 2022 | net_profit_excluding_non_recurring | exchange_official | 1 | b148db9bc6e2d8ed7e1c79064932fa8d06a9f4575a527d8daca8f22e6b969624 |  |
| 2022 | net_profit_excluding_non_recurring | exchange_official | 2 | a84f4e9618e3942ea390e62593d625d94d5ce91911610aa8728f405763623abb | b148db9bc6e2d8ed7e1c79064932fa8d06a9f4575a527d8daca8f22e6b969624 |
| 2022 | net_profit_excluding_non_recurring | reconciled_derived | 1 | eedb8d79f49b41b09e2a12ee0a0829f6a718dbc61c5951fbc7a4e6abfb4559c6 |  |
| 2022 | net_profit_excluding_non_recurring | reconciled_derived | 2 | 26b44e1d6f26ba1c55aa491e14428729a43e5853a3e1457af70b6cc5bdf06e77 | eedb8d79f49b41b09e2a12ee0a0829f6a718dbc61c5951fbc7a4e6abfb4559c6 |
| 2022 | operating_cost | company_official | 1 | 15efbd3b3606985de76d6bdba30757154fdea28ec38fc93606879881174c5742 |  |
| 2022 | operating_cost | exchange_official | 1 | 740e8382e29234d5cc0c7cd28cb68b182fb7779e805fede97fb06239518e8892 |  |
| 2022 | operating_cost | reconciled_derived | 1 | 584cd6073e7043e12b71c14ef692c4610447f442c58623a57b6fbc18494e8459 |  |
| 2022 | operating_profit | company_official | 1 | 05f138124096190dc9b9393d773fb631e85066c78689f5f3ec7c5e75f1acf71c |  |
| 2022 | operating_profit | exchange_official | 1 | 4e342304d8fc3c2e3b9cff9bbd1b6e77f4275529b064227bb7b734a4ef80d3b8 |  |
| 2022 | operating_profit | reconciled_derived | 1 | 707e35066ae15b6558a8f59c470bebf01f10820829553133543945e8ee992974 |  |
| 2023 | net_profit_excluding_non_recurring | company_official | 1 | f6ba8c62dbd9b7c865e132af97aef6b987a439f2c5c5b421be18e055802d30fb |  |
| 2023 | net_profit_excluding_non_recurring | company_official | 2 | 25bd3f5130978a51ac45329a2de4bcb9b2428c3f5cb8fb5b712469cea248a986 | f6ba8c62dbd9b7c865e132af97aef6b987a439f2c5c5b421be18e055802d30fb |
| 2023 | net_profit_excluding_non_recurring | exchange_official | 1 | 52b3fcbeef841610a5685142991ae5a01f7fd7b95e46db7158c36d6d373394a4 |  |
| 2023 | net_profit_excluding_non_recurring | exchange_official | 2 | 981e03a72475a21cbe2f969f9b2a5ed501d765116d4cc39a286975ff9b503171 | 52b3fcbeef841610a5685142991ae5a01f7fd7b95e46db7158c36d6d373394a4 |
| 2023 | net_profit_excluding_non_recurring | reconciled_derived | 1 | 8ef5a9f44891e977d06b5cc6a37aa537c6cffe8bd08d71d8e552cf14b8c8bff8 |  |
| 2023 | net_profit_excluding_non_recurring | reconciled_derived | 2 | 9f2609b8f35229fe86048373b66236ce10a5e1c5eddc91588703dceab481d5c9 | 8ef5a9f44891e977d06b5cc6a37aa537c6cffe8bd08d71d8e552cf14b8c8bff8 |
| 2023 | operating_cost | company_official | 1 | 1e408b2271c8d88d55b226caa04c42eda78cdd125377ca4a112378b65697e580 |  |
| 2023 | operating_cost | company_official | 2 | af683eb9509e469cd4424042b8d88a7534445640efe21ba3f8045a9d8e3a57e5 | 1e408b2271c8d88d55b226caa04c42eda78cdd125377ca4a112378b65697e580 |
| 2023 | operating_cost | exchange_official | 1 | 28bf6ba8782e05a287506592638368632354d7d7ff2bb7186cf9fb1c66a090c6 |  |
| 2023 | operating_cost | exchange_official | 2 | cb2e6d3be0d9aa0d50eec7717aa819ea04dce468764a00697f02bdc2ee9f5795 | 28bf6ba8782e05a287506592638368632354d7d7ff2bb7186cf9fb1c66a090c6 |
| 2023 | operating_cost | reconciled_derived | 1 | 1023ed94b6a7230f239bca84632e58c14fc0a9bb8f9851c276638d98f0828c14 |  |
| 2023 | operating_cost | reconciled_derived | 2 | 66a584865ba4be80644644fc2e26cd41cfdf8d34385102d48b3ee261e9e49409 | 1023ed94b6a7230f239bca84632e58c14fc0a9bb8f9851c276638d98f0828c14 |
| 2023 | operating_profit | company_official | 1 | 70bb32eda6ca22d135da5275e2e05019fdf960e851849f85632a1d885a43e688 |  |
| 2023 | operating_profit | company_official | 2 | e73df6bc7f64c2625ac6af8b4911a2e4d7847e77755f691ff293cee85eec0994 | 70bb32eda6ca22d135da5275e2e05019fdf960e851849f85632a1d885a43e688 |
| 2023 | operating_profit | exchange_official | 1 | 4a087ed21e8b0d2f5928f3275aedfd3d99fd5759d1a605d2415cf293a5b0756c |  |
| 2023 | operating_profit | exchange_official | 2 | 444467ccc5091372a81054be74501dfd4d5d015312bee33da9c6b98cc50aceee | 4a087ed21e8b0d2f5928f3275aedfd3d99fd5759d1a605d2415cf293a5b0756c |
| 2023 | operating_profit | reconciled_derived | 1 | bd07502f296ce6f80bcbffee8e35b3b56b0833d08baf098e43a345edd614a252 |  |
| 2023 | operating_profit | reconciled_derived | 2 | b2b38471ceb24e6225c8e0fa91e8fa7585ec5d4104596d913bc91900f7034e4a | bd07502f296ce6f80bcbffee8e35b3b56b0833d08baf098e43a345edd614a252 |
| 2024 | net_profit_excluding_non_recurring | company_official | 1 | 3af44d023609dcca54edffd6b263fec6d36a9489bb95c191e4ff4bbd04b4383a |  |
| 2024 | net_profit_excluding_non_recurring | exchange_official | 1 | a8be95ec2a2795b05741bcd63aa10a93d0dd5af02a5b0326c0302809b1de33fc |  |
| 2024 | net_profit_excluding_non_recurring | reconciled_derived | 1 | 7e45367d9ee46515ba1ac054d7fd0b6654f75a13ffb20c31ce6136353507a824 |  |
| 2024 | operating_cost | company_official | 1 | 4c2ad1ac465eebe2c50827965789e99e09b7c803d975bef7a4e61de5185e8f74 |  |
| 2024 | operating_cost | exchange_official | 1 | ecccb3d9d0d0756131e384b185e68e2bde0f8cea0f4c1bdca613d742798a9c93 |  |
| 2024 | operating_cost | reconciled_derived | 1 | 244f0f5ff7d60542c5f070d6085afda52cf07229d00a5aa411425a5df76a448d |  |
| 2024 | operating_profit | company_official | 1 | 37a5504eefffbd9fb2c9f9de9c9941cdb1a9f17a789bd6c93011f8860805daba |  |
| 2024 | operating_profit | exchange_official | 1 | 8f9bc732a7a76dcff41fcc9411eec2bda9b9bad54d84dc8b30356e6fc96a4b61 |  |
| 2024 | operating_profit | reconciled_derived | 1 | 53fc036f99690397a46995970845868c8b4ad53a9321d7656edd025aacd6123f |  |

## 最终状态

```text
M2 Stage 2C-C.1: PASS
2021 official document-scope correction: ACCEPTED
2021—2025 earnings-quality official facts: TRUSTED
Earnings-quality metric extension: ALLOWED
ROE / ROA fact foundation: NOT YET
Scoring: STILL NOT YET
```
