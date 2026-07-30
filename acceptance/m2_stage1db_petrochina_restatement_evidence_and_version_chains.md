# M2 Stage 1D-B：中国石油重列证据与版本链正式验收报告

## 验收结论

> **M2 Stage 1D-B：PASS**  
> **Restatement version chains：TRUSTED**  
> **Metrics foundation：ALLOWED**  
> **Scoring：NOT YET**

- Branch：`feat/m2-value-assessment-mvp`
- 起始提交：`9608e64fd3af5ffdb2012c5ca6b2558a9d75399e`
- 合同修正提交：`fb12d56`（`fix: close reconciled restatement version chains`）
- 证据与工具提交：`d03f7c0`（`test: register PetroChina restatement evidence`）
- 最终真实 run：
  `restatement_601857_SH_2021_2025_20260730_111131_272246`
- Fact Schema：`2.1`（本阶段未修改）
- Restatement evidence contract：`restatement_evidence_v1`
- transaction committed：`true`
- 实际 changed Concept-Year 数：`R = 4`

本阶段只核验 `revenue`、`net_profit_attributable_to_parent`、
`operating_cash_flow`，未计算指标、同比、利润率、现金流质量或评分。

## 官方后续年度报告证据

四组 company / exchange PDF 均从既有年度 bundle 注册的正式 URL
重新下载。本地文件的 SHA-256、字节数、页数与 bundle 完全一致；公司与
交易所副本分别目视核验。所有 PDF、截图与临时渲染均位于 Git 忽略范围，
未提交。

| 复核目标 | 来源 | 公告日 | SHA-256 | 字节数 | 页数 | 关系 |
|---|---|---:|---|---:|---:|---|
| 2021 ← 2022 | company | 2023-03-29 | `fea19e9033bbcff24357575d02da3e9b8ddda7d5bbcdd7cabfb018a7e35615c1` | 12,261,788 | 285 | same report, different bytes |
| 2021 ← 2022 | exchange | 2023-03-30 | `da64c67d9e575c3cfcfbd892ce5e8c19d4cf8ca07d51c47df01be2fa4587d861` | 12,257,199 | 285 | same report, different bytes |
| 2022 ← 2023 | company | 2024-03-25 | `b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692` | 12,437,650 | 293 | byte-identical |
| 2022 ← 2023 | exchange | 2024-03-26 | `b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692` | 12,437,650 | 293 | byte-identical |
| 2023 ← 2024 | company | 2025-03-30 | `15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba` | 11,167,845 | 280 | byte-identical |
| 2023 ← 2024 | exchange | 2025-03-31 | `15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba` | 11,167,845 | 280 | byte-identical |
| 2024 ← 2025 | company | 2026-03-29 | `0eba96bd4e815187e7b64645f523f2b5d363ca3fea8168a63ec930f624715f8d` | 10,608,680 | 273 | same report, different bytes |
| 2024 ← 2025 | exchange | 2026-03-30 | `840b15aa4dc38745a6b86a3656063e6a73081ce87407acb0ca93554f4e836e65` | 9,416,509 | 273 | same report, different bytes |

重新下载时间已分别登记在四个证据 JSON 中。公司和交易所后续比较值全部
一致，未触发硬停止条件。

## 三项事实的系统复核结果

原值与后续比较值的单位均为人民币百万元。每项在两份官方副本中完成至少
两遍读数复核。

