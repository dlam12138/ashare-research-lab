# M4-B 理论/假设注册表验收场景 v1

状态：DESIGN_ONLY / ACCEPTANCE_CASES_NOT_IMPLEMENTED。本文是
[M4-B 理论/假设注册表设计 v1](m4b_hypothesis_registry_design_v1.md) 的配套验收场景清单，
与设计文档同为**规范性**文件。

本文的上游事实（Stage4P 冻结前置合同字段、来源类型、状态词表、候选类别、规模边界）都是
2026-09-12 在本工作树对**既有冻结产物**只读复核得到的；registry 层的期望值是**设计口径**
（由设计第 3–13 节直接推得），**registry 实现尚不存在**，因此本文不声称任何 registry 实现
测试已通过，也**不包含任何真实候选、真实引用、真实 A 股结果、系数、区间、p 值或处置结果**——
设计阶段禁止计算或引入这些内容。

每个案例都写明四件事：**输入变化**、**预期结果或错误**、**验证阶段**（设计第 8.1 节编号）、
**授权解释**（该案例证明了哪一条授权边界）。

## 0. 验证入口与前置条件

### 0.1 拟议入口（尚未实现）

```text
parse_hypothesis_record(document) -> HypothesisRecordV1
hypothesis_record_to_canonical_dict(record) -> dict
serialize_hypothesis_record(record) -> bytes
validate_hypothesis_record(record) -> None
hypothesis_record_identity_digest(record) -> str
hypothesis_record_digest(record) -> str
transition_hypothesis_record(record, request) -> HypothesisRecordV1
validate_state_transition(record, request) -> None
build_hypothesis_registry_snapshot(records) -> HypothesisRegistrySnapshotV1
registry_snapshot_to_canonical_dict(snapshot) -> dict
serialize_hypothesis_registry_snapshot(snapshot) -> bytes
validate_hypothesis_registry_snapshot(snapshot) -> None
count_real_demo_candidates(snapshot) -> int
```

以上 13 个签名是设计第 11.2 节冻结的公开面。硬性要求：

- 公开面恰为上述 **13** 个入口；实现阶段必须机器核对完整名称集合（既不多也不少）；
- 不存在 `execute`、`run`、`scan`、`rank`、`sort`、`promote`、`advance`、`select`、
  `optimize`、`search`、`auto_*` 入口；任何此类请求是 `UNSUPPORTED_REGISTRY_OPERATION`
  或签名层 `TypeError`；
- 不存在 `**kwargs`：未声明的关键字参数（`returns=`、`outcome=`、`sort_key=`、`real_data=`、
  `holdout=`）必须是 `TypeError`；
- 所有入口 IO-free：不读写文件、不访问路径/环境/时钟/网络/provider/数据库/holdout；
- 上游异常（如 `HypothesisConfigError`）按设计第 8.3 节 T7 原样传播，
  `RegistryError` 只承载 registry 自身失败。

### 0.2 复现口径

- 解释器：`D:/量化分析-m4a2i/.venv/Scripts/python.exe`（与本工作树既有验证命令一致）。
- 正例 fixture 必须是**合成/示意**记录：`hypothesis_id` 以 `SYNTH_EXAMPLE_` 前缀、
  文本使用 `SYNTHETIC_EXAMPLE_*` 字面量，**不含**任何真实论文标题、作者、期刊、机构或行情数据。
- 探针只读、不写文件、不开数据库、不调用 provider，也**不调用**
  `regression.py` / `bootstrap.py` / `robustness.py` / `evidence.py` / `crash.py`。
- 本文档中的摘要位置一律写成 `<64 hex>` 占位符：设计阶段不得写死任何摘要值，
  否则文档会变成伪证据。实现阶段由真实实现产出真实值后另行评审。

### 0.3 基线上游身份（2026-09-12 只读复核，实测）

```text
reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
  schema_version            = "M4_STAGE4P_M4B_HYPOTHESIS_REGISTRY_CONTRACT_V1"
  status                    = "FROZEN_PREFLIGHT_ONLY"
  implementation_status     = "NOT_STARTED"
  real_registry_dataset_authorized = false
  not_implementation        = true
  len(minimum_fields)       = 19
  len(allowed_source_types) = 6
  len(state_machine.states) = 12
  len(initial_candidate_classes) = 3   # 全部 status = NOT_TESTED, real_A_share_outcome_read = false
  scale_boundary.MAX_REAL_DEMO_CANDIDATES = 3
  scale_boundary.AUTOMATED_ANOMALY_SCAN   = "PROHIBITED"
  scale_boundary.BACKTEST_RANKING         = "PROHIBITED"
  literature_provenance.literature_is_hypothesis_source_not_local_evidence = true
  literature_provenance.full_text_download_in_M4B = false

仓库状态（本工作树实测）
  branch = codex/m4b-hypothesis-registry-design
  HEAD   = 0de39577f164c095c4bf4f9c3b742fbbee50745d   （Goal 契约提交）
  origin/main = 1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd
  src/ashare_research/m4 存在？否        knowledge/ 存在？否
  既有 mechanism 子包：datasets/  execution/  planning/     （registry/ 尚不存在）
```

