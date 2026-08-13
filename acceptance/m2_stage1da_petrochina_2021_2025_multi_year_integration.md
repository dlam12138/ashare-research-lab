# M2 Stage 1D-A 正式验收报告：中国石油 2021—2025 多年度官方事实整合

## 结论

**Pass。**

五个已经通过单年度验收的 bundle 已在同一个全新、隔离的 run-scoped DuckDB 中完成整合。整合只包含 original facts 及由现有服务产生的 reconciled facts；没有创建重列版本，没有计算指标、评分或买卖建议。

```text
M2 Stage 1D-A: PASS
M2 Stage 1D-B Restatement Evidence And Version Chains: ALLOWED
Metrics and scoring: NOT YET
```

## Integration Run

- Base commit：`b17387ec36a111da41a5ef10b04c64d70ab0175b`
- Code commit：`053fc1a feat: add multi-year official fact integration`
- run_id：`multi_year_official_601857_SH_2021_2025_20260730_101527_996990`
- status：`passed`
- transaction committed：`true`
- offline：`true`
- Fact Schema：`2.1`
- Annual acceptance contract：`annual_official_facts_v1_1`
- Integration contract：`multi_year_official_facts_v1`
- 数据库：`integration.duckdb`，仅位于被 Git 忽略的本次 run 目录。
- integration.duckdb SHA-256：`F1273AAC859AAF5655A24F820159224513A6FF9A09CEC910C36D7EC9527C86B1`

## 五个输入 Bundle

| 年度 | Bundle SHA-256 | Git blob | latest_available_at | Context ID |
|---:|---|---|---|---|
| 2021 | `0c97789044bc594dec48e95a846603b2d22a06227dce535ec855f569aeaf391b` | `cb85f84c3a1459f3a909e36bd6482c8d8124d1a4` | `2022-04-01` | `601857.SH\|2021\|annual\|consolidated` |
| 2022 | `5c610fd5ac33f61f5777ae4ea6fb62b50caff741b7c414e3a4161915db130ed9` | `7076195f3532ead9f0278f97691fe552fdb2ff54` | `2023-03-30` | `601857.SH\|2022\|annual\|consolidated` |
| 2023 | `3f1bd6859927871570aaf1d4efbea2ce36c6d1013bbb2b2630115600c03aae2c` | `6612148ea91b2004605b98e0c8fe799a4d2686ea` | `2024-03-26` | `601857.SH\|2023\|annual\|consolidated` |
| 2024 | `d596ebfc9404cc6bca7520de10ddec5647830212daa946ff25b9e8fe9cc54176` | `03a2ec2813c31676aebed20e4df50042f42f140b` | `2025-03-31` | `601857.SH\|2024\|annual\|consolidated` |
| 2025 | `1cea469542ec4293658703167e7d10cc00b7ced21c9ce6a5e13843bed6e1caab` | `0ababb5262e6cbf1646e165ccfb3e7bfe2769670` | `2026-03-30` | `601857.SH\|2025\|annual\|consolidated` |

五个 bundle 均保持提交时字节不变；工具没有下载或重新解析 PDF。

## Fact ID 清单

下表完整记录 30 个 original Fact ID 和 15 个 reconciled Fact ID。