| 目标年 | 后续年报 | Concept | original | comparative | 结论 | 披露原因 |
|---:|---:|---|---:|---:|---|---|
| 2021 | 2022 | revenue | 2,614,349 | 2,614,349 | unchanged | not applicable |
| 2021 | 2022 | net profit attributable to parent | 92,161 | 92,161 | unchanged | not applicable |
| 2021 | 2022 | operating cash flow | 341,469 | 341,469 | unchanged | not applicable |
| 2022 | 2023 | revenue | 3,239,167 | 3,239,167 | unchanged | not applicable |
| 2022 | 2023 | net profit attributable to parent | 149,375 | 148,738 | **changed** | 企业会计准则解释第 16 号相关递延所得税追溯调整 |
| 2022 | 2023 | operating cash flow | 393,768 | 393,768 | unchanged | not applicable |
| 2023 | 2024 | revenue | 3,011,012 | 3,012,812 | **changed** | 同一控制下合并中国石油集团电能有限公司 |
| 2023 | 2024 | net profit attributable to parent | 161,144 | 161,414 | **changed** | 同一控制下合并中国石油集团电能有限公司 |
| 2023 | 2024 | operating cash flow | 456,596 | 456,847 | **changed** | 同一控制下合并中国石油集团电能有限公司 |
| 2024 | 2025 | revenue | 2,937,981 | 2,937,981 | unchanged | not applicable |
| 2024 | 2025 | net profit attributable to parent | 164,676 | 164,676 | unchanged | not applicable |
| 2024 | 2025 | operating cash flow | 406,532 | 406,532 | unchanged | not applicable |

2023 年报印刷第 6 页同时列示 2022 追溯前/后数据并说明解释第 16 号；
2024 年报合并利润表印刷第 113 页明确说明同一控制下合并及被合并方。
未把未知原因推断为“会计差错更正”。

2025 年尚无后续年度报告，状态严格记录为：

```text
review_status = not_yet_reviewable
```

它不是 missing、mismatch 或 Fail，且未创建任何 2025 v2。

## 版本链合同

Service 在任何写入前对 company / exchange 高版本输入调用既有
`VersionChainValidator`，并额外守住 `source_tier` 稳定性。
reconciled v2 的前序 Fact ID 由调用者通过
`output_supersedes_fact_id` 显式提供；Engine 不猜测前序 ID。

设置 `supersedes_fact_id` 后重新生成 canonical output Fact ID，再执行
FactValidator、VersionChainValidator、provenance、lineage 检查。错误
Concept、Context、source identity、缺失前序、断链、日期倒退和非严格
`+1` 均由可证伪测试证明零写入。

未修改 Engine 数值/单位/容差/匹配语义、FactIdentity、
VersionChainValidator、Fact Schema 或 AsOfQuery。

## 新增 v2 Fact ID 与 supersedes 链

### 2022：归属于母公司股东的净利润

- company：
  `9e8a2e50b7e3318732114a4a74233b40c0503df9e1dbd0cb88662793cbbe45f3`
  → supersedes
  `e40af899cb646df7f3c16cd458bd4d991be7822fc39c3890797d4024fc5b70fa`
- exchange：
  `4de741a561af7dedd9586e327c8ca7f09e2106d0bac9f90cfb75b7c75cff259a`
  → supersedes
  `9b70bf5e7b5c98059910449752931a4cbbbd9cf8047fdbf92fcea53b72a56b1e`
- reconciled：
  `fb2c528c6b9009465dfbed06dd1a76f7277ec2c78655d57aeb0da541f62ab534`
  → supersedes
  `d3f70991ddb193324747fd7673274da61d56ffbfbac9a8a813ef3a1467072603`

### 2023：归属于母公司股东的净利润

- company：
  `fff29e3ee4e12e946a9372bdb080f02bf467b1d9956d046048d0219a454084bd`
  → supersedes
  `8c0ad69221674ff45505d199b7d6711510d7db2ed91c0dae72ad705a691b2a79`
- exchange：
  `075ba76aaaf934f251372183c1b309cae9d31e1b07a6e7e1a0b8491f35b7d6eb`
  → supersedes
  `21d6b20c8886ccdecc5783258b8b2a4d6c0990459a799a80ddfb97f14928f973`
- reconciled：
  `0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129`
  → supersedes
  `d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4`

### 2023：经营活动产生的现金流量净额

- company：
  `85ec54d7d75e6bff9c99b3f80132eacfaa10baa226189b9d9274540e414e5749`
  → supersedes
  `efc9b7157781c64a7b992200d1c17a967defa9752ae556f856ff5d6429c95d9a`
- exchange：
  `a01f338767444c5387bccac37a22247f4a260068874f348ba7295239c5d2812f`
  → supersedes
  `dd37a724277e9cceb6c05c50c78b14d7c53690700dc8a43cad094298a8b7b76a`
- reconciled：
  `109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4`
  → supersedes
  `7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289`