设计文档第 4.2 节在 19 个最小字段之上新增 5 个字段（来源身份必需的 `source_version`、`source_notes`，
以及记录级 `schema_version`、`hypothesis_version`、`state_history`），再加 2 个派生摘要字段
（`identity_digest`、`record_digest`），共 **26** 个键；**不得**再新增其它字段。

## 1. 案例索引

| ID | 案例 | 类型 | 验证阶段 | 授权解释 |
| --- | --- | --- | --- | --- |
| AC-01 | 正例：完整合成记录的规范形态与往返 | 正常 | V1–V11 | 设计可用 ≠ 实现已授权 |
| AC-02 | 未知来源类型 | 负例/枚举 | V5 | 来源类型封闭，不降级 |
| AC-03 | 缺失来源身份（`required_identity` 五要素） | 负例/来源 | V2 / V7 | 无身份的候选不得登记 |
| AC-04 | 禁止的规范来源（盗版教材/随机博客/LLM 记忆） | 负例/来源 | V7 | 不可追溯来源 fail-closed |
| AC-05 | 未知/额外键（顶层与嵌套） | 负例/结构 | V2 | 未知键不被静默忽略 |
| AC-06 | 严格 bool/int 与数值处理 | 负例/类型 | V3 / S7 | 无强制转换、无浮点数字 |
| AC-07 | 非法状态转换（矩阵外、reason 不相容、from 不匹配） | 负例/状态机 | V10 | 状态只能按矩阵前进 |
| AC-08 | `ESTABLISHED` 缺少完整证据 | 负例/证据门 | V10 | 无三项证据不得判定成立 |
| AC-09 | 结果/统计键拒绝 | 负例/分离 | V8 | registry 不承载研究结果 |
| AC-10 | 规模违规（real-demo 与记录总数） | 负例/规模 | V12 | 上限是天花板，不是目标 |
| AC-11 | 重复 hypothesis ID | 负例/唯一性 | V12 | 无歧义重复 ID |
| AC-12 | 规范序列化与摘要对键序/工作目录稳定 | 等价性 | V11 / S4 | 身份只由内容决定 |
| AC-13 | 字节可复现（同进程、独立进程、往返） | 等价性 | S1–S10 / V11 | 记录可独立复核 |
| AC-14 | 嵌套变更改变身份层 | 负例/身份 | V11 / V12 | 身份绑定全量身份承载内容 |
| AC-15 | registry 元数据与结果产物的机械分离 | 结构/分离 | V8 / 结构 | 元数据不是证据 |
| AC-16 | fail-closed 读取路径与无部分产出 | 负例/读取 | V1–V3 / S1–S7 | 坏输入不产生半条记录 |
| AC-17 | 不可跳过边界与执行授权引用 | 负例/边界 | V10 | 只有冻结 M4-A 合同可进入执行态 |
| AC-18 | 终态无出边与 `DEFERRED` 唯一恢复边 | 负例/终态 | V10 | 判定不可翻案、搁置不丢历史 |
| AC-19 | 来源改写拒绝与版本提升为新记录 | 负例/可追溯 | V12 | 来源与版本不可被改写 |
| AC-20 | 幂等再验证与无副作用 | 结构/幂等 | V1–V11 | 验证可重复且不改状态 |
| AC-21 | 文献不是本地 A 股证据与授权语义 | 结构/授权 | 结构 + L1–L5 | 文献来源不构成项目证据 |
| AC-22 | 结构性禁令（公开面、导入边界、无 IO、无扫描/排序/提升） | 结构/禁令 | 结构 | 禁令是结构性的，不是约定 |

编号说明：本清单编号是稳定标识，**不得**留下“索引里有条目、正文里没有对应小节”的孤儿编号，
也不得在正文出现索引外的编号。第 7 节给出机器可核对的索引/正文一致性要求。

### 1.1 合同要求覆盖映射（逐条对齐 Goal 的“必须至少覆盖”清单）

| Goal 要求的案例类 | 承载案例 |
| --- | --- |
| valid synthetic record | AC-01（+ AC-13 字节可复现） |
| unknown source type | AC-02 |
| missing provenance | AC-03 |
| forbidden citation source | AC-04 |
| unknown/extra key | AC-05 |
| strict bool/int and numeric handling | AC-06 |
| illegal transition | AC-07（+ AC-17 不可跳过边界） |
| `ESTABLISHED` without complete evidence | AC-08 |
| outcome/statistic key rejection | AC-09（+ AC-15 分离） |
| scale violation | AC-10 |
| duplicate hypothesis ID | AC-11 |
| canonical serialization + digest stability under key order and CWD changes | AC-12 |
| byte reproducibility | AC-13 |
| nested mutation | AC-14 |
| registry/outcome separation | AC-15 |
| fail-closed read paths | AC-16 |
| （附加）可追溯性/授权语义 | AC-18、AC-19、AC-20、AC-21、AC-22 |