| 年度 | Concept | company original | exchange original | reconciled |
|---:|---|---|---|---|
| 2021 | net_profit_attributable_to_parent | `65c656bcac5d2efc9d5e79e30891e7daeb1d6c0c7ab952890db33b665a60b1b9` | `38ec7019d25dededf58d5dc046f346ec91e1441a2b78b6b5c398a25f0201aa1a` | `00a7319ffc9aeff068a71d1895a8ba05c042b289894d1e3e9e2a65aa3c5521f4` |
| 2021 | operating_cash_flow | `bff27442c19c115839326e362696bda86003bb00f81ada5740d6c8dc44fe96f1` | `5429fd7e648f4d3d06217e57e1e8344baab06ab7328fd41595a029992501b5bc` | `932e9eb9ef2ee654f0a31036eb5bad324231c6274bbc5b9befe6d1c216b61da2` |
| 2021 | revenue | `dcccf0526fd2d52cf0c791615035d62938c6d68bf8b563788ef661bae5048850` | `3a337163978075c730e517bfee5f4faad8a4ddcbd7ea578b5e3187bfc82b2e71` | `1b1612e8ca2f32f885d577d67f83bb02a4a7e2f8f220b64f25dbd3be7f4161d6` |
| 2022 | net_profit_attributable_to_parent | `e40af899cb646df7f3c16cd458bd4d991be7822fc39c3890797d4024fc5b70fa` | `9b70bf5e7b5c98059910449752931a4cbbbd9cf8047fdbf92fcea53b72a56b1e` | `d3f70991ddb193324747fd7673274da61d56ffbfbac9a8a813ef3a1467072603` |
| 2022 | operating_cash_flow | `b31644176365f6c0e1d1bb1dd3d4caaffc28aae57feedcf1bd2cb0f93db53728` | `4b202de9d788c0137de7a453a35a7e1ad4bbe5069f964513d67037b3b43e71b6` | `e695784ac714744d5d8250e9b5efa4dd91291dd509e84719e9d534a04cc0c91d` |
| 2022 | revenue | `80817b56628836a4f6dabf2b57682a06f4724667648fc42876f1a6530ca8f693` | `3342b40b4e9ef4931e993a7aede1697ade1bffee1e74ba632eeee9bbcb6eb5ae` | `62c9961e2e5a2c19ba3885bf212764b706645c5c1b59d5e65bf23a6c1faf3e43` |
| 2023 | net_profit_attributable_to_parent | `8c0ad69221674ff45505d199b7d6711510d7db2ed91c0dae72ad705a691b2a79` | `21d6b20c8886ccdecc5783258b8b2a4d6c0990459a799a80ddfb97f14928f973` | `d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4` |
| 2023 | operating_cash_flow | `efc9b7157781c64a7b992200d1c17a967defa9752ae556f856ff5d6429c95d9a` | `dd37a724277e9cceb6c05c50c78b14d7c53690700dc8a43cad094298a8b7b76a` | `7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289` |
| 2023 | revenue | `232c4c512fff424f993bd03535036d2b2b57669da0cc6a2508df15a0d1d050b9` | `70a20f6c1b415cda930100ce6af2324c70ad08bce0984baedc7aaa199da72572` | `9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7` |
| 2024 | net_profit_attributable_to_parent | `c68c5eb457d7a7fda556fd8f3ab7330deefa333a5d43862068773adaa58afffc` | `1e5f7988349e6e1f0914417ed91a90dab3edbd3fa3ad6c9f0b42d1658af18eb6` | `d082020ffd54095ac923e545c0c540449a7b8a3b7b1c78872b184423b9af065f` |
| 2024 | operating_cash_flow | `7477571542e7336afa3532d8c0957904cd923b02af9087ae8a334c817cfc9867` | `da3c485c75ffb34fdfa15afeec8b19bc2b76d8755ad54f96bb3f1e88afe95164` | `3356c5c1cb02b386d2d6d0720c81109f13191aad4d453ead86553267ab3c2e43` |
| 2024 | revenue | `de04cf1a1ad6319926e7fac0324ca7107b137c1e2ccac8b043ab3113111bf8d7` | `741a6ee18c719382ab9616c28ee9816a71e5a7e8653c695c21e1581045de2911` | `edbac03ffc9b1bde84db242ece1cf7e5c8eddeb7e33337fbcc2cf3b04515d196` |
| 2025 | net_profit_attributable_to_parent | `16d823106e9f4a4538ce81f9113b0fb4b13314e0469a9a224bde8521db114626` | `32de1c06a68c8030fe1526d71ada3c25b315dce8b1cf6f19d34ef977b0826e50` | `9009dbb2ddaf6981e33d68fafd2cce681c0c87e591d30a1fa366d0051b38df6c` |
| 2025 | operating_cash_flow | `a1578249e0cb33585398a5b924ae26896968f563dac7a685f804f32bbec4c86d` | `01e3aa3597616feff38621837057a3619400f3d29be72285e1e0ec231ffef47e` | `ad3b6e2a3675ce7e8a8e16bda427597b72d28e30808281e17cd4aa549949357a` |
| 2025 | revenue | `73ed6cf1ddce425e2d51a54272336ee8f2891f54b31a020d8922157de068e6cf` | `a33a051d1ee4aa12b5930aefa1aa70b8bc8e8c72c8ebe7b236f4eaebb618c37b` | `460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1` |

所有 45 个 Fact ID 与各单年度构造结果一致；多年度编排没有改变 canonical identity。

## 持久化计数

| 项目 | 结果 |
|---|---:|
| fact_contexts | 5 |
| company_original | 15 |
| exchange_original | 15 |
| original facts total | 30 |
| reconciled | 15 |
| financial_facts total | 45 |
| eligible_for_metrics | 15 |
| ineligible originals | 30 |
| reconciliation matched | 15 |
| lineage | 45 |
| audit | 45 |

每个年度均为：1 Context、3 company original、3 exchange original、3 reconciled、9 facts、9 lineage。

Lineage 角色计数：

- `reconciliation_input_company = 15`
- `reconciliation_input_exchange = 15`
- `reconciliation_output = 15`

## Point-in-Time 验收

所有快照均通过 `AsOfQuery.get_latest_available()` 取得。

| as_of_date | 可见年度 | Fact 数 |
|---|---|---:|
| 2022-03-31 | 无 | 0 |
| 2022-04-01 | 2021 | 3 |
| 2023-03-30 | 2021—2022 | 6 |
| 2024-03-26 | 2021—2023 | 9 |
| 2025-03-31 | 2021—2024 | 12 |
| 2026-03-30 | 2021—2025 | 15 |

每个可见年度恰好三个 Concept；所有返回事实均为 eligible 的 `reconciled_derived`，没有 original ineligible facts，没有未来年度，也没有按 `period_end` 提前释放事实。

## Restatement Boundary

本阶段所有 45 条事实均保持：

- `fact_version = 1`
- `restatement_version = original`
- `supersedes_fact_id = ""`

没有创建或覆盖任何重列事实。下一阶段需要系统核验的候选为：

- 2022：归母净利润存在后续比较数变化；
- 2023：三个 Concept 均存在后续比较数变化；
- 2024：三项后续比较值已经核对一致；
- 2021：是否存在后续重列留给 Stage 1D-B 系统核验。

## 质量门禁

- Ruff 0.13.2：通过。
- compileall：通过。
- import：通过。
- 多年度及五个注册 bundle targeted pytest：`72 passed`。
- Reconciliation targeted pytest：`86 passed`。
- 全量 pytest：`501 passed, 2 warnings`。
- `git diff --check`：通过。
- 单年度 runner Git blob 保持 `334a369bd44549d255014d04886977330f6ca338`。
- 五个 bundle blob 保持不变。
- 默认 `data/research.duckdb` 验收前后 SHA-256 均为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。
- Manifest 不含本地绝对路径。
- PDF、PNG、DuckDB、output 和 `data/raw/official` 均未进入 Git。
- `stash@{0}` 保持不动。

## 最终状态

```text
M2 Stage 1D-A:
PASS

official annual inputs:
2021—2025 ACCEPTED

integration database:
RUN-SCOPED / ISOLATED

restatement versions created:
NONE

M2 Stage 1D-B:
ALLOWED

metrics and scoring:
NOT YET
```