### 2023：营业收入

- company：
  `67860986671d89f5e517eb8129a3a453747fcc311bc3f789c0e090e6fdaa45ca`
  → supersedes
  `232c4c512fff424f993bd03535036d2b2b57669da0cc6a2508df15a0d1d050b9`
- exchange：
  `061f8ef088e48d266ba4fee640804ebeb1dc9775955871644da8542bfc836821`
  → supersedes
  `70a20f6c1b415cda930100ce6af2324c70ad08bce0984baedc7aaa199da72572`
- reconciled：
  `1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8`
  → supersedes
  `9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7`

所有 v2 均为 `fact_version = 2`、
`restatement_version = restated_1`；12 条前序链接真实存在，版本严格
`+1`，stable identity 一致，日期单调且无循环。unchanged 数据未创建
空版本或假版本。

## PIT 与 compare_versions

| Concept / 年度 | 前一日 | v1 值（万元） | 切换日 | v2 值（万元） | compare_versions |
|---|---:|---:|---:|---:|---|
| 2022 net profit attributable to parent | 2024-03-25 | 14,937,500 | 2024-03-26 | 14,873,800 | changed = true |
| 2023 net profit attributable to parent | 2025-03-30 | 16,114,400 | 2025-03-31 | 16,141,400 | changed = true |
| 2023 operating cash flow | 2025-03-30 | 45,659,600 | 2025-03-31 | 45,684,700 | changed = true |
| 2023 revenue | 2025-03-30 | 301,101,200 | 2025-03-31 | 301,281,200 | changed = true |

每个切换点均由 `AsOfQuery.get_latest_available()` 验证：前一日只返回 v1，
切换日只返回 v2，且 v2 指向该 v1。基础快照的年度可见数量仍为
`0 / 3 / 6 / 9 / 12 / 15`；重列只替换同一事实键的当前版本，不增加
指标层键数。最终 `2026-03-30` snapshot 恰为 15 个 eligible
`reconciled_derived` facts，无未来数据提前暴露。

## 动态计数、Audit 与 Lineage

实际 `R = 4`：

| 项目 | 合同公式 | 实际 |
|---|---:|---:|
| fact contexts | 5 | 5 |
| company facts | 15 + R | 19 |
| exchange facts | 15 + R | 19 |
| original/raw facts | 30 + 2R | 38 |
| reconciled facts | 15 + R | 19 |
| financial facts | 45 + 3R | 57 |
| eligible for metrics | 15 + R | 19 |
| ineligible raw facts | 30 + 2R | 38 |
| version-chain links | 3R | 12 |
| Audit | 45 + 3R | 57 |
| Lineage | 45 + 3R | 57 |

每次 reconciliation run 仍保留 company input、exchange input、output
三角色 lineage；output parent Fact IDs 与实际两个 v2 input 完全一致。

## 基线不变性与门禁

- Ruff：`0.13.2`，`py -3.13 -m ruff check src tests` 严格运行通过；
- compileall：`python -m compileall -q src tests` 通过；
- import：Service 与 restatement integration tool 通过；
- Service/version-chain + restatement evidence targeted：`30 passed`；
- Multi-year integration regression：`19 passed`；
- Reconciliation regression：`92 passed`；
- Full pytest：`531 passed, 2 warnings`；两条 warning 均为既有 pandas
  日期解析警告；
- `git diff --check`：通过。

不变性证明：

- 2021—2025 五个 original bundle blob 与 Stage 1D-A 基线完全一致；
- 原 45 个 v1 Fact ID 在新数据库中逐一相等；
- Stage 1D-A runner 与正式报告未修改；
- 默认 `data/research.duckdb` SHA-256 保持：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`；
- PDF、PNG、DuckDB、output、`data/raw/official` 均未进入 Git；
- `stash@{0}` 未操作；
- 未 merge main，未创建 Tag/Release。

## 最终状态

```text
M2 Stage 1D-B: PASS
Restatement evidence: ACCEPTED
Restatement version chains: TRUSTED
Point-in-Time switching: TRUSTED
project north-star drift: FALSE
Metrics foundation: ALLOWED
Scoring: NOT YET
```