## 2. 正常案例

### AC-01 正例：完整合成记录的规范形态与往返

**输入变化**：构造一条完整的合成记录（26 个键齐全，`status = DISCOVERED`，
`state_history` 长度 1，`source_type = TEXTBOOK_THEORY`，四个已知项数组可含 0 或多个
`SYNTHETIC_EXAMPLE_*` 元素）。

**预期结果 / 错误**：验证通过（无异常）；随后断言：

1. `serialize_hypothesis_record(record)` 返回 `bytes`，以 `\n` 结束且恰好一个；
2. 字节以 UTF-8 解码成功且无 BOM；
3. `identity_digest` 与 `record_digest` 均为 64 位小写十六进制，并可被
   `hypothesis_record_identity_digest` / `hypothesis_record_digest` 重算得到**逐字符相等**的值；
4. `parse_hypothesis_record(serialize_hypothesis_record(record))` 的规范字典与
   `hypothesis_record_to_canonical_dict(record)` **相等**；
5. `hypothesis_record_to_canonical_dict` 的返回值修改后不影响原记录；
6. 两个摘要**互不覆盖**：`identity_digest` 不随 `status` 改变，`record_digest` 随 `status` 改变。

**验证阶段**：V1–V11（结构、键集、类型、枚举、日期、来源、禁止键、历史、转换、摘要）。

**授权解释**：证明设计**可实现**且内部自洽；不证明 registry 已实现，不证明任何真实候选存在，
也不构成实现授权（设计第 2.3 节）。

## 3. 来源与字段案例

### AC-02 未知来源类型

**输入变化**：`source_type` 取六类词表外的值（例如 `"BLOG_POST"`、`"LLM_MEMORY"`、
`"PAPER"`、空串、`null`、`123`）。

**预期结果 / 错误**：`UNKNOWN_SOURCE_TYPE`（`null` 与 `123` 先在 V3 得到
`INVALID_FIELD_TYPE`，`""` 先在 V4 得到 `INVALID_FIELD_LENGTH`；字符串形态的非词表值在 V5 得
`UNKNOWN_SOURCE_TYPE`）。

**验证阶段**：V5（类型/长度更早的阶段按第 8.1 节顺序先报）。

**授权解释**：来源类型是封闭词表；不允许把未知来源降级为“其它”或“待定”，
因此“来源不明但先登记”的路径不可表达。

### AC-03 缺失来源身份（`required_identity` 五要素）

**输入变化**：分别构造四组负例——(3a) 缺 `citation_or_source_identity` 键；
(3b) `citation_or_source_identity = ""`；(3c) 缺 `source_version` 键；
(3d) `source_notes` 键缺失（区别于允许的 `""`）。

**预期结果 / 错误**：(3a)、(3c)、(3d) → `MISSING_REQUIRED_FIELD`（V2）；
(3b) → `MISSING_PROVENANCE_FIELD`（V7）。
另加正例：`source_notes = ""` 与 `citation_or_source_identity = "UNKNOWN"` 必须**通过**，
以证明“显式未知”与“缺失”被区分。

**验证阶段**：V2（键集）与 V7（来源完备性）。

**授权解释**：无来源身份的候选不得登记；`"UNKNOWN"` 是显式的可审计未知，
而缺键/空串是拒绝路径。

### AC-04 禁止的规范来源

**输入变化**：(4a) `source_type = TEXTBOOK_THEORY` 且来源身份命中盗版/影印/扫描/网盘特征词；
(4b) 来源身份为个人博客/论坛/自媒体/内容农场，且无可追溯作者与版次；
(4c) `citation_or_source_identity` 或 `source_version` 为 `"LLM"`/`"MODEL"`/`"MEMORY"`
之类的模型记忆标记；(4d) `source_type ∈ {ACADEMIC_PAPER, TEXTBOOK_THEORY, KNOWN_ANOMALY,
REPLICATION_EXTENSION}` 且 `source_version = "UNKNOWN"`。

**预期结果 / 错误**：全部 → `FORBIDDEN_CANONICAL_SOURCE`（V7）。
反向断言：可追溯的合成来源（`SYNTHETIC_EXAMPLE_*` 且版次明确）**不**被拒绝。

**验证阶段**：V7，且必须先于 V8/V9/V10/V11（来源错误不得被后续阶段的错误掩盖）。

**授权解释**：合同冻结的三类禁止来源被机械拒绝；拒绝是 fail-closed，
不存在“降级为 UNKNOWN 来源”或“标记待人工复核后继续”的路径。

