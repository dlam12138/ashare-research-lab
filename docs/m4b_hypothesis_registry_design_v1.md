# M4-B 理论/假设注册表设计 v1

状态：DESIGN_ONLY / READY_FOR_IMPLEMENTATION_REVIEW。本文是 M4-B
`Theory / Hypothesis Registry` 最小切片的**设计规范与拟议接口契约**，尚未实现。文中全部类名、
函数名、字段名、常量名与错误码都标记为**拟议 API**，不冒充现有实现，也不表示本阶段获得任何
实现、真实候选数据集、文献获取、真实假设执行、真实数据、provider、数据库内容或 holdout 授权。

基线：工作树 `D:/量化分析-m4b-registry-design`，分支 `codex/m4b-hypothesis-registry-design`，
HEAD `0de39577f164c095c4bf4f9c3b742fbbee50745d`（Goal 契约提交，2026-09-12 实测）。
`origin/main` 为 `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd`（PR #13 合并点；本地跟踪引用与
GitHub API 实测一致）。PR #13 已合并，40 项 GitHub 检查通过，仅合成 fixture 的有界执行已在
主线。M4-B 仍为 `NOT_STARTED`；真实数据执行与真实假设执行仍未授权。

依赖并保持冻结的既有设计与实现：

- 冻结前置合同 `reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json`
  （`status=FROZEN_PREFLIGHT_ONLY`、`implementation_status=NOT_STARTED`、
  `real_registry_dataset_authorized=false`、`not_implementation=true`）
- [北极星 v2](../A股个股研究与市场机制验证平台-项目北极星.md) 中的
  `Theory / Hypothesis Registry`、`M4-A`、`M4-B` 与“文献证据不自动变成项目证据”边界
- [M4 有界执行与证据处置设计 v1](m4_bounded_execution_and_evidence_design_v1.md)（A.2E，已实现）
- [M4 合成分析矩阵设计 v1](m4_analysis_matrix_design_v1.md)（A.2M，已实现）
- 既有 Goal `agent/goals/2026-09-12_m4b_hypothesis_registry_design.md`（本文不覆盖、不改写）

## 1. 目标、范围与非目标

### 1.1 目标

冻结一个**可实现的** M4-B 最小切片设计，使下列问题不再留给实现者做选择：

1. 记录 schema：19 个冻结最小字段，加 2 个来源身份必需字段（`source_version`、`source_notes`）
   与 3 个记录级字段（`schema_version`、`hypothesis_version`、`state_history`），再加 2 个派生摘要字段
   （`identity_digest`、`record_digest`），共 26 键的完整类型、必填/可选、
   可空性、枚举、长度边界、记录 schema 版本、身份承载字段与可变字段的精确划分、
   未知键策略；
2. 规范序列化与摘要身份：UTF-8 无 BOM、LF、确定性键序、精确数字表示、摘要算法与绑定范围，
   以及主机名、绝对路径、墙钟时间、数据库内容等环境输入被结构性排除；
3. 六类冻结来源类型各自的来源规则、引用/来源身份、版本与备注；文献是假设来源、
   永远不是本地 A 股证据；禁止的规范来源被机械拒绝并给出稳定错误码；
4. 十二个冻结状态与显式合法转换矩阵、转换前置条件、不可跳过边界、禁止的回归与提升，
   以及 `ESTABLISHED` 在缺少适用的冻结开发、注册稳健性与独立 OOS 证据时不可达；
5. 验证顺序与稳定错误码、fail-closed 与类型严格、无强制转换、无部分写入、无歧义重复 ID、
   幂等再验证；
6. registry 元数据与研究结果产物的机械分离：系数、区间、p 值、处置等结果/统计字段被禁止；
7. `MAX_REAL_DEMO_CANDIDATES=3` 的精确规模语义，以及自动异常扫描、回测排序、按收益排序、
   候选自动提升的强制禁令；
8. 拟议实现落点 `src/ashare_research/mechanism/registry/`，匹配既有子包模式，保留冻结的顶层
   `mechanism/*` 聚合，且不引入 `src/ashare_research/m4` 或 `knowledge/`；
9. 仅合成/示意示例：不引入任何真实候选、下载全文、真实引用获取、真实 A 股结果、provider
   或注册数据集；
10. 可追溯性与授权语义：来源/版本/理论保持可追溯；记录可无限期保持 `NOT_TESTED`；
    设计完成不等于实现、执行、证据、真实数据、holdout、推送、PR 或合并授权。

### 1.2 非目标（本设计不授权）

- 不实现任何产品代码。本文只冻结 schema、状态机、错误码与拟议接口；实现需另立 Goal 并获
  用户授权。
- 不创建 `src/ashare_research/mechanism/registry/` 目录或任何 `src/**` 文件。
- 不创建任何注册数据集，不写入真实候选，不采集或下载文献/教材全文，不做真实引用获取。
- 不访问 provider、数据库内容或真实行情，不读取 A 股结果，不接触 holdout，不运行统计执行。
- 不调用 `mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、
  `crash.py`；不计算任何系数、区间、p 值、秩、处置或其他结果。
- 不把文献、教材或经典 anomaly 当作本地 A 股证据，不把发现当作证据，不声称任何机制结论、
  有效性、显著性或可交易性。
- 不修改既有 schema、摘要算法、既有测试、冻结报告、北极星文档、依赖或工作流。
- 不推送、不开 PR、不合并、不进入实现阶段、不递归委派。

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| registry | M4-B 理论/假设注册表；本设计只定义记录、状态机与容器，不实现存储后端 |
| record | 一条假设登记项 `HypothesisRecordV1`（拟议），本文的核心冻结对象 |
| snapshot | 一次注册表快照 `HypothesisRegistrySnapshotV1`（拟议），记录的有序不可变集合 |
| identity-bearing | 进入 `identity_digest` 的字段；在同一 `(hypothesis_id, hypothesis_version)` 内不可变 |
| mutable | 只进入 `record_digest`、不进入 `identity_digest` 的字段（`status`、`state_history`） |
| transition | 一次状态转换请求 `StateTransitionRequestV1`（拟议） |
| candidate | 一条尚未执行的假设；候选身份不等于证据，发现不等于证据 |
| real-demo candidate | `a_share_data_feasibility ∈ {FEASIBLE_FREE, FEASIBLE_PAID}` 的记录；计入规模门 |
| provenance | 来源类型、标题、作者/发布方、来源日期、引用/来源身份、版本、备注的合称 |
| outcome artifact | 任何承载系数、区间、p 值、秩、处置或收益的产物；registry **不得**包含其字段 |

编号约定：本文的设计条款编号（如 `V9`、`S7`）是稳定标识，验收场景文档按同一编号引用；
任何编号一旦发布不得重用或改义。

## 2. 已验证基线与来源绑定

### 2.1 冻结前置合同（Stage4P M4-B，实测原样引用）

`reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json` 的实际字段（本设计**不修改**该文件）：

```json
{"schema_version":"M4_STAGE4P_M4B_HYPOTHESIS_REGISTRY_CONTRACT_V1",
 "status":"FROZEN_PREFLIGHT_ONLY","implementation_status":"NOT_STARTED",
 "real_registry_dataset_authorized":false,
 "purpose":"Store candidate research provenance and feasibility metadata without treating literature or discovery as A-share evidence.",
 "minimum_fields":["hypothesis_id","source_type","source_title","authors_or_issuer",
   "source_date","citation_or_source_identity","theory","original_market","original_sample",
   "expected_direction","candidate_signal","target_horizon","known_controls",
   "known_alternative_explanations","known_replications","known_failures_or_decay",
   "a_share_data_feasibility","free_data_feasibility","status"],
 "allowed_source_types":["PERSONAL_OBSERVATION","TEXTBOOK_THEORY","ACADEMIC_PAPER",
   "KNOWN_ANOMALY","OFFICIAL_MECHANISM","REPLICATION_EXTENSION"],
 "literature_provenance":{"full_text_download_in_M4B":false,
   "required_identity":["source identity","citation","version","source type","notes"],
   "preferred_sources_later":["original paper","author manuscript","replication",
     "official source","high-quality textbook"],
   "forbidden_canonical_sources":["pirated textbook source","random blog",
     "LLM memory as citation"],
   "literature_is_hypothesis_source_not_local_evidence":true},
 "state_machine":{"states":["DISCOVERED","LITERATURE_REVIEWED","A_SHARE_FEASIBILITY_REVIEWED",
   "NOT_TESTED","PRE_REGISTERED","DEVELOPMENT_EXECUTED","ROBUSTNESS_EXECUTED","OOS_EXECUTED",
   "NOT_ESTABLISHED","ESTABLISHED","INCONCLUSIVE","DEFERRED"],
  "invariants":["DISCOVERED != evidence","LITERATURE_REVIEWED != A-share validation",
    "NOT_TESTED cannot enter recommendation system",
    "registry metadata is separate from research outcome artifacts"],
  "execution_boundary":"Only a separately frozen M4-A research contract may move a candidate into execution states.",
  "evidence_boundary":"ESTABLISHED is unavailable without the applicable frozen development, robustness, and independent OOS evidence policy."},
 "initial_candidate_classes":[
   {"class_id":"CANDIDATE_CLASS_1","category":"MOMENTUM","status":"NOT_TESTED","real_A_share_outcome_read":false,"parameters_defined":false,"effectiveness_claim":false},
   {"class_id":"CANDIDATE_CLASS_2","category":"VALUE_OR_PROFITABILITY","status":"NOT_TESTED","real_A_share_outcome_read":false,"parameters_defined":false,"effectiveness_claim":false},
   {"class_id":"CANDIDATE_CLASS_3","category":"BEHAVIORAL_OR_EVENT","status":"NOT_TESTED","real_A_share_outcome_read":false,"parameters_defined":false,"effectiveness_claim":false}],
 "scale_boundary":{"MAX_REAL_DEMO_CANDIDATES":3,"AUTOMATED_ANOMALY_SCAN":"PROHIBITED",
   "BACKTEST_RANKING":"PROHIBITED","real_candidate_dataset_in_preflight":false},
 "not_implementation":true}
