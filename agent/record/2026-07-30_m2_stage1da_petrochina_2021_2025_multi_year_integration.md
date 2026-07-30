# M2 Stage 1D-A 工作记录：中国石油 2021—2025 多年度官方事实整合

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`b17387ec36a111da41a5ef10b04c64d70ab0175b`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持不动
- Fact Schema：`2.1`
- Annual acceptance contract：`annual_official_facts_v1_1`
- 默认 `data/research.duckdb` 启动 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`
- 单年度 runner 启动 Git blob：`334a369bd44549d255014d04886977330f6ca338`

## 输入基线

| 年度 | Bundle SHA-256 | Git blob | latest_available_at | Context ID |
|---:|---|---|---|---|
| 2021 | `0c97789044bc594dec48e95a846603b2d22a06227dce535ec855f569aeaf391b` | `cb85f84c3a1459f3a909e36bd6482c8d8124d1a4` | `2022-04-01` | `601857.SH\|2021\|annual\|consolidated` |
| 2022 | `5c610fd5ac33f61f5777ae4ea6fb62b50caff741b7c414e3a4161915db130ed9` | `7076195f3532ead9f0278f97691fe552fdb2ff54` | `2023-03-30` | `601857.SH\|2022\|annual\|consolidated` |
| 2023 | `3f1bd6859927871570aaf1d4efbea2ce36c6d1013bbb2b2630115600c03aae2c` | `6612148ea91b2004605b98e0c8fe799a4d2686ea` | `2024-03-26` | `601857.SH\|2023\|annual\|consolidated` |
| 2024 | `d596ebfc9404cc6bca7520de10ddec5647830212daa946ff25b9e8fe9cc54176` | `03a2ec2813c31676aebed20e4df50042f42f140b` | `2025-03-31` | `601857.SH\|2024\|annual\|consolidated` |
| 2025 | `1cea469542ec4293658703167e7d10cc00b7ced21c9ce6a5e13843bed6e1caab` | `0ababb5262e6cbf1646e165ccfb3e7bfe2769670` | `2026-03-30` | `601857.SH\|2025\|annual\|consolidated` |

每个 bundle 均包含 `revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`，以及 company/exchange 各三条 canonical original fact。

## 实现边界

- 新增薄编排工具，不修改单年度 runner。
- 直接复用 `load_bundle`、`build_context`、`build_source_facts`、`ReconciliationEngine`、`FactRepository`、`OfficialFactReconciliationService` 和 `AsOfQuery.get_latest_available`。
- 所有五年 bundle、30 条 original facts 和 15 对 reconciliation 在创建数据库前完成内存预检。
- 只创建 run-scoped `integration.duckdb`；失败时删除该次数据库，避免部分持久化。
- 不访问网络、不读取 PDF、不写默认数据库、不建立重列版本、不计算指标或评分。

## 待完成

- 完整测试合同。
- 真实离线整合。
- 正式验收报告、全量门禁、两个独立提交和远程核验。