### AC-05 未知/额外键（顶层与嵌套）

**输入变化**：(5a) 顶层加入额外键（`"notes_extra"`、`"evidence_level"`、`"params"`）；
(5b) `state_history[*]` 加入额外嵌套键（`"note"`、`"source"`）；(5c) 顶层复制一个键
（同时给出新旧两种拼写）。

**预期结果 / 错误**：全部 → `UNKNOWN_RECORD_FIELD`（V2）；
且必须先于 V3 报出（额外键不得被静默忽略后再报类型错误）。

**验证阶段**：V2。

**授权解释**：未知键策略是 fail-closed 且先于取值；不存在向前兼容的“忽略未知字段”模式，
因此“夹带额外结果字段”不能靠拼写差异绕过第 9 节。

## 4. 类型与数值案例

### AC-06 严格 bool/int 与数值处理

**输入变化**：(6a) `hypothesis_version = True`；(6b) `hypothesis_version = "1"`；
(6c) `hypothesis_version = 1.0`；(6d) `state_history[0].ordinal = False`；
(6e) 序列化字节中把 `hypothesis_version` 写成 `1.0`（浮点 JSON token）；
(6f) `hypothesis_version = 0` 与 `1001`（越界）；(6g) `hypothesis_version = 1`（正例）。

**预期结果 / 错误**：(6a)–(6d) → `INVALID_FIELD_TYPE`（V3：`bool` 不是 `int`，
`str`/`float` 不是 `int`，不做强制转换）；(6e) → `NON_CANONICAL_SERIALIZATION`（S7）；
(6f) → `INVALID_FIELD_LENGTH`（V4，范围越界）；(6g) 通过。

**验证阶段**：V3 / V4 / S7。

**授权解释**：无强制转换（设计第 8.3 节 T1）意味着“`True` 当作 1”“`"1"` 当作 1”
这类静默兼容不存在；registry 记录不含任何浮点数值，因此也没有浮点身份层。

## 5. 状态机案例

### AC-07 非法状态转换

**输入变化**：(7a) 矩阵外转换 `DISCOVERED → A_SHARE_FEASIBILITY_REVIEWED`（跳过 S2）；
(7b) `DISCOVERED → NOT_TESTED`（跳过 S2/S3）；(7c) `NOT_TESTED → DEVELOPMENT_EXECUTED`
（跳过预注册）；(7d) `PRE_REGISTERED → DEVELOPMENT_EXECUTED` 且 `reason_code =
"OOS_COMPLETED"`（reason 与转换不相容）；(7e) 请求 `from_state` 与记录当前 `status` 不一致；
(7f) `DEVELOPMENT_EXECUTED → OOS_EXECUTED`（跳过注册稳健性）。

**预期结果 / 错误**：全部 → `ILLEGAL_STATE_TRANSITION`（V10）；
(7a)、(7b)、(7c)、(7f) 属矩阵外或不可跳过边界 `B1/B2/B3`；(7d) 属第 7.3.1 节相容表违规；
(7e) 属乐观并发前置条件失败。

**验证阶段**：V10（且必须先于 V11：非法转换不得被报成摘要不匹配）。

**授权解释**：状态只能沿冻结矩阵前进；跳过边界、理由不相容与并发错位都不可表达，
因此“快速推进候选”没有路径。

### AC-08 `ESTABLISHED` 缺少完整证据

**输入变化**：六组负例分别破坏设计第 7.5 节的门：
(8a) 缺 `DEVELOPMENT_EXECUTED` 历史项；(8b) 缺 `ROBUSTNESS_EXECUTED` 历史项；
(8c) 缺 `OOS_EXECUTED` 历史项；(8d) 三项齐备但当前 `status != OOS_EXECUTED`；
(8e) 三项齐备但 `authorization_ref` 三项**相同**（未独立授权）；(8f) 历史中存在先前的
`EVIDENCE_NOT_SUPPORTED` 判定项后再请求 `ESTABLISHED`。
另加正例 (8g)：三项齐备、三项授权身份互不相同、`status = OOS_EXECUTED`、
`reason_code = EVIDENCE_SUPPORTED`，必须**通过**门检查。

**预期结果 / 错误**：(8a)–(8f) → `ESTABLISHED_EVIDENCE_INCOMPLETE`（V10）；(8g) 通过。

**验证阶段**：V10。

**授权解释**：`ESTABLISHED` 在缺少适用的冻结开发、注册稳健性与独立 OOS 证据时不可达；
且该门是**登记完备性**门，不是统计判定门——“登记齐备”不等于“已被证明”，
也不等于可交易（设计第 7.5 节）。

### AC-17 不可跳过边界与执行授权引用