```

`minimum_fields` 实际为 **19** 项。该列表是**下限**：第 4.2 节在其之上只新增来源身份所必需的
`source_version`、`source_notes`（对应 `required_identity` 的 "version"、"notes"）与记录级
`schema_version`，并新增 `hypothesis_version` 与 `state_history`（共 5 个新增字段），
再加 2 个派生摘要字段 `identity_digest`、`record_digest`，全记录恰为 **26** 键；不得再新增任何其它字段。
上方引用块与本工作树的合同文件逐字对应（12 个顶层键，2026-09-12 用 `json.loads` 逐键比对为相等）。

`initial_candidate_classes` 是**类别**，不是记录：三个类别都没有参数、没有结果、没有真实候选；
本设计不把任何类别实体化为记录。

### 2.2 本设计消费的既有能力（2026-09-12 只读复核）

| 既有对象 | 真实位置 | 本设计如何消费 |
| --- | --- | --- |
| `canonical_digest(payload)` | `mechanism/model_digest.py` | 直接复用为唯一摘要算法；`bounded.py` 亦从此处导入，保持单一来源 |
| `canonical_decimal(value)` | `mechanism/hypothesis_config.py` | 仅作为“十进制规范化”语义的既有先例；registry 记录不含任何浮点/参数数值，故本设计不调用它承载结果 |
| `_IDENTIFIER_RE = ^[A-Za-z0-9][A-Za-z0-9_.-]*$` | `mechanism/hypothesis_config.py` | `hypothesis_id` 采用**同一**标识符规则（本设计不改写该既有实现） |
| 序列化约定 | `serialize_matrix` / `serialize_dataset` / `serialize_execution_artifact` | `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))` + 恰好一个结尾 `\n`，再 `.encode("utf-8")` |
| 失败约定 | `MatrixError(ValueError)`、`AdapterError(ValueError)`、`ExecutionError(ValueError)` 带 `code` | 本设计提出同级 `RegistryError(ValueError)`，带稳定 `code` |
| `RESTRICTED_RESEARCH_OUTPUT_KEYS` | `mechanism/contracts.py` | 第 9 节的禁止结果键集合必须**包含**该冻结集合的全部成员 |
| `FORBIDDEN_KEYS` | `mechanism/execution/bounded.py` | 第 9 节的禁止环境/选择键集合必须**包含**该冻结集合的全部成员 |

### 2.3 为什么现在不能直接实现（本设计的核心授权声明）

本设计**不构成**实现许可。直接实现当前不获允许，理由必须逐条记录：

1. 本 Goal 的 Forbidden scope 明确禁止修改 `src/**`；registry 是新增子包，只能在另行授权的
   实现 Goal 下创建。
2. `real_registry_dataset_authorized=false` 且 `real_candidate_dataset_in_preflight=false`：
   即使实现了 registry，也**没有**任何获授权的真实候选可以写入；文献获取与真实引用下载同样
   未授权。
3. 状态机的执行状态（`DEVELOPMENT_EXECUTED` 及之后）要求绑定一份**单独冻结的 M4-A 研究合同**
   身份；真实假设执行仍为 `NOT AUTHORIZED`，因此执行状态在实践中不可达。
4. 实现阶段的验收必须针对**真实实现产物**才能执行；本阶段只能给出规范性期望，
   不能声称任何 registry 实现测试已通过。
5. 北极星 v2 与 Stage4P 合同的 `not_implementation=true` 把 M4-B 保持在
   `FROZEN_PREFLIGHT_ONLY`；本设计是该前置状态的**延续**，不是其完成。

因此：本文全部接口一律标记为**拟议（proposed）**，且不得被描述为已实现。

## 3. 冻结的常量（拟议）

全部为**拟议**常量；实现不得改名、改值或新增同类常量。

```text
RECORD_SCHEMA_VERSION      = "M4_HYPOTHESIS_REGISTRY_RECORD_V1"
SNAPSHOT_SCHEMA_VERSION    = "M4_HYPOTHESIS_REGISTRY_SNAPSHOT_V1"
REGISTRY_VERSION           = "M4_THEORY_HYPOTHESIS_REGISTRY_V1"
DIGEST_ALGORITHM_ID        = "M4_HYPOTHESIS_REGISTRY_SHA256_CANONICAL_JSON_V1"
MAX_REAL_DEMO_CANDIDATES   = 3
MAX_RECORDS_PER_SNAPSHOT   = 3          # 与 MAX_REAL_DEMO_CANDIDATES 同值；见第 10 节
MAX_IDENTITY_DIGEST_LEN    = 64         # 小写十六进制 SHA-256
HYPOTHESIS_ID_MAX_LEN      = 120
SHORT_TEXT_MAX_LEN         = 500
LONG_TEXT_MAX_LEN          = 2000
NOTES_MAX_LEN              = 4000
CITATION_MAX_LEN           = 1000
SOURCE_VERSION_MAX_LEN     = 200
TARGET_HORIZON_MAX_LEN     = 100
MAX_HYPOTHESIS_VERSION     = 1000
UNKNOWN_SENTINEL           = "UNKNOWN"
INTERPRETATION_BOUNDARY    = (
  "REGISTRY_METADATA_ONLY: design-stage hypothesis provenance metadata. Not evidence, "
  "not a research finding, not a significance, effectiveness, estimability or tradability "
  "claim, not an A-share mechanism result, and not an authorization to implement the "
  "registry, to create a real candidate dataset, to acquire literature, to execute on real "
  "data, to access holdout, or to enter M4-A/M4-B execution."
)
```

`MAX_RECORDS_PER_SNAPSHOT = 3` 的理由：M4-B 最小切片是**有界**注册表，其规模上限由
`MAX_REAL_DEMO_CANDIDATES=3` 与“真实候选数据集未授权”共同决定。两者同值使“把非 real-demo
记录塞进快照绕过规模门”不可表达。实现不得把该常量解释为“必须填满 3 条”。

## 4. 记录 schema（冻结项 1）

### 4.1 记录结构（拟议 `HypothesisRecordV1`）

一条记录是**冻结 dataclass**，容器一律为 `tuple`，不存在 `dict`/`list`/`set` 字段。
规范字典形态（键序由序列化器决定，见第 5 节）：

```text
{ "schema_version": RECORD_SCHEMA_VERSION,
  "hypothesis_id": <标识符>,
  "hypothesis_version": <正整数>,
  "source_type": <六值枚举>,
  "source_title": <文本>,
  "authors_or_issuer": <文本>,
  "source_date": <ISO 部分精度日期>,
  "citation_or_source_identity": <文本>,
  "source_version": <文本>,
  "source_notes": <文本，可为 "">,
  "theory": <文本>,
  "original_market": <文本>,
  "original_sample": <文本>,
  "expected_direction": <三值枚举>,
  "candidate_signal": <文本>,
  "target_horizon": <文本>,
  "known_controls": [<文本>, ...],
  "known_alternative_explanations": [<文本>, ...],
  "known_replications": [<文本>, ...],
  "known_failures_or_decay": [<文本>, ...],
  "a_share_data_feasibility": <四值枚举>,
  "free_data_feasibility": <四值枚举>,
  "status": <十二值枚举>,
  "state_history": [<StateTransitionV1>, ...],
  "identity_digest": <64 位小写十六进制>,
  "record_digest": <64 位小写十六进制> }
```

### 4.2 字段冻结表（19 个最小字段 + 5 个新增字段 + 2 个派生摘要字段，共 26 键）

必填 = 键必须存在；不可空 = 值不得为 `null`；枚举 = 封闭词表，取词表外值一律失败。

| # | 字段 | 类型 | 必填 | 可空 | 约束与枚举 |
| --- | --- | --- | --- | --- | --- |
| 1 | `hypothesis_id` | `str` | 是 | 否 | 匹配 `^[A-Za-z0-9][A-Za-z0-9_.-]*$`，长度 1..120；同一快照内唯一 |
| 2 | `hypothesis_version` | `int` | 是 | 否 | 严格 `int`（`bool` 不是 `int`），1..1000 |
| 3 | `source_type` | `str` 枚举 | 是 | 否 | `PERSONAL_OBSERVATION` / `TEXTBOOK_THEORY` / `ACADEMIC_PAPER` / `KNOWN_ANOMALY` / `OFFICIAL_MECHANISM` / `REPLICATION_EXTENSION` |
| 4 | `source_title` | `str` | 是 | 否 | 去除首尾空白后非空，长度 1..500 |
| 5 | `authors_or_issuer` | `str` | 是 | 否 | 非空，长度 1..500；未知时写 `"UNKNOWN"` |
| 6 | `source_date` | `str` | 是 | 否 | `YYYY` / `YYYY-MM` / `YYYY-MM-DD` 三选一，必须是该精度下的合法公历日期；精度必须显式 |
| 7 | `citation_or_source_identity` | `str` | 是 | 否 | 非空，长度 1..1000；未知时写 `"UNKNOWN"` |
| 8 | `source_version` | `str` | 是 | 否 | 非空，长度 1..200；未知时写 `"UNKNOWN"` |
| 9 | `source_notes` | `str` | 是 | 否 | 长度 0..4000；**唯一**允许空串的字段；空串表示“无附加备注” |
| 10 | `theory` | `str` | 是 | 否 | 非空，长度 1..2000 |
| 11 | `original_market` | `str` | 是 | 否 | 非空，长度 1..500；未知时写 `"UNKNOWN"` |
| 12 | `original_sample` | `str` | 是 | 否 | 非空，长度 1..2000；未知时写 `"UNKNOWN"` |
| 13 | `expected_direction` | `str` 枚举 | 是 | 否 | `POSITIVE` / `NEGATIVE` / `TWO_SIDED`（与既有 `EvidenceDirection` 同词表） |
| 14 | `candidate_signal` | `str` | 是 | 否 | 非空，长度 1..500；只描述候选信号，不承载参数值 |
| 15 | `target_horizon` | `str` | 是 | 否 | 非空，长度 1..100；文本口径，不是拟合参数 |
| 16 | `known_controls` | `tuple[str, ...]` | 是 | 否 | 元素 1..500，可为空元组（显式“未知已知控制项”）；顺序有意义，不得排序 |
| 17 | `known_alternative_explanations` | `tuple[str, ...]` | 是 | 否 | 元素 1..2000，可为空元组；顺序有意义 |
| 18 | `known_replications` | `tuple[str, ...]` | 是 | 否 | 元素 1..500，可为空元组；每个元素是引用/来源身份文本，**不是**复制结果 |
| 19 | `known_failures_or_decay` | `tuple[str, ...]` | 是 | 否 | 元素 1..2000，可为空元组；不得承载数值结果 |
| 20 | `a_share_data_feasibility` | `str` 枚举 | 是 | 否 | `FEASIBLE_FREE` / `FEASIBLE_PAID` / `NOT_FEASIBLE` / `UNKNOWN` |
| 21 | `free_data_feasibility` | `str` 枚举 | 是 | 否 | `SUFFICIENT` / `PARTIAL` / `INSUFFICIENT` / `UNKNOWN` |
| 22 | `status` | `str` 枚举 | 是 | 否 | 十二状态之一（第 7.1 节） |
| 23 | `state_history` | `tuple[StateTransitionV1, ...]` | 是 | 否 | 至少 1 项；`ordinal` 从 1 连续；末项 `to_state == status` |
| 24 | `schema_version` | `str` | 是 | 否 | 必须恰为 `RECORD_SCHEMA_VERSION` |
| 25 | `identity_digest` | `str` | 是 | 否 | 64 位小写十六进制，自洽（第 5.2 节） |
| 26 | `record_digest` | `str` | 是 | 否 | 64 位小写十六进制，自洽（第 5.2 节） |

文本字段的**公共文本规则**（对第 4、5、6、7、8、9、10、11、12、14、15 及元组元素生效）：

1. 必须是 `str`，不得是 `bool`/`int`/`float`/`None`/容器/`FrozenJSON*`；
2. 不得包含 `\r` 或 `\n`；不得包含 C0/C1 控制字符；不得以空白开头或结尾
   （唯一例外是允许为空的 `source_notes`，此时“空”必须是零长度，不是纯空白）；
3. 不得包含 BOM（`\ufeff`）、零宽字符或 Unicode 非字符；
4. 不做任何规范化（不 `strip`、不 `casefold`、不 `NFC`）：输入必须已经是规范形态，
   否则失败（见第 8.3 节：不强制转换）。

### 4.3 身份承载字段与可变字段（冻结划分）

```text
identity-bearing（进入 identity_digest，共 22 项）：
  schema_version, hypothesis_id, hypothesis_version,
  source_type, source_title, authors_or_issuer, source_date,
  citation_or_source_identity, source_version, source_notes,
  theory, original_market, original_sample, expected_direction,
  candidate_signal, target_horizon,
  known_controls, known_alternative_explanations,
  known_replications, known_failures_or_decay,
  a_share_data_feasibility, free_data_feasibility

mutable（只进入 record_digest）：
  status, state_history

派生（不进入任何摘要输入，由计算得出）：
  identity_digest, record_digest
```

冻结规则：

- **来源、版本与理论不可改写。** `source_notes` 属于身份承载字段：注册之后**不得**追加或修改
  备注。需要更正来源信息时，必须提升 `hypothesis_version` 形成新记录，旧记录保持原样同时存在。
- **只有状态可以前进。** 在同一 `(hypothesis_id, hypothesis_version)` 内，唯一允许的变化是
  `status` 与 `state_history`；因此 `identity_digest` 在全部合法转换下保持不变。
- **可变字段不可被外部直接写入。** 公开面不提供“设置 `status`”的入口，
  只提供第 7 节的转换入口（第 11.2 节）。

### 4.4 记录身份键与唯一性

```text
记录身份键 = (hypothesis_id, hypothesis_version)
```

- 同一快照内 `(hypothesis_id, hypothesis_version)` 必须唯一；出现两条同身份键记录时 fail-closed，
  且**先于**任何“取最新/后写覆盖”语义：两条 `identity_digest` 相同 → `DUPLICATE_HYPOTHESIS_ID`；
  两条 `identity_digest` 不同（同一身份键下内容被改写）→ `PROVENANCE_REWRITE`；
- 同一 `hypothesis_id` **允许**存在多个不同 `hypothesis_version`：更高的版本是新记录，
  旧记录不得被覆盖、删除或改写；
- 同一 `(hypothesis_id, hypothesis_version)` 只允许一个 `identity_digest`；改写既有身份（含经
  转换入口改写身份承载字段，第 7.6 节 N7）一律失败并报 `PROVENANCE_REWRITE`（第 8.2 节）；
- 不做“自动合并”“自动取最新”：快照内所有版本同时可见。

### 4.5 未知键策略（fail-closed）

- 记录对象的键集合必须**恰好**等于第 4.1 节的 26 个键；任何额外键 → `UNKNOWN_RECORD_FIELD`；
  任何缺失键 → `MISSING_REQUIRED_FIELD`；
- 未知键检查先于取值检查（第 8.1 节 V2 先于 V3），因此额外键不会被静默忽略；
- 不存在“忽略未知字段以向前兼容”的模式，不存在 `extra="allow"` 语义，不存在环境变量开关；
- 嵌套对象（`state_history[*]`）同样适用精确键集规则，未知嵌套键 → `UNKNOWN_RECORD_FIELD`。

## 5. 规范序列化与摘要身份（冻结项 2）

### 5.1 规范序列化（拟议 `serialize_hypothesis_record`）

```text
bytes = (json.dumps(canonical_dict, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")) + "\n").encode("utf-8")
```

冻结规则 S1–S10：

| 编号 | 规则 |
| --- | --- |
| S1 | 编码必须是 UTF-8，**不带 BOM**；读取时若前 3 字节为 `EF BB BF` → `NON_CANONICAL_SERIALIZATION` |
| S2 | 换行只允许 `LF`（`\n`）；任何 `CR`（`\r`）字节 → `NON_CANONICAL_SERIALIZATION` |
| S3 | 结尾必须恰好一个 `LF`：零个或两个及以上 → `NON_CANONICAL_SERIALIZATION` |
| S4 | 键序由 `sort_keys=True` 决定（Unicode 码位升序），实现不得自定义键序 |
| S5 | 分隔符固定为 `,` 与 `:`，不得有空格、缩进或换行 |
| S6 | `ensure_ascii=False`：非 ASCII 字符以原字符输出，不做 `\uXXXX` 转义 |
| S7 | JSON 数字 token 只允许整数形态 `-?(0|[1-9][0-9]*)`，且只出现在 `hypothesis_version` 与 `state_history[*].ordinal`；任何浮点或指数 token（`.`,`e`,`E`）→ `NON_CANONICAL_SERIALIZATION` |
| S8 | `null` 只允许出现在第 7.7 节声明可空的三个位置（`state_history[*].from_state`、`.authorization_ref`、`.evidence_kind`）；其它位置出现 `null` → `INVALID_FIELD_TYPE` |
| S9 | 数组顺序是**输入顺序**，实现不得排序、去重或规范化数组元素（顺序进入摘要） |
| S10 | 序列化入口必须先完整验证再输出：验证失败时**不得**返回任何字节，也不得写出部分内容 |

### 5.2 摘要身份（拟议 `hypothesis_record_identity_digest` / `hypothesis_record_digest`）

摘要算法唯一：既有 `ashare_research.mechanism.model_digest.canonical_digest`，即
`sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())`。
本设计不新增第二套摘要算法；`DIGEST_ALGORITHM_ID` 只作为载荷内的自描述字段。

```text
identity_payload = { "digest_algorithm": DIGEST_ALGORITHM_ID,
                     "digest_scope": "identity_bearing_fields",
                     <第 4.3 节 22 个身份承载字段> }
identity_digest  = canonical_digest(identity_payload)

record_payload   = { "digest_algorithm": DIGEST_ALGORITHM_ID,
                     "digest_scope": "full_record",
                     "identity_digest": identity_digest,
                     <第 4.3 节 22 个身份承载字段>,
                     "status": <status>,
                     "state_history": <state_history 的规范字典数组> }
record_digest    = canonical_digest(record_payload)
```

冻结规则：

- **绑定范围**：`identity_digest` 绑定全部 22 个身份承载字段（含来源、版本、理论、4 个已知项
  数组的元素与顺序）；`record_digest` 绑定 `identity_digest` 加 `status` 与完整 `state_history`；
- **两个摘要互不覆盖对方字段**：`identity_digest` 不得包含 `status`/`state_history`/`record_digest`，
  `record_digest` 不得包含自身；
- **再验证必须是纯函数**：重算必须与记录内值逐字符相等，否则
  `IDENTITY_DIGEST_MISMATCH` / `RECORD_DIGEST_MISMATCH`；
- **无 float64 层**：registry 记录不含任何浮点结果，因此**不存在**执行层那种“float64 身份层”；
  本设计明确声明 registry 摘要不绑定、也不可能绑定任何统计输出。

### 5.3 必须排除的环境输入（结构性排除）

以下输入**不得**出现在记录、规范字典、序列化字节或任一摘要载荷中，也不得影响它们的取值：

| 被排除的输入 | 机械保证 |
| --- | --- |
| 主机名 / 用户名 / 主目录 | 记录 schema 无对应字段；第 9 节禁止键扫描含 `hostname`/`username`/`user`/`home` |
| 当前工作目录 / 绝对路径 / 仓库根 | 无对应字段；禁止键扫描含 `cwd`/`worktree`/`path`/`abspath`/`absolute_path`/`root_path`；值扫描拒绝绝对路径 |
| 墙钟时间 / 时区 / 运行时间戳 | 无对应字段；公共入口不接受任何时间参数；`source_date` 是来源出版日期，**不是**采集时间 |
| 环境变量 / 会话 / 进程 | 无对应字段；禁止键扫描含 `env`/`environment`/`session` |
| 数据库内容 / provider 身份 / 真实行情 | registry 不打开数据库、不调用 provider；公共入口无 IO |
| 文件 mtime / inode / 文件大小 | 无对应字段；公共入口不接受路径参数 |
| 记录在文件或数据库中的物理位置与插入顺序 | 快照顺序由 `(hypothesis_id, hypothesis_version)` 决定（第 6/10 节），与插入顺序无关 |

因此：同一记录内容在不同机器、不同工作目录、不同时间、不同插入顺序下必须得到
**逐字节相同**的序列化输出与相同的两个摘要（验收场景 AC-12/AC-13）。

### 5.4 规范字典视图（拟议 `hypothesis_record_to_canonical_dict`）

- 返回**独立副本**：修改返回值不得改变原记录（冻结 dataclass + 深拷贝语义）；
- 返回的字典是可被 `canonical_digest` 直接序列化的**纯 JSON 值**（`dict`/`list`/`str`/`int`/`None`），
  不得含 dataclass 或 `FrozenJSON*`；这与执行层“先投影为纯 JSON 再入摘要”的既有结论一致；
- 键序在返回时不必排序（排序由序列化器保证），但内容必须与序列化字节一一对应。

## 6. 来源与引用规则（冻结项 3）

### 6.1 六类冻结来源类型（逐类规则）

| `source_type` | 允许的来源身份形态 | 最低来源要求 | 明确不等于 |
| --- | --- | --- | --- |
| `PERSONAL_OBSERVATION` | 观察者标识 + 观察记录标识 + 观察日期 | `source_title` 描述被观察现象；`authors_or_issuer` 写观察者；`citation_or_source_identity` 写可复查的记录标识或 `"UNKNOWN"` | 不等于证据，不等于可执行假设 |
| `TEXTBOOK_THEORY` | 教材名 + 版次 + 出版方 | `source_version` 必须是版次/印次；`citation_or_source_identity` 必须含出版方与版次 | 不等于 A 股验证，不等于实证支持 |
| `ACADEMIC_PAPER` | 期刊/工作论文标识 + 版本（published / accepted / working paper / preprint） | `citation_or_source_identity` 必须含期刊或 repository 标识；`source_version` 必须写明版本状态 | 不等于本地复现，不等于 A 股结论 |
| `KNOWN_ANOMALY` | 该 anomaly 的原始文献身份 + 版本 | `citation_or_source_identity` 必须指向原始文献而非二次综述 | 不等于本项目复现，不等于可持续 |
| `OFFICIAL_MECHANISM` | 官方文件/规则标识 + 发布机构 + 生效版本 | `authors_or_issuer` 必须是发布机构；`source_version` 必须写到可区分的规则版本 | 不等于市场影响已验证 |
| `REPLICATION_EXTENSION` | 原始研究身份 + 复制/扩展研究身份 | `citation_or_source_identity` 必须同时可解析到原始与复制身份；`source_version` 写复制版本 | 不等于本项目复制，不等于独立 OOS |

六类之外任何取值 → `UNKNOWN_SOURCE_TYPE`（第 8.2 节）。

### 6.2 `required_identity` 五要素到字段的映射（冻结）

| 合同 `required_identity` | 记录字段 | 强制程度 |
| --- | --- | --- |
| source type | `source_type` | 必填 + 封闭枚举 |
| source identity | `citation_or_source_identity` | 必填非空（未知写 `"UNKNOWN"`） |
| citation | `citation_or_source_identity` | 同一字段承载；`known_replications` 的元素同样是引用文本 |
| version | `source_version` | 必填非空；`TEXTBOOK_THEORY`/`OFFICIAL_MECHANISM`/`ACADEMIC_PAPER` 必须写到可区分版本 |
| notes | `source_notes` | 必填（可为空串） |

### 6.3 文献是假设来源，不是本地 A 股证据（冻结不变式）

```text
L1  source_type ∈ {TEXTBOOK_THEORY, ACADEMIC_PAPER, KNOWN_ANOMALY, REPLICATION_EXTENSION}
    ⇒ 该记录最多支持“假设来源”语义，永远不构成本项目证据。
L2  DISCOVERED / LITERATURE_REVIEWED 状态本身不含任何证据语义；
    “已读文献”不得被读成“已在 A 股验证”。
L3  记录不得包含任何把来源证据升级为项目证据的字段（第 9 节机械拒绝）；
    不存在 evidence_level、verified、confirmed、significant 之类字段。
L4  registry 记录与 M4-A 执行产物是不同产物：registry 只提供来源与候选元数据，
    执行产物只在 M4-A 合同下产出，两者不共享身份、不互相写入。
L5  状态机不提供从来源状态直接跳到 ESTABLISHED 的路径（第 7 节）。
```

### 6.4 禁止的规范来源（机械拒绝）

合同冻结的 `forbidden_canonical_sources` 必须被机械拒绝，映射为稳定错误码
`FORBIDDEN_CANONICAL_SOURCE`（第 8.1 节 V6）：

| 禁止来源 | 机械判定规则（在 `citation_or_source_identity`、`source_title`、`source_version`、`source_notes` 四个字段上求值） |
| --- | --- |
| pirated textbook source | 命中盗版/影印/扫描/网盘/PDF 聚合站特征词表，且 `source_type == TEXTBOOK_THEORY` |
| random blog | 命中个人博客/论坛/自媒体/内容农场特征词表，或来源身份只含平台域名而无可追溯作者与版次 |
| LLM memory as citation | 来源身份为 `"LLM"`、`"MODEL"`、`"AI"`、`"CHATGPT"`、`"MEMORY"`、`"RECALL"` 等模型记忆标记，或 `source_version` 为 `"UNKNOWN"` 而 `source_type ∈ {ACADEMIC_PAPER, TEXTBOOK_THEORY, KNOWN_ANOMALY, REPLICATION_EXTENSION}` |

冻结约束：

- 特征词表是**常量数据**，必须在实现中以显式、可评审的常量集合存在，
  不得由模型或运行期推断生成；实现阶段必须在验收场景中给出词表的正例与反例；
- 拒绝是**fail-closed**：命中即失败，不存在“降级为 UNKNOWN 来源”或“标记待人工复核”的路径；
- 拒绝先于任何状态转换与写入（V6 早于 V9/V11）；
- 词表的具体条目属于**实现评审项**；本设计只冻结判定位置、错误码与 fail-closed 语义，
  并明确禁止实现把词表做成可配置开关。

### 6.5 `source_notes` 的规范性与禁止内容

- `source_notes` 是身份承载字段（第 4.3 节），注册后不可改写；
- 它不得承载结果：第 9 节的禁止键扫描与禁止值扫描同样作用于它；
- 它不得包含绝对路径、URL 之外的本地路径、凭据或个人信息；
- 空串是唯一合法的“无备注”表示；`null`、纯空白串、缺键都不合法。

## 7. 状态机（冻结项 4）

### 7.1 十二个冻结状态

```text
S1  DISCOVERED
S2  LITERATURE_REVIEWED
S3  A_SHARE_FEASIBILITY_REVIEWED
S4  NOT_TESTED
S5  PRE_REGISTERED
S6  DEVELOPMENT_EXECUTED
S7  ROBUSTNESS_EXECUTED
S8  OOS_EXECUTED
S9  NOT_ESTABLISHED
S10 ESTABLISHED
S11 INCONCLUSIVE
S12 DEFERRED
```

状态语义（与合同 `invariants` 逐条对齐）：

| 状态 | 含义 | 授权含义 |
| --- | --- | --- |
| `DISCOVERED` | 已知存在该候选 | `DISCOVERED != evidence`；不授权任何执行 |
| `LITERATURE_REVIEWED` | 来源已读并登记来源身份 | `LITERATURE_REVIEWED != A-share validation` |
| `A_SHARE_FEASIBILITY_REVIEWED` | 已评估数据可得性（仅元数据判断） | 可得性评估不是可执行性证明 |
| `NOT_TESTED` | 休息态：已登记、未执行 | `NOT_TESTED cannot enter recommendation system`；可无限期保持 |
| `PRE_REGISTERED` | 已预注册研究设计身份 | 预注册不是执行授权 |
| `DEVELOPMENT_EXECUTED` | 冻结开发期已执行（M4-A 合同下） | 需 `authorization_ref`；单一开发期结果不是证据 |
| `ROBUSTNESS_EXECUTED` | 注册稳健性已执行 | 需 `authorization_ref`；注册稳健性不等于独立验证 |
| `OOS_EXECUTED` | 独立 OOS 已执行 | 需 `authorization_ref`；OOS 未通过前不得提升 |
| `NOT_ESTABLISHED` | 证据不支持 | 终态；不得直接提升为 `ESTABLISHED` |
| `ESTABLISHED` | 三项证据齐备且通过策略 | 需完整证据链；见 7.5；不等于可交易 |
| `INCONCLUSIVE` | 证据不确定 | 终态；不得直接提升 |
| `DEFERRED` | 主动搁置 | 只能恢复到 `NOT_TESTED`；不丢失历史 |

### 7.2 合法转换矩阵（完整、封闭）

行 = 当前状态（`from`），列 = 目标状态（`to`）；`·` 表示非法。转换必须逐格实现，
不得有“默认允许”分支。

| from \ to | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | S11 | S12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **S1 DISCOVERED** | · | ✅ | · | · | · | · | · | · | · | · | · | ✅ |
| **S2 LITERATURE_REVIEWED** | · | · | ✅ | · | · | · | · | · | · | · | · | ✅ |
| **S3 A_SHARE_FEASIBILITY_REVIEWED** | · | · | · | ✅ | · | · | · | · | · | · | · | ✅ |
| **S4 NOT_TESTED** | · | · | · | · | ✅ | · | · | · | · | · | · | ✅ |
| **S5 PRE_REGISTERED** | · | · | · | · | · | ✅ | · | · | · | · | · | ✅ |
| **S6 DEVELOPMENT_EXECUTED** | · | · | · | · | · | · | ✅ | · | ✅ | · | ✅ | · |
| **S7 ROBUSTNESS_EXECUTED** | · | · | · | · | · | · | · | ✅ | ✅ | · | ✅ | · |
| **S8 OOS_EXECUTED** | · | · | · | · | · | · | · | · | ✅ | ✅ | ✅ | · |
| **S9 NOT_ESTABLISHED** | · | · | · | · | · | · | · | · | · | · | · | · |
| **S10 ESTABLISHED** | · | · | · | · | · | · | · | · | · | · | · | · |
| **S11 INCONCLUSIVE** | · | · | · | · | · | · | · | · | · | · | · | · |
| **S12 DEFERRED** | · | · | · | ✅ | · | · | · | · | · | · | · | · |

合法转换的冻结计数为 **20** 条，按用途分组列举以便核对：

```text
执行前链        4 条   S1→S2, S2→S3, S3→S4, S4→S5
预注册与执行链  3 条   S5→S6, S6→S7, S7→S8
搁置            5 条   S1→S12, S2→S12, S3→S12, S4→S12, S5→S12
恢复            1 条   S12→S4
执行期提前终止  6 条   S6→S9, S6→S11, S7→S9, S7→S11, S8→S9, S8→S11
终局判定        1 条   S8→S10
合计           20 条
```

冻结要求：**矩阵是唯一真源**。实现必须以第 7.2 节矩阵逐格定义合法边，并在测试中机器核对
“矩阵展开得到的合法边集合”恰好等于上表 20 条（既不多也不少）；不得以“默认允许”分支实现。
上表仅用于交叉核对，任何与矩阵不一致的表述以矩阵为准。

### 7.3 转换前置条件（`StateTransitionRequestV1`）

拟议转换请求的字段（精确键集，未知键 `UNKNOWN_RECORD_FIELD`）：

```text
{ "hypothesis_id": <必须等于记录>, "hypothesis_version": <必须等于记录>,
  "from_state": <必须等于记录当前 status>,
  "to_state": <目标状态>,
  "reason_code": <封闭枚举>,
  "authorization_ref": <str 或 null>,
  "evidence_kind": <str 或 null> }
```

`reason_code` 封闭词表（拟议）：

```text
SOURCE_REVIEWED, FEASIBILITY_ASSESSED, CANDIDATE_REGISTERED, PRE_REGISTRATION_REGISTERED,
DEVELOPMENT_COMPLETED, ROBUSTNESS_COMPLETED, OOS_COMPLETED, EVIDENCE_NOT_SUPPORTED,
EVIDENCE_SUPPORTED, EVIDENCE_INCONCLUSIVE, DEFERRED_BY_REVIEW
```

`evidence_kind` 封闭词表（拟议，仅执行期转换可非 null）：

```text
FROZEN_DEVELOPMENT_EVIDENCE, REGISTERED_ROBUSTNESS_EVIDENCE, INDEPENDENT_OOS_EVIDENCE
```

逐条前置条件（全部必须满足，任一不满足即 `ILLEGAL_STATE_TRANSITION` 或更专门的错误码）：

| # | 转换 | 前置条件 | 额外要求 |
| --- | --- | --- | --- |
| P1 | 任意合法转换 | `from_state == 记录.status`；`(hypothesis_id, hypothesis_version)` 等于记录 | `reason_code` 与转换相容（第 7.3.1 节） |
| P2 | → `LITERATURE_REVIEWED` | 来源身份五要素齐备且非禁止来源 | `reason_code = SOURCE_REVIEWED` |
| P3 | → `A_SHARE_FEASIBILITY_REVIEWED` | `a_share_data_feasibility != UNKNOWN` **或** `free_data_feasibility != UNKNOWN` | `reason_code = FEASIBILITY_ASSESSED` |
| P4 | → `NOT_TESTED`（含自 `DEFERRED` 恢复） | 无额外要求（休息态不要求证据） | `reason_code ∈ {CANDIDATE_REGISTERED, DEFERRED_BY_REVIEW}` |
| P5 | → `PRE_REGISTERED` | 记录已处于 `NOT_TESTED`；`reason_code = PRE_REGISTRATION_REGISTERED` | 不要求 `authorization_ref`（预注册不执行） |
| P6 | → `DEVELOPMENT_EXECUTED` | `authorization_ref` 非空且形如既有研究合同身份（64 位小写十六进制或标识符）；`evidence_kind = FROZEN_DEVELOPMENT_EVIDENCE` | 合同 `execution_boundary` 的落点 |
| P7 | → `ROBUSTNESS_EXECUTED` | 已存在 `DEVELOPMENT_EXECUTED` 历史项；`authorization_ref` 非空；`evidence_kind = REGISTERED_ROBUSTNESS_EVIDENCE` | 注册稳健性必须已注册 |
| P8 | → `OOS_EXECUTED` | 已存在 `DEVELOPMENT_EXECUTED` 与 `ROBUSTNESS_EXECUTED` 历史项；`authorization_ref` 非空；`evidence_kind = INDEPENDENT_OOS_EVIDENCE` | 独立 OOS |
| P9 | → `ESTABLISHED` | 第 7.5 节完整证据门 | `reason_code = EVIDENCE_SUPPORTED` |
| P10 | → `NOT_ESTABLISHED` | 已存在至少一个执行期历史项 | `reason_code = EVIDENCE_NOT_SUPPORTED` |
| P11 | → `INCONCLUSIVE` | 已存在至少一个执行期历史项 | `reason_code = EVIDENCE_INCONCLUSIVE` |
| P12 | → `DEFERRED` | 当前状态 ∈ 执行前五态；`reason_code = DEFERRED_BY_REVIEW` | 执行期与终态不可搁置 |
| P13 | 执行期转换 | `authorization_ref` 缺失或为 `null` → `MISSING_AUTHORIZATION_REF`（**先于** `ILLEGAL_STATE_TRANSITION` 报出） | 合同 `execution_boundary` 的机械保证 |
| P14 | 终态转出 | 从 S9/S10/S11 出发的任何转换 → `TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION` | 见 7.6 |

#### 7.3.1 `reason_code` 与转换的相容表（冻结）

| 转换类别 | 允许的 `reason_code` |
| --- | --- |
| → S2 | `SOURCE_REVIEWED` |
| → S3 | `FEASIBILITY_ASSESSED` |
| → S4 | `CANDIDATE_REGISTERED`（首次）或 `DEFERRED_BY_REVIEW`（自 S12 恢复） |
| → S5 | `PRE_REGISTRATION_REGISTERED` |
| → S6 | `DEVELOPMENT_COMPLETED` |
| → S7 | `ROBUSTNESS_COMPLETED` |
| → S8 | `OOS_COMPLETED` |
| → S9 | `EVIDENCE_NOT_SUPPORTED` |
| → S10 | `EVIDENCE_SUPPORTED` |
| → S11 | `EVIDENCE_INCONCLUSIVE` |
| → S12 | `DEFERRED_BY_REVIEW` |

不相容组合 → `ILLEGAL_STATE_TRANSITION`。`reason_code` 是叙述性代码，**不得**承载结果值：
它不是 disposition，也不是 evidence level，不存在“`EVIDENCE_SUPPORTED` 表示统计显著”的语义；
它只表示“本次转换的登记原因”。

### 7.4 不可跳过的边界（non-skippable）

```text
B1  执行前五态必须逐级前进：S1→S2→S3→S4→S5，不允许跳过任一格。
    例：S1→S4、S2→S5、S3→S5 全部非法。
B2  进入执行必须自 S5：S6 的前驱只能是 S5。
B3  执行期必须逐级前进：S6→S7→S8，不允许 S6→S8（缺注册稳健性）。
B4  终局判定只能自 S8：S9/S10/S11 的前驱（在判定意义上）只能是 S8。
    S6→S9、S6→S11、S7→S9、S7→S11 是“执行期提前终止”的合法边（第 7.2 节矩阵），
    但它们**不**通向 S10；只有 S8→S10 存在。
B5  执行状态不可回退：从任何执行期状态或终态回到 S1–S5 的转换不存在。
B6  S12 只能恢复到 S4，不能恢复到它被搁置时的状态；被搁置时的状态保留在 `state_history` 中。
B7  `ESTABLISHED` 没有自环、没有其它入边（唯一入边是 S8→S10）。
```

### 7.5 `ESTABLISHED` 门（完整证据链，fail-closed）

`to_state = ESTABLISHED` 的转换必须**同时**满足下列全部条件，否则
`ESTABLISHED_EVIDENCE_INCOMPLETE`：

```text
E1  state_history 中存在 to_state = DEVELOPMENT_EXECUTED 的项，
    且该项 evidence_kind = FROZEN_DEVELOPMENT_EVIDENCE 且 authorization_ref 非空；
E2  state_history 中存在 to_state = ROBUSTNESS_EXECUTED 的项，位于 E1 之后，
    且该项 evidence_kind = REGISTERED_ROBUSTNESS_EVIDENCE 且 authorization_ref 非空；
E3  state_history 中存在 to_state = OOS_EXECUTED 的项，位于 E2 之后，
    且该项 evidence_kind = INDEPENDENT_OOS_EVIDENCE 且 authorization_ref 非空；
E4  记录当前 status 恰为 OOS_EXECUTED；
E5  E1/E2/E3 的三项 authorization_ref 指向**三份不同的**冻结合同身份（互不相同）；
E6  reason_code = EVIDENCE_SUPPORTED，且 state_history 中不存在先前以
    EVIDENCE_NOT_SUPPORTED 或 EVIDENCE_INCONCLUSIVE 结束的判定项。
```

冻结声明：`E1`–`E6` 是**登记层**的完备性门，不是统计判定门。它们只检查“是否存在适用的冻结开发、
注册稳健性与独立 OOS 证据**的登记项与授权身份**”，不检查、不计算、不解释任何统计量。
“证据是否真的支持”由**另行授权的** M4-A 证据策略在 registry 之外判定；
registry 不得把“登记齐备”表述为“已被证明”。`ESTABLISHED` 也**不等于**可交易、可推荐或可分配资金。

### 7.6 禁止的回归与提升（明确列举）

```text
N1  任何终态（S9/NOT_ESTABLISHED、S10/ESTABLISHED、S11/INCONCLUSIVE）没有出边：
    不存在“翻案”“撤销判定”“从 NOT_ESTABLISHED 提升到 ESTABLISHED”的路径。
N2  S9/S11 → S10 的转换在矩阵中不存在，因此“不显著改判为显著”不可表达。
N3  执行期状态不可回退到执行前状态；不存在“重置后重跑”的路径。
N4  不存在“跳过预注册直接执行”的路径（B2）。
N5  不存在“未执行即判定”的路径：S9/S11 要求至少一个执行期历史项。
N6  同一 (hypothesis_id, hypothesis_version) 内的身份承载字段不可改写；
    需要重做研究必须提升 hypothesis_version 形成新记录（第 4.4 节）。
N7  转换不改变 identity_digest；任何试图改写身份承载字段的转换必须失败
    （`PROVENANCE_REWRITE`）。
```

### 7.7 `state_history` 元素（拟议 `StateTransitionV1`）

```text
{ "ordinal": <1 起连续整数>, "from_state": <十二状态之一或 null>,
  "to_state": <十二状态之一>,
  "reason_code": <封闭枚举>, "authorization_ref": <str 或 null>,
  "evidence_kind": <str 或 null> }
```

冻结规则：

- `ordinal` 必须从 1 开始连续递增（1,2,3,...），不得跳号或重复；
- 第 1 项的 `from_state` 必须为 `null`（登记起点），其余项必须等于前一项的 `to_state`；
- 末项的 `to_state` 必须等于记录 `status`；
- 每一项的 `(from_state, to_state)` 必须命中第 7.2 节矩阵中的合法格；
- `authorization_ref` 与 `evidence_kind` 仅在执行期转换（to_state ∈ S6/S7/S8）上非空；
  其余转换必须为 `null`（含值即 `INVALID_FIELD_TYPE`）；
- 执行期转换（to_state ∈ S6/S7/S8）的 `authorization_ref` 缺失或为 `null` → `MISSING_AUTHORIZATION_REF`；
  执行期转换的 `evidence_kind` 缺失、为 `null` 或不等于该转换对应的证据种类（P6–P8）→
  `ILLEGAL_STATE_TRANSITION`（前置条件未满足；本设计不新增错误码，且该选择已冻结，见 AC-17(17e)）；
- `state_history` 只增不改：一次转换只在末尾追加一项，历史项不得编辑或删除。

## 8. 验证顺序与稳定错误码（冻结项 5）

### 8.1 冻结验证顺序（首错即停，fail-closed）

拟议入口 `validate_hypothesis_record(record)`（以及 `parse_hypothesis_record(document)` 内部）
必须按下列顺序求值；编号是稳定标识，验收场景按此引用。**顺序本身是契约**：
先报出的错误必须是下表顺序中的第一个失败项，不得因实现细节改变首错。

| 阶段 | 检查内容 | 主要错误码 |
| --- | --- | --- |
| `V1` | 对象形状：顶层必须是记录类型（冻结 dataclass）或映射；容器必须是 `tuple`；不得是 `dict`/`list`/`set`/标量 | `INVALID_RECORD_STRUCTURE` |
| `V2` | 键集：缺失键、额外键、嵌套对象键集 | `MISSING_REQUIRED_FIELD` / `UNKNOWN_RECORD_FIELD` |
| `V3` | 逐字段类型严格性：`str` 不得是 `bool`/`int`；`int` 不得是 `bool`/`float`/`str`；元组元素类型；`null` 只允许在声明位置；公共文本规则（第 4.2 节） | `INVALID_FIELD_TYPE` |
| `V4` | 标识符与长度：`hypothesis_id` 正则、各字段长度边界、`hypothesis_version` 范围 | `INVALID_IDENTIFIER` / `INVALID_FIELD_LENGTH` |
| `V5` | 枚举成员：`source_type`、`expected_direction`、两个可行性、`status`、`reason_code`、`evidence_kind` | `UNKNOWN_SOURCE_TYPE` / `INVALID_ENUM_VALUE` |
| `V6` | 日期：`source_date` 形态与公历有效性 | `INVALID_DATE` |
| `V7` | 来源与出处：`required_identity` 五要素完备；禁止来源拒绝；来源类型专属最低要求 | `MISSING_PROVENANCE_FIELD` / `FORBIDDEN_CANONICAL_SOURCE` |
| `V8` | 禁止结果/统计与环境/选择键的**递归**扫描；禁止值扫描（绝对路径、凭据形态） | `FORBIDDEN_OUTCOME_FIELD` / `FORBIDDEN_ENVIRONMENT_FIELD` / `FORBIDDEN_VALUE` |
| `V9` | `state_history` 内部一致性：ordinal 连续、from/to 链接、末项等于 status、空值位置 | `STATE_HISTORY_INCONSISTENT` |
| `V10` | 转换合法性与前置条件：矩阵命中、reason 相容、`authorization_ref` 要求、`ESTABLISHED` 门、终态无出边 | `ILLEGAL_STATE_TRANSITION` / `MISSING_AUTHORIZATION_REF` / `ESTABLISHED_EVIDENCE_INCOMPLETE` / `TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION` |
| `V11` | 摘要自洽：重算 `identity_digest`、`record_digest` 并逐字符比较 | `IDENTITY_DIGEST_MISMATCH` / `RECORD_DIGEST_MISMATCH` |
| `V12` | 快照级：身份键重复判定（同 `identity_digest` → 重复登记；不同 `identity_digest` → 身份改写）、规模门 | `DUPLICATE_HYPOTHESIS_ID` / `PROVENANCE_REWRITE` / `SCALE_LIMIT_EXCEEDED` |

`V12` 内部顺序同样冻结：先做身份键重复判定（两条同身份键记录 `identity_digest` 相同 →
`DUPLICATE_HYPOTHESIS_ID`；不同 → `PROVENANCE_REWRITE`），再做规模门
（`SCALE_LIMIT_EXCEEDED`）。同一身份键不会同时得到两个码。

顺序理由（必须保留）：结构先于取值（`V1` < `V3`）、键集先于取值（`V2` < `V3`）、
取值先于枚举（`V4` < `V5`）、来源完整性先于结果键扫描（`V7` < `V8`，来源错误不得被
“顺带发现的结果键”掩盖）、状态一致性先于转换合法性（`V9` < `V10`）、
合法性先于摘要（`V10` < `V11`，非法转换不得被报成摘要不匹配）、
单记录先于快照（`V11` < `V12`）。

### 8.2 稳定错误码表（拟议，封闭）

全部挂在拟议 `RegistryError(ValueError)` 上，异常携带 `code` 属性；`str(exc)` 至少包含 `code`。
实现不得新增同类错误码，不得更改现有码的语义。

| 错误码 | 触发条件 | 阶段 |
| --- | --- | --- |
| `INVALID_RECORD_STRUCTURE` | 顶层形状/容器类型错误 | V1 |
| `MISSING_REQUIRED_FIELD` | 必需键缺失 | V2 |
| `UNKNOWN_RECORD_FIELD` | 额外键或未知嵌套键 | V2 |
| `INVALID_FIELD_TYPE` | 类型不匹配、`bool`/`int` 混用、`null` 出现在非可空位置 | V3 |
| `INVALID_FIELD_LENGTH` | 长度越界 | V4 |
| `INVALID_IDENTIFIER` | `hypothesis_id` 不匹配标识符规则；`authorization_ref` 形态非法 | V4 |
| `UNKNOWN_SOURCE_TYPE` | `source_type` 不在六类词表 | V5 |
| `INVALID_ENUM_VALUE` | 其它枚举字段越界 | V5 |
| `INVALID_DATE` | `source_date` 形态或公历无效 | V6 |
| `MISSING_PROVENANCE_FIELD` | `required_identity` 五要素之一缺失或为空（`source_notes` 的空串合法） | V7 |
| `FORBIDDEN_CANONICAL_SOURCE` | 命中合同冻结的三类禁止来源 | V7 |
| `FORBIDDEN_OUTCOME_FIELD` | 出现系数/区间/p 值/处置等结果或统计键 | V8 |
| `FORBIDDEN_ENVIRONMENT_FIELD` | 出现主机/路径/会话/环境/选择/排序/提升类键 | V8 |
| `FORBIDDEN_VALUE` | 值形态非法：绝对路径、凭据形态、BOM/控制字符逃逸 | V8 |
| `STATE_HISTORY_INCONSISTENT` | ordinal 跳号、链接断裂、末项不等于 status、空值位置错误 | V9 |
| `ILLEGAL_STATE_TRANSITION` | 矩阵外转换、reason 不相容、前置条件不满足 | V10 |
| `MISSING_AUTHORIZATION_REF` | 执行期转换缺少 `authorization_ref` | V10 |
| `ESTABLISHED_EVIDENCE_INCOMPLETE` | `ESTABLISHED` 门 E1–E6 任一不满足 | V10 |
| `TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION` | 从 S9/S10/S11 出发的转换 | V10 |
| `IDENTITY_DIGEST_MISMATCH` | `identity_digest` 重算不一致 | V11 |
| `RECORD_DIGEST_MISMATCH` | `record_digest` 重算不一致 | V11 |
| `DUPLICATE_HYPOTHESIS_ID` | 快照内同一 `(hypothesis_id, hypothesis_version)` 出现两条 `identity_digest` **相同**的记录 | V12 |
| `PROVENANCE_REWRITE` | 同一身份键出现**不同** `identity_digest`（改写既有身份），含经转换入口改写身份承载字段 | V10 / V12 |
| `SCALE_LIMIT_EXCEEDED` | real-demo 候选数 > `MAX_REAL_DEMO_CANDIDATES`，或记录数 > `MAX_RECORDS_PER_SNAPSHOT` | V12 |
| `NON_CANONICAL_SERIALIZATION` | BOM/CR/结尾换行/数字 token 形态违反 S1–S7 | 反序列化入口 |
| `UNSUPPORTED_REGISTRY_OPERATION` | 请求本设计未定义的 registry 操作（扫描/排序/提升/自动扩展等） | 公开面层 |
| `REAL_CANDIDATE_DATASET_NOT_AUTHORIZED` | 请求创建或加载真实候选数据集 | 公开面层 |

### 8.3 fail-closed 与类型严格（无强制转换）

```text
T1  不强制转换：`"1"` 不得被接受为 `hypothesis_version`；`1.0` 不得被接受为整数；
    `True` 不得被接受为整数 1；`None` 不得被替换为默认值；缺失键不得被补默认值。
T2  不静默截断：超长文本失败，不截断；不去除首尾空白；不做大小写或 Unicode 规范化。
T3  不忽略：未知键、未知枚举词、未知 reason 一律失败，绝不忽略或降级。
T4  无部分写入：验证失败时不返回部分记录、不修改输入对象、不追加历史项、不写出字节。
T5  无歧义重复 ID：同一身份键必须失败且只报一个码——两条 `identity_digest` 相同 →
    `DUPLICATE_HYPOTHESIS_ID`；不同 → `PROVENANCE_REWRITE`；不做“后写覆盖”或“先写保留”。
T6  无默认值表：除第 4.2 节明确的“允许空元组/允许空备注”外，不存在字段默认值。
T7  异常不吞：既有 `HypothesisConfigError` 等上游异常如需传播则原样传播，
    不包装成 registry 错误码，也不被 `except Exception` 静默吞掉。
```

### 8.4 幂等再验证（冻结）

- `validate_hypothesis_record(record)` 必须是**纯函数**：同一记录重复调用返回相同结果，
  不修改记录，不产生副作用，不读写文件/环境/时钟；
- `parse_hypothesis_record(serialize_hypothesis_record(record))` 必须得到与输入
  **规范字典相等**的记录（往返幂等）；
- 再次验证一条已验证记录不得改变其 `identity_digest`/`record_digest`；
- 幂等性不依赖缓存：不得实现“已验证标记”短路，否则会掩盖后续篡改。

## 9. registry 元数据与研究结果产物的机械分离（冻结项 6）

### 9.1 禁止结果/统计键（冻结集合，递归求值）

`validate_hypothesis_record` 的 V8 阶段对整个记录（含元组元素文本之外的**所有键**）做递归键扫描，
键名比较口径：转为小写、去除 `-`/`_`/空格后再比较。命中即 `FORBIDDEN_OUTCOME_FIELD`。
该集合必须**至少**包含：

```text
# 既有冻结集合（mechanism/contracts.py::RESTRICTED_RESEARCH_OUTPUT_KEYS）的全部成员
abnormal_return, alpha, beta, bootstrap_result, confidence_interval, correlation,
crash_day_count, effect_size, evidence_level, gamma, p_value, positive_probability

# 本设计追加的结果/统计族
coefficient, coefficients, coef, se, std_error, t_stat, t_statistic, z_stat,
estimate, point_estimate, ci, ci_lower, ci_upper, interval, confidence,
significance, significant, pvalue, p, f_stat, r_squared, adj_r_squared,
disposition, verdict, conclusion, finding, findings, result, results,
outcome, outcomes, return, returns, excess_return, abnormal_returns,
pnl, profit, sharpe, drawdown, hit_rate, win_rate, turnover,
evidence, proof, confirmed, validated, verified, robust_result,
rank, ranking, score, scores, best, best_result, selected, winner
```

### 9.2 禁止环境/选择键（冻结集合，递归求值）

必须**至少**包含既有
`mechanism/execution/bounded.py::FORBIDDEN_KEYS` 的全部成员，即
`cwd`、`worktree`、`hostname`、`username`、`user`、`home`、`abspath`、`absolute_path`、
`root_path`、`env`、`environment`、`path`、`session`、`best`、`best_result`、`best_id`、
`selected`、`selected_id`、`winner`、`aggregate`、`ranking`、`optimize`、`tuned`、`search`；
命中即 `FORBIDDEN_ENVIRONMENT_FIELD`。

### 9.3 禁止值形态（冻结）

| 值形态 | 判定 | 错误码 |
| --- | --- | --- |
| 绝对路径（Windows 盘符、UNC、POSIX 绝对路径） | 值扫描（复刻既有 `_ABSOLUTE_PATH_RE` 语义） | `FORBIDDEN_VALUE` |
| 凭据形态（`api_key`、`token`、`secret`、`cookie`、`password` 之类的键或 `Bearer ` 值） | 键扫描 + 值扫描 | `FORBIDDEN_VALUE` |
| 数字结果文本（形如 `p=0.03`、`t=2.1`、`IC=0.05`、`sharpe 1.2`） | **不做**通用正则判定（会误伤合法文本）；改为在实现阶段由显式常量词表覆盖，并在验收场景中给出正反例 | 见第 15 节风险 R2 |
| `null` 出现在非可空位置 | 类型检查 | `INVALID_FIELD_TYPE` |

### 9.4 registry 与 M4-A 产物的关系（冻结）

```text
D1  registry 记录不引用、不包含、不派生任何 M4-A 执行产物的字段或摘要；
    `authorization_ref` 只登记**合同身份**，不登记结果。
D2  M4-A 执行产物不得写入 registry 记录；两者不共享可变状态。
D3  registry 的公开面没有任何“读取结果”或“导入结果”的入口。
D4  registry 不可被用作推荐系统的输入：`NOT_TESTED cannot enter recommendation system`
    在本文中由“不存在推荐/排序/提升入口”结构性保证（第 10.2 节）。
D5  registry 记录不得被描述为证据、发现或结论；`INTERPRETATION_BOUNDARY` 常量必须在
    实现阶段作为快照级字面量出现（第 11.2 节），使任何导出的元数据都自带该边界声明。
```

## 10. 规模语义与禁止行为（冻结项 7）

### 10.1 `MAX_REAL_DEMO_CANDIDATES = 3` 的精确语义

```text
SC1  real_demo_candidate(record) := record.a_share_data_feasibility ∈ {FEASIBLE_FREE, FEASIBLE_PAID}
SC2  count_real_demo_candidates(snapshot) := |{ r ∈ snapshot.records : real_demo_candidate(r) }|
SC3  合法当且仅当 count_real_demo_candidates(snapshot) <= MAX_REAL_DEMO_CANDIDATES (3)
SC4  违反 → SCALE_LIMIT_EXCEEDED（V12），快照整体失败，不产生部分快照
SC5  规模门与 `status` 无关：把记录改为 NOT_ESTABLISHED / DEFERRED 不减少计数，
     因此规模不可被状态操作规避
SC6  规模门与 `source_type` 无关、与结果无关、与排序无关
SC7  `MAX_RECORDS_PER_SNAPSHOT = 3` 同时限制快照记录总数，使“塞入非 real-demo 记录”
     不可绕过 SC3
SC8  该上限是**天花板**，不是目标：本设计不要求、不鼓励达到 3 条；
     创建任何真实候选仍需单独授权（`real_registry_dataset_authorized=false`）
```

### 10.2 强制禁令（结构性，而非约定）

| 禁令 | 机械保证 |
| --- | --- |
| 自动异常扫描（`AUTOMATED_ANOMALY_SCAN = PROHIBITED`） | 公开面无扫描入口；无 `scan`/`mine`/`screen`/`discover_all` 名称；任何此类请求 → `UNSUPPORTED_REGISTRY_OPERATION` |
| 回测排序（`BACKTEST_RANKING = PROHIBITED`） | 公开面无排序/排名入口；快照的规范顺序只按 `(hypothesis_id, hypothesis_version)`，与任何收益或结果无关 |
| 按收益排序 | 记录中不存在收益字段（第 9.1 节禁止键）；公开入口不接受排序键或收益序列参数 |
| 候选自动提升 | 状态只能经第 7 节显式转换前进；无 `promote`/`auto_*`/`advance_all` 入口；`ESTABLISHED` 需完整证据门 |
| 自动扩展 | 无“全部注册项”开关；每次转换是单记录、显式、带 `reason_code` 的请求 |
| 参数自动生成/调优 | registry 记录不含参数值；无 `tune`/`optimize`/`search` 入口（亦在禁止键集合中） |
| 真实候选数据集 | 本设计不定义加载真实数据的入口；请求即 `REAL_CANDIDATE_DATASET_NOT_AUTHORIZED` |

实现阶段必须在测试中以**结构性断言**证明上述禁令：公开面名称集合、
`inspect.signature` 无 `VAR_KEYWORD`、`registry/**` 无 pandas/numpy/duckdb/provider 导入、
无 `open`/`Path.read_text`/`os.environ` 调用面。

## 11. 拟议实现落点与公开接口（冻结项 8）

### 11.1 拟议模块布局

```text
src/ashare_research/mechanism/registry/__init__.py    # 公开重导出 + __all__（拟议）
src/ashare_research/mechanism/registry/records.py     # schema、V1–V8、V11、规范序列化与摘要（拟议）
src/ashare_research/mechanism/registry/states.py      # 十二状态、转换矩阵、V9–V10、ESTABLISHED 门（拟议）
src/ashare_research/mechanism/registry/snapshot.py    # 快照、V12、规模门、规范快照序列化（拟议）
```

布局约束（全部为冻结要求）：

- 必须匹配既有子包模式：`mechanism/<subpkg>/__init__.py` 显式重导出并声明 `__all__`
  （既有 `datasets/`、`execution/`、`planning/` 均如此）；
- **不得**新增任何顶层 `src/ashare_research/mechanism/*.py` 文件：顶层 `mechanism/*` 聚合
  受既有治理测试保护（`test_m3_protected_aggregates_are_byte_identical` 的 mechanism 作用域）；
- **不得**创建 `src/ashare_research/m4`，**不得**创建 `knowledge/`，**不得**创建
  `src/ashare_research/engine.py`（既有 `test_no_m4_production_surface_was_created` 保护）；
- 不得新增数据库 schema、迁移或存储后端；本设计只定义内存记录与快照；
- 不得新增依赖、工作流或配置项。

### 11.2 拟议公开签名（本轮冻结）

```text
# 拟议新包：ashare_research.mechanism.registry
parse_hypothesis_record(document) -> HypothesisRecordV1
hypothesis_record_to_canonical_dict(record) -> dict            # 独立副本，纯 JSON
serialize_hypothesis_record(record) -> bytes                   # 规范字节
validate_hypothesis_record(record) -> None
hypothesis_record_identity_digest(record) -> str
hypothesis_record_digest(record) -> str

transition_hypothesis_record(record, request) -> HypothesisRecordV1   # 返回新记录
validate_state_transition(record, request) -> None

build_hypothesis_registry_snapshot(records) -> HypothesisRegistrySnapshotV1
registry_snapshot_to_canonical_dict(snapshot) -> dict
serialize_hypothesis_registry_snapshot(snapshot) -> bytes
validate_hypothesis_registry_snapshot(snapshot) -> None
count_real_demo_candidates(snapshot) -> int
```

共 **13** 个公开入口。硬性要求：

- 不存在名为 `execute`、`run`、`scan`、`rank`、`sort`、`promote`、`advance`、`select`、
  `optimize`、`search`、`auto_*` 的入口；
- 不存在只吃 `hypothesis_id` 的“裸查询后写入”入口；转换必须同时给出记录与带
  `from_state` 的完整请求（乐观并发：`from_state` 不匹配即失败）；
- 任何入口都**不得**声明 `**kwargs`：未声明的关键字参数（如 `returns=`、`outcome=`、
  `sort_key=`、`real_data=`、`holdout=`）必须是 `TypeError`；
- 全部入口 IO-free：不访问文件、路径、环境、时钟、网络、provider、数据库或 holdout；
- `HypothesisRegistrySnapshotV1` 是**不可变**快照：构造后只读，`records` 为按
  `(hypothesis_id, hypothesis_version)` 升序排列的 `tuple`；
- 快照的规范字典必须包含 `registry_schema_version`、`registry_version`、
  `digest_algorithm`、`interpretation_boundary`（`INTERPRETATION_BOUNDARY` 字面量）、
  `records`、`real_demo_candidate_count`、`registry_digest`；
- `registry_digest = canonical_digest(<快照载荷，排除 registry_digest 本身>)`；
- 私有实现细节（例如 `_transition_matrix`、`_forbidden_outcome_keys`、`_scan_keys`）
  不得导出、不得作为验收入口、不得被文档描述为 API。

### 11.3 导入边界（冻结）

允许的导入（白名单，拟议）：

```text
标准库：json, re, hashlib（经既有 canonical_digest 间接使用）, dataclasses, enum,
        datetime.date（仅用于 source_date 公历校验）, typing, collections.abc
仓内：ashare_research.mechanism.model_digest.canonical_digest
      （唯一摘要实现，执行层亦从此处导入）
```

明确禁止的导入：

```text
pandas, numpy, duckdb, pyarrow, statsmodels, yaml（记录不是配置文件）
ashare_research.mechanism.planning*
ashare_research.mechanism.datasets*
ashare_research.mechanism.execution*
ashare_research.mechanism.regression / bootstrap / robustness / evidence / crash /
  analysis_contracts / contract_compiler / contracts / model_digest（除 canonical_digest 外）
任何 provider、数据库或网络模块；任何 M3 绑定模块
```

理由：registry 是**纯元数据**层，必须能在没有数据底座、没有 provider、没有统计栈的环境下
独立验证；把 M3/M4-A 模块拉进导入图会把“登记来源”与“读取结果”在结构上混在一起。
注意：本白名单使 registry **不**复用 `hypothesis_config` 的私有 `_IDENTIFIER_RE`
（下划线前缀为私有），因此 `hypothesis_id` 的规则必须在 `records.py` 中以**同一正则字面量**
独立声明；实现阶段必须在验收中机械断言该字面量与既有规则一致
（`records._IDENTIFIER_RE.pattern == hypothesis_config._IDENTIFIER_RE.pattern`），
以避免两套标识符规则漂移。

### 11.4 公开面之外的拒绝面（结构性，而非约定）

```text
真实候选数据集请求     -> 无入口；REAL_CANDIDATE_DATASET_NOT_AUTHORIZED
扫描/排序/提升请求     -> 无入口；UNSUPPORTED_REGISTRY_OPERATION / TypeError
holdout 参数           -> 不存在（TypeError）
真实数据/provider 参数 -> 不存在（TypeError）
结果/统计参数          -> 不存在（TypeError）
“设置 status”入口      -> 不存在：只有带 from_state 的显式转换入口
```

## 12. 合成/示意示例（冻结项 9）

以下示例**全部是示意**，不是真实候选、不是真实引用、不是真实数据集，也不得被复制到任何
数据文件。它们只用于固定 schema 的形态与规范序列化的形状。

### 12.1 示意记录（合成，`DISCOVERED`）

```json
{"authors_or_issuer":"SYNTHETIC_EXAMPLE_ISSUER","a_share_data_feasibility":"FEASIBLE_FREE",
 "candidate_signal":"SYNTHETIC_EXAMPLE_SIGNAL_TEXT","citation_or_source_identity":"SYNTHETIC_EXAMPLE_IDENTITY",
 "expected_direction":"TWO_SIDED","free_data_feasibility":"PARTIAL","hypothesis_id":"SYNTH_EXAMPLE_0001",
 "hypothesis_version":1,"identity_digest":"<64 hex>","known_alternative_explanations":["SYNTHETIC_EXAMPLE_ALT"],
 "known_controls":[],"known_failures_or_decay":[],"known_replications":[],
 "original_market":"SYNTHETIC_EXAMPLE_MARKET","original_sample":"SYNTHETIC_EXAMPLE_SAMPLE",
 "record_digest":"<64 hex>","schema_version":"M4_HYPOTHESIS_REGISTRY_RECORD_V1",
 "source_date":"2000-01","source_notes":"SYNTHETIC_EXAMPLE_NOTES","source_title":"SYNTHETIC_EXAMPLE_TITLE",
 "source_type":"TEXTBOOK_THEORY","source_version":"SYNTHETIC_EXAMPLE_EDITION",
 "state_history":[{"authorization_ref":null,"evidence_kind":null,"from_state":null,"ordinal":1,
   "reason_code":"SOURCE_REVIEWED","to_state":"DISCOVERED"}],
 "status":"DISCOVERED","target_horizon":"SYNTHETIC_EXAMPLE_HORIZON","theory":"SYNTHETIC_EXAMPLE_THEORY"}
```

说明：`state_history` 的首项 `from_state` 为 `null`；`to_state` 等于 `status`；
`identity_digest`/`record_digest` 在示例中以占位符表示，**不得**在文档中写死具体数值——
任何写死的摘要都会把文档变成伪证据。实现阶段必须由真实实现产出。

### 12.2 示意合法转换序列（合成）

```text
DISCOVERED --SOURCE_REVIEWED--> LITERATURE_REVIEWED
LITERATURE_REVIEWED --FEASIBILITY_ASSESSED--> A_SHARE_FEASIBILITY_REVIEWED
A_SHARE_FEASIBILITY_REVIEWED --CANDIDATE_REGISTERED--> NOT_TESTED
NOT_TESTED --PRE_REGISTRATION_REGISTERED--> PRE_REGISTERED
PRE_REGISTERED --DEVELOPMENT_COMPLETED(auth=frozen A contract id)--> DEVELOPMENT_EXECUTED
DEVELOPMENT_EXECUTED --ROBUSTNESS_COMPLETED(auth=...)--> ROBUSTNESS_EXECUTED
ROBUSTNESS_EXECUTED --OOS_COMPLETED(auth=...)--> OOS_EXECUTED
OOS_EXECUTED --EVIDENCE_SUPPORTED--> ESTABLISHED
```

该序列只是**登记路径示意**：它证明 `ESTABLISHED` 需要三项授权身份齐备，
**不**表示该路径已被执行、被授权，也不表示任何机制成立。

### 12.3 示意非法序列（合成，必须失败）

```text
DISCOVERED --DEVELOPMENT_COMPLETED--> DEVELOPMENT_EXECUTED
  → ILLEGAL_STATE_TRANSITION（跳过 S2/S3/S4/S5；且 authorization_ref 为 null）
OOS_EXECUTED --EVIDENCE_SUPPORTED--> ESTABLISHED（缺失 DEVELOPMENT/ROBUSTNESS 历史项）
  → ESTABLISHED_EVIDENCE_INCOMPLETE
NOT_ESTABLISHED --EVIDENCE_SUPPORTED--> ESTABLISHED
  → TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION（终态无出边）
DEFERRED --CANDIDATE_REGISTERED--> A_SHARE_FEASIBILITY_REVIEWED
  → ILLEGAL_STATE_TRANSITION（S12 只能恢复到 NOT_TESTED）
```

## 13. 可追溯性与授权语义（冻结项 10）

### 13.1 可追溯性

- 来源可追溯：`source_type` + `citation_or_source_identity` + `source_version` +
  `source_title` + `authors_or_issuer` + `source_date` 六元组必须在整条记录生命周期内保持不变
  （`identity_digest` 强制）；
- 版本可追溯：`hypothesis_version` 单调递增形成新记录，旧版本同时保留，不删除、不覆盖；
- 理论可追溯：`theory` 是身份承载字段，注册后不可改写；
- 判定可追溯：`state_history` 只增不改，每次转换的 `reason_code` 与（执行期的）
  `authorization_ref` 永久保留，因此“谁在什么授权下把候选推进到哪一步”可回答；
- 不可追溯的内容**不进入** registry：结果、统计量、参数值、文件位置、运行环境。

### 13.2 授权矩阵（冻结）

| 能力 | 本设计 | 需要的单独授权 |
| --- | --- | --- |
| 冻结 M4-B 设计（本文） | ✅ 已交付 | — |
| 实现 `mechanism/registry/**` | ❌ 禁止 | 实现 Goal + 用户授权 |
| 创建真实候选数据集 | ❌ 禁止 | 单独授权（`real_registry_dataset_authorized=false`） |
| 采集/下载文献或教材全文 | ❌ 禁止 | 单独授权（`full_text_download_in_M4B=false`） |
| 读取真实 A 股结果 | ❌ 禁止 | 单独授权 |
| 访问 provider / 数据库内容 | ❌ 禁止 | 单独授权 |
| 访问 holdout | ❌ 禁止 | 单独授权（始终不授权执行） |
| 由 registry 触发 M4-A 执行 | ❌ 禁止 | M4-A 合同 + 单独授权 |
| `ESTABLISHED` 判定 | ❌ 本设计只冻结登记门 | 另行授权的证据策略 + 人工评审 |
| 推送 / PR / 合并 | ❌ 禁止 | 单独授权 |
| 进入下一阶段 | ❌ 禁止 | 用户明确授权 |

### 13.3 `NOT_TESTED` 可无限期保持

- 记录可以永久停留在 `NOT_TESTED`；不存在超时、过期、自动推进或自动搁置机制；
- 不存在“长期未测试则自动降级/自动清理”的路径；
- 时间不进入身份，也不进入状态判定（第 5.3 节）：任何“已登记 N 天”之类的字段都不存在；
- 因此 `NOT_TESTED` 是**稳定可审计**的休息态，而不是等待被自动消费的队列。

## 14. 实现前置条件与验收边界

实现阶段（另行授权）必须至少满足：

1. 本设计与配套验收场景已通过独立评审，且无未决的实现关键歧义；
2. 新增 Goal 明确 whitelist（`src/ashare_research/mechanism/registry/**`、相应测试、
   状态同步文案），并显式保留 `src/ashare_research/m4`、`knowledge/`、
   顶层 `mechanism/*.py` 的“不存在/不变”断言；
3. 实现必须逐条对齐第 8.1 节验证顺序与第 8.2 节错误码表；
4. 实现必须提供结构性禁令测试（第 10.2、11.3 节）；
5. 实现阶段的验收场景必须覆盖本文档配套文档的**全部**案例，并补齐实现期才可测量的数值
   （如真实摘要值）；
6. 实现**不得**创建真实候选、不得采集文献、不得读取结果、不得访问 provider/数据库/holdout。

本设计阶段**不做**的事（边界声明）：

- 不运行任何 registry 实现测试（不存在实现）；
- 不声称任何摘要值、转换结果或验证结果已被实测；
- 不声称 M4-B 已实现、已授权或已完成。

## 15. 未决与风险

| # | 风险/未决项 | 处理 |
| --- | --- | --- |
| R1 | 第 6.4 节禁止来源特征词表的具体条目未冻结，只冻结了判定位置、错误码与 fail-closed 语义 | 属实现评审项；实现阶段必须给出显式常量词表与正反例，且不得做成可配置开关 |
| R2 | 文本字段是自由文本，无法机械阻止作者在 `theory`/`source_notes` 中写下带数字的结论性表述（第 9.3 节明确不做通用正则判定以避免误伤） | 结构性拒绝键级结果字段已强制；文本语义审查属人工评审阶段，且在实现阶段必须记录为已知残余风险 |
| R3 | 第 7.5 节的 `ESTABLISHED` 门只检查**登记完备性**，不检查统计有效性 | 这是刻意的：registry 不得判定统计；统计判定属另行授权的证据策略 |
| R4 | 第 7.2 节矩阵必须逐格实现，且实现不得遗漏/新增合法边 | 实现阶段必须机器核对合法边集合恰为冻结的 20 条（第 7.2 节）；`state_history` 与转换入口共用同一矩阵，不存在第二处定义 |
| R5 | 第 11.3 节白名单要求独立声明 `hypothesis_id` 正则字面量，存在与既有规则漂移的风险 | 实现阶段必须机械断言两侧 pattern 相等（第 11.3 节）；本设计不复制既有私有正则 |
| R6 | 记录数上限与 real-demo 上限同值（均为 3）是基于“最小切片”的设计选择；未来若需要更大注册表，必须重新冻结规模语义 | 扩大规模需要新的设计评审与授权 |
| R7 | `MAX_REAL_DEMO_CANDIDATES` 可能被误读为“目标数量”或“已授权数量” | 第 10.1 节 SC8 明确：天花板不是目标，创建任何真实候选仍需单独授权 |
| R8 | 本设计未冻结持久化格式（文件/数据库/Parquet） | 刻意如此：持久化属实现评审项；本设计只冻结内存记录、快照与规范字节，避免在无授权数据层的情况下预设存储 |

## 16. 参考

- [M4-B 注册表验收场景 v1](m4b_hypothesis_registry_acceptance_cases_v1.md)
- [M4 有界执行与证据处置设计 v1](m4_bounded_execution_and_evidence_design_v1.md)
- [M4 合成分析矩阵设计 v1](m4_analysis_matrix_design_v1.md)
- [M4 数据适配器设计 v1](m4_dataset_adapter_design_v1.md)
- Goal 契约 [agent/goals/2026-09-12_m4b_hypothesis_registry_design.md](../agent/goals/2026-09-12_m4b_hypothesis_registry_design.md)
- 冻结前置合同 `reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json`
- 项目北极星 `A股个股研究与市场机制验证平台-项目北极星.md`

本文为设计规范，**不是**实现、不是证据、不是执行授权。`M4-B NOT STARTED`；
真实假设执行 `NOT AUTHORIZED`。