**输入变化**：(17a) `DISCOVERED → DEVELOPMENT_EXECUTED`；(17b) 合法的
`PRE_REGISTERED → DEVELOPMENT_EXECUTED` 但 `authorization_ref = null`；
(17c) 同上但 `authorization_ref = ""`；(17d) `DEVELOPMENT_EXECUTED → ROBUSTNESS_EXECUTED`
但 `authorization_ref = null`；(17e) 执行期转换携带 `evidence_kind = null`；
(17f) 非执行期转换（如 `DISCOVERED → LITERATURE_REVIEWED`）却携带非空
`authorization_ref`/`evidence_kind`；(17g) 合法执行期转换（授权身份非空、`evidence_kind` 正确）
必须通过。

**预期结果 / 错误**：(17a) → `ILLEGAL_STATE_TRANSITION`；(17b)、(17c)、(17d) →
`MISSING_AUTHORIZATION_REF`（**先于** `ILLEGAL_STATE_TRANSITION` 报出）；
(17e) → `ILLEGAL_STATE_TRANSITION`（执行期转换缺少该转换对应的 `evidence_kind`，
前置条件 P6–P8 未满足；设计第 7.7 节已冻结该单一选择，不是二选一）；
(17f) → `INVALID_FIELD_TYPE`（非执行期必须为 `null`）；(17g) 通过。

**验证阶段**：V10。

**授权解释**：合同 `execution_boundary`（“只有单独冻结的 M4-A 研究合同可以把候选推入执行状态”）
由 `authorization_ref` 强制；执行态不能靠“跳过前置”或“空授权”抵达。

### AC-18 终态无出边与 `DEFERRED` 唯一恢复边

**输入变化**：(18a) `NOT_ESTABLISHED → ESTABLISHED`；(18b) `NOT_ESTABLISHED → INCONCLUSIVE`；
(18c) `ESTABLISHED → NOT_ESTABLISHED`；(18d) `INCONCLUSIVE → ESTABLISHED`；
(18e) `DEFERRED → A_SHARE_FEASIBILITY_REVIEWED`（恢复到被搁置时的状态）；
(18f) `DEFERRED → NOT_TESTED` 且 `reason_code = DEFERRED_BY_REVIEW`（合法）；
(18g) `DEVELOPMENT_EXECUTED → DEFERRED`（执行期搁置）；(18h) `NOT_TESTED → DEFERRED`（合法）。

**预期结果 / 错误**：(18a)–(18d) → `TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION`；
(18e) → `ILLEGAL_STATE_TRANSITION`；(18g) → `ILLEGAL_STATE_TRANSITION`（执行期与终态不可搁置）；
(18f)、(18h) 通过。撤销/翻案/回归路径全部不可表达：不存在 `S9/S11 → S10`、
不存在执行期回退到执行前状态。

**验证阶段**：V10。

**授权解释**：判定不可翻案；搁置只能回到 `NOT_TESTED` 且被搁置时的状态保留在
`state_history` 中（历史不丢失），因此“先搁置、再从旧状态继续推进”不可表达。

## 6. 分离、规模与身份案例

### AC-09 结果/统计键拒绝

**输入变化**：在记录中分别注入结果或统计键：`p_value`、`coefficient`、`confidence_interval`、
`disposition`、`effect_size`、`evidence_level`、`abnormal_return`、`sharpe`、`best`、
`ranking`，以及既有冻结集合 `RESTRICTED_RESEARCH_OUTPUT_KEYS` 的全部 12 个成员
（`abnormal_return`、`alpha`、`beta`、`bootstrap_result`、`confidence_interval`、
`correlation`、`crash_day_count`、`effect_size`、`evidence_level`、`gamma`、`p_value`、
`positive_probability`），并分别注入到顶层与嵌套位置。

**预期结果 / 错误**：结果/统计键 → `FORBIDDEN_OUTCOME_FIELD`（V8）；
环境/选择键（`hostname`、`cwd`、`path`、`session`、`best`、`winner`、`aggregate`、
`optimize`、`search` 等，即既有 `FORBIDDEN_KEYS` 全部成员）→
`FORBIDDEN_ENVIRONMENT_FIELD`（V8）。断言：第 9.1 节集合**包含**既有
`RESTRICTED_RESEARCH_OUTPUT_KEYS` 与 `FORBIDDEN_KEYS` 的全部成员（集合包含关系可机器核对）。

**验证阶段**：V8（且在 V7 之后：来源错误优先）。

**授权解释**：registry 元数据与研究结果产物被机械分离；系数、区间、p 值、处置与
“最佳/排序/选中”语义在 schema 中**不可表达**，因此 registry 不能被读成研究结论库。

### AC-15 registry 元数据与结果产物的机械分离

**输入变化**：结构性检查（不注入数据）：核对记录键集合恰为设计第 4.1 节的 26 个键；
核对没有 `evidence`/`result`/`outcome` 语义的字段；核对快照载荷不含任何浮点统计块；
核对 `authorization_ref` 只登记**合同身份**而非结果。

**预期结果 / 错误**：全部断言成立，无异常；并断言记录规范字典中**不含**任何
`float` 类型的值（registry 没有 float64 身份层），且 `canonical_digest` 的输入是纯 JSON 值
（不含 dataclass / `FrozenJSON*`）。

**验证阶段**：V8 加结构性断言。

**授权解释**：registry 只承载来源与候选元数据；它与 M4-A 执行产物不共享身份、
不互相写入、不派生结果（设计第 9.4 节 D1–D5）。

### AC-10 规模违规

**输入变化**：(10a) 构造 4 条 `a_share_data_feasibility ∈ {FEASIBLE_FREE, FEASIBLE_PAID}`
的记录；(10b) 构造 4 条记录而其中仅 2 条为 real-demo；(10c) 3 条 real-demo 记录（正例）；
(10d) 把 (10a) 的其中一条 `status` 改为 `NOT_ESTABLISHED` / `DEFERRED` 后重新校验。

**预期结果 / 错误**：(10a) → `SCALE_LIMIT_EXCEEDED`（V12，real-demo 计数 4 > 3）；
(10b) → `SCALE_LIMIT_EXCEEDED`（V12，记录总数 4 > `MAX_RECORDS_PER_SNAPSHOT`）；
(10c) 通过（计数 3 ≤ 3）；(10d) **仍然** `SCALE_LIMIT_EXCEEDED`——
规模门与 `status` 无关（设计第 10.1 节 SC5），状态操作不能减少计数。
另断言：`count_real_demo_candidates` 与实际计数一致，且规模门与来源类型、结果、排序无关。

**验证阶段**：V12。

**授权解释**：`MAX_REAL_DEMO_CANDIDATES=3` 是天花板而不是目标；即使计数 ≤ 3，
创建任何真实候选仍需单独授权（`real_registry_dataset_authorized=false`）。

### AC-11 重复 hypothesis ID

**输入变化**：(11a) 快照内出现两条 `(hypothesis_id, hypothesis_version)` 完全相同的记录
（内容相同）；(11b) 同上但两条内容不同；(11c) 同一 `hypothesis_id` 的两个不同
`hypothesis_version`（1 与 2）；(11d) 不同 `hypothesis_id`、相同 `hypothesis_version`。

**预期结果 / 错误**：(11a) → `DUPLICATE_HYPOTHESIS_ID`（V12；两条 `identity_digest` 相同）；
(11b) → `PROVENANCE_REWRITE`（V12；两条各自摘要自洽、身份键相同而身份承载内容不同，
即 `identity_digest` 不同；该码由设计第 4.4/8.2 节冻结，不是二选一）；(11c) 通过
（两个版本同时可见，均不被覆盖）；(11d) 通过。若 (11b) 中第二条记录未重算摘要，
则按 `V11 < V12` 先在 V11 得到 `IDENTITY_DIGEST_MISMATCH`（确定性首错，见 AC-19）。

**验证阶段**：V12。

**授权解释**：无歧义重复 ID——不存在“后写覆盖”或“先写保留”；同一假设的多次尝试
以版本并存的方式留下完整痕迹。

### AC-19 来源改写拒绝与版本提升为新记录

**输入变化**：(19a) 保持 `(hypothesis_id, hypothesis_version)` 不变，改动 `source_title`；
(19b) 同前，改动 `citation_or_source_identity`；(19c) 同前，改动 `source_notes`（追加备注）；
(19d) 同前，改动 `theory`；(19e) 提升 `hypothesis_version` 为 2 并给出新的
`identity_digest`，与版本 1 并存。

**预期结果 / 错误**：(19a)–(19d) → `PROVENANCE_REWRITE`（V12，同一身份键出现不同
`identity_digest`，即改写既有身份）；若未重算摘要则按 `V11 < V12` 先在 V11 得到
`IDENTITY_DIGEST_MISMATCH`（确定性首错：摘要自洽先于快照级身份一致性）；
(19e) 通过：版本 2 是新记录，版本 1 **原样保留**，两者同时可见、均不被改写。

**验证阶段**：V11 / V12。

**授权解释**：来源、版本与理论在记录生命周期内不可改写；需要更正或重做研究时只能提升版本，
因此“静默修正来源”不可表达，可追溯性由结构保证。

### AC-14 嵌套变更改变身份层

**输入变化**：(14a) 改动 `known_controls` 一个元素；
(14b) 改动 `known_alternative_explanations` 一个元素；
(14c) **交换** `known_replications` 两个元素的顺序（集合内容相同、顺序不同）；
(14d) 改动 `known_failures_or_decay` 一个元素；
(14e) 改动嵌套的 `state_history[0].reason_code`；
(14f) 只改动 `status`（不触碰身份承载字段）。

**预期结果 / 错误**：(14a)–(14d) → `identity_digest` 必然改变，未重算时
`IDENTITY_DIGEST_MISMATCH`（V11），重算后 `PROVENANCE_REWRITE`（V12）；
(14e) → `record_digest` 改变（`state_history` 属可变字段），未重算时
`RECORD_DIGEST_MISMATCH`（V11），且 `state_history` 内部一致性可能在 V9 先失败；
(14f) 正例：`identity_digest` **不变**、`record_digest` **改变**，且该变化只能经
`transition_hypothesis_record` 合法转换产生。

**验证阶段**：V9 / V11 / V12。

**授权解释**：身份绑定全量身份承载内容（含数组元素**与顺序**，因为顺序是输入语义且不得被排序）；
“改一个控制项而不改身份”不可表达。

## 7. 序列化、可复现与读取案例

### AC-12 规范序列化与摘要对键序/工作目录稳定

**输入变化**：(12a) 用不同的字典插入顺序构造同一记录的规范字典；
(12b) 在不同工作目录下（例如进程 CWD 切换到临时目录）执行序列化与摘要；
(12c) 以不同的记录插入顺序构造同一快照的 `records` 输入序列。

**预期结果 / 错误**：三种变化下 `serialize_hypothesis_record` 的字节**逐字节相同**，
两个摘要**逐字符相同**；快照的 `records` 规范顺序恒为
`(hypothesis_id, hypothesis_version)` 升序，与插入顺序无关；
且两个摘要均不含 `cwd`/主机/时间等环境输入（加入这些环境变化不改变任何字节）。

**验证阶段**：S4（`sort_keys=True`）与 V11（摘要自洽）。

**授权解释**：身份只由内容决定；记录的身份可在不同机器与工作目录下独立复核。

### AC-13 字节可复现

**输入变化**：(13a) 同一进程内连续两次序列化同一记录；
(13b) 在独立解释器进程中重新构造并序列化同一记录；
(13c) `parse_hypothesis_record(serialize_hypothesis_record(record))` 往返后再序列化。

**预期结果 / 错误**：三次得到的字节**逐字节相同**（包括结尾恰好一个 `LF`）；
两次摘要相同；往返后的规范字典与原始规范字典相等。

**验证阶段**：S1–S10 与 V11。

**授权解释**：记录可被独立复核与重放；但字节可复现**不等于**该记录已被执行、
被验证或被判定（`NOT_TESTED` 的语义不受影响）。

### AC-16 fail-closed 读取路径与无部分产出

**输入变化**：(16a) 传入非映射文档（列表、字符串、`None`、整数）；
(16b) 序列化字节以 UTF-8 BOM 开头；(16c) 字节含 `CR`；
(16d) 字节结尾无 `LF` 或有 2 个 `LF`；(16e) 字节含浮点 JSON token；
(16f) 在合法可空位置之外出现 `null`；(16g) 合法记录（正例）。

**预期结果 / 错误**：(16a) → `INVALID_RECORD_STRUCTURE`（V1）；
(16b)–(16e) → `NON_CANONICAL_SERIALIZATION`；(16f) → `INVALID_FIELD_TYPE`（V3）；
(16g) 通过。全部失败路径都**不返回部分记录、不修改输入、不写出任何字节**
（设计第 8.3 节 T4），且重复读取失败输入得到相同错误码（稳定错误码）。

**验证阶段**：反序列化层与 V1–V3（S1–S7）。

**授权解释**：读取路径 fail-closed：坏输入不产生半条记录，也不被“尽量修复”，
因此不存在“先写入、后补全”的登记路径。

### AC-20 幂等再验证与无副作用

**输入变化**：(20a) 对同一已通过验证的记录连续两次调用
`validate_hypothesis_record`；(20b) 对同一快照连续两次调用
`validate_hypothesis_registry_snapshot`；(20c) 在调用前后比较记录的规范字典与两个摘要；
(20d) 在 IO 被拒绝的环境中运行公共入口。

**预期结果 / 错误**：两次调用返回相同结果（无异常），记录与快照不被修改，
摘要不变；公共入口在无文件/网络/环境访问的条件下正常运行（IO-free），
不存在“已验证标记”短路（否则后续篡改会被掩盖）。

**验证阶段**：V1–V11（纯函数语义）。

**授权解释**：验证可重复且不改状态；registry 不因“被验证过”而产生持久副作用或新的授权。

## 8. 授权与语义案例

### AC-21 文献不是本地 A 股证据与授权语义

**输入变化**：结构性断言（不注入数据）：核对设计第 6.3 节 L1–L5 与第 13.2 节授权矩阵在
文档中显式存在并可被逐条引用；核对来源状态不携带证据语义
（`DISCOVERED`/`LITERATURE_REVIEWED` 不得被描述为已验证）。

**预期结果 / 错误**：全部断言成立；并断言：

1. 记录与快照的公开面没有任何“读取证据等级/显著性/结论”的入口；
2. 不存在从来源状态直达 `ESTABLISHED` 的转换（AC-08 的门与 AC-07 的矩阵共同保证）；
3. 实现阶段必须在验收中覆盖“文献来源记录不产生任何项目证据”的语义陈述，
   并**不得**把它实现为可配置的开关。

**验证阶段**：结构断言 + L1–L5 + 第 13.2 节授权矩阵。

**授权解释**：文献/教材/经典 anomaly 只提供假设来源；`literature evidence` 不自动变成
`project evidence`；设计完成不等于实现、执行、证据、真实数据、holdout、推送、PR 或合并授权。

### AC-22 结构性禁令

**输入变化**：结构性检查（不注入数据）：

1. 公开面名称集合恰为第 0.1 节的 13 个入口；
2. 每个入口的 `inspect.signature` 不含 `VAR_KEYWORD`；
3. 不存在名称匹配 `scan|rank|sort|promote|advance|select|optimize|search|auto_` 的公开入口；
4. `registry/**` 的导入图不含 `pandas`/`numpy`/`duckdb`/`pyarrow`/`statsmodels`/`yaml`，
   不含 `mechanism.planning`/`datasets`/`execution`/`regression`/`bootstrap`/`robustness`/
   `evidence`/`crash`/`analysis_contracts`/`contract_compiler`/`contracts`；
5. 公共入口不调用 `open`/`Path.read_text`/`os.environ`/`socket`；
6. 顶层 `src/ashare_research/mechanism/*.py` 文件集合不变，
   `src/ashare_research/m4` 与 `knowledge/` 不存在；
7. `records` 模块声明的 `hypothesis_id` 正则字面量与既有
   `hypothesis_config._IDENTIFIER_RE.pattern` 相等（防两套标识符规则漂移）。

**预期结果 / 错误**：全部断言成立，无异常；任一项不成立即为实现缺陷，
不得通过放宽断言“修复”。

**验证阶段**：结构性断言（跨第 10.2、11.1、11.3 节）。

**授权解释**：自动异常扫描、回测排序、按收益排序与候选自动提升不是靠约定禁止，
而是**结构性不可表达**：没有入口、没有参数、没有字段、没有导入面。

## 9. 本设计阶段实际执行的验证（非实现测试）

本阶段**没有** registry 实现，因此**没有**任何 registry 测试通过。实际执行的是：

1. 只读复核冻结前置合同的全部字段（第 0.3 节实测值）；
2. 只读复核既有可复用接口：`canonical_digest`、`serialize_matrix` 的序列化约定、
   `_IDENTIFIER_RE`、`RESTRICTED_RESEARCH_OUTPUT_KEYS`、`FORBIDDEN_KEYS`、
   `MatrixError`/`AdapterError`/`ExecutionError` 的失败约定；
3. Goal 规定的全部验证命令（pytest 组、ruff、git 检查、hash 检查、`Test-Path` 检查），
   逐条独立执行并记录真实退出码；
4. 变更 Markdown 的 UTF-8/换行/空白/冲突标记/代码围栏审计与仓内相对链接解析。

命令、退出码与真实输出记录在
[设计交付验收](../acceptance/2026-09-12_m4b_hypothesis_registry_design.md) 与
[工作记录](../agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md)。

## 10. 实现阶段的验收顺序要求

实现阶段（另行授权）必须满足：

1. AC-01..AC-22 **全部**被真实实现覆盖，不得 skip、xfail 或弱化；
2. 第 8.1 节验证顺序必须被结构性断言（阶段标记顺序），且首错可复现；
3. 第 7.2 节矩阵的合法边集合必须机器核对为冻结的 **20** 条；
4. 第 9.1/9.2 节的禁止键集合必须机器核对为既有冻结集合的**超集**；
5. 第 11.3 节导入白名单与第 10.2 节禁令必须以结构性断言实现（AC-22）；
6. 真实摘要值只能由真实实现产出后写入验收文档，不得在设计与场景文档中预先写死；
7. 实现不得创建真实候选、不得采集文献、不得读取 A 股结果、不得访问 provider/数据库/holdout；
8. 实现阶段的验收文档必须逐条标注“已实现测试”与“仍为设计口径”的内容，不得混同。

## 11. 边界声明

- 本文与配套设计文档都是**设计规范**，不是实现、不是证据、不是执行授权。
- registry 实现**尚不存在**；本文**不声称**任何 registry 测试已通过。
- 本文不含任何真实候选、真实引用、真实论文/教材内容、真实 A 股结果、系数、区间、p 值或处置。
- `M4-B NOT STARTED`；真实假设执行 `NOT AUTHORIZED`；
  `real_registry_dataset_authorized = false`。
- 推送、PR、合并与进入实现/下一阶段各需单独明确授权。
