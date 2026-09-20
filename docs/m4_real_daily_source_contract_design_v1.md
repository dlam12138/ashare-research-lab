# M4 真实日频来源合同与适配器设计 v1

## 2026-09-20 post-PR21 integration reconciliation

本文件正文是 2026-09-14 的历史设计快照。PR #20 与 PR #21 现已合并；正文第 8 节
所列“PR #20 未合并”已解除，不再是当前 blocker。合并没有提供真实日历、成员、
来源 revision、PIT、目标收益语义或执行授权，因此其余 blocker 与
`DESIGN_ONLY / NOT_AUTHORIZED` 边界不变。后续 K1 仅为缩小版离线证明内核，
不等同于本文件拟议的完整 `M4_REAL_SOURCE_BUNDLE_V1` 适配器。

日期：2026-09-14。状态：**DESIGN_ONLY / NOT_IMPLEMENTED / NOT_AUTHORIZED**。执行者：DSH；独立验收：Codex。

本文件是[本轮 Goal](../agent/goals/2026-09-14_m4_real_daily_source_contract_design.md)的设计交付之一，上游决策见[设计准入评审 v1](m4_real_daily_adapter_design_gate_v1.md)。本文只冻结拟议接口与验证语义：**不实现**适配器、**不获取或读取**任何真实数据、**不授权**真实研究执行。基于本文件的任何实现都必须另立 Goal 并取得用户单独授权。

## 1. 拟议接口（独立、版本化的真实来源合同）

| 项目 | 拟议值 | 说明 |
| --- | --- | --- |
| 模块 | `ashare_research.mechanism.datasets.real_daily` | 新增模块，当前不存在 |
| 输入 schema | `M4_REAL_SOURCE_BUNDLE_V1` | 真实来源与角色观测输入信封 |
| 输出 schema | `M4_REAL_DATASET_PREPARATION_V1` | 仅在校验全通过时产出 |
| 拒绝 schema | `M4_REAL_SOURCE_REJECTION_V1` | 任何拒绝的可审计结果 |
| 适配器版本 | `M4_REAL_DAILY_ROLE_ADAPTER_V1` | 与合成适配器版本名不重叠 |
| 摘要算法 | `M4_CANONICAL_REAL_SOURCE_DIGEST_V1` | 复用规范化原则，不复用合成 `evidence_digest` 身份 |
| 异常 | `RealSourceError(code, stage, locator)` | `code` 为第 4 节稳定错误码 |

拟议公共函数（签名，均未实现）：

- `validate_real_source_bundle(bundle: RealSourceBundleV1, contract: RealStudyContractV1, plan: RealAnalysisPlanV1, lock: FrozenStudyLockV1, artifacts: RawArtifactReaderV1) -> RealValidationReportV1`
- `prepare_real_daily_dataset(bundle, contract, plan, lock, artifacts) -> RealDatasetPreparationV1`
- `reject_real_source_bundle(bundle, contract, plan, lock, error) -> RealSourceRejectionV1`
- `real_dataset_to_canonical_dict(preparation) -> dict`、`serialize_real_dataset(preparation) -> bytes`、`validate_real_dataset(preparation, bundle, contract, plan, lock, artifacts) -> None`

以上类型与函数均为拟议、尚不存在。`RealStudyContractV1` 至少冻结 `study_id`、角色及顺序、开发/holdout 窗口、允许的来源版本与修订选择规则、signal cutoff、收益转换/horizon、单位、质量门槛；`RealAnalysisPlanV1` 至少绑定合同摘要、角色与 horizon；它们独立于现有合成 V1 配置/计划。`FrozenStudyLockV1` 必须是 bundle 之外独立封存的只读记录，载有封存时间、合同/计划/代码摘要和来源版本承诺，并有独立可验证的内容身份；缺锁或锁晚于目标字节访问即拒绝，不能接受合同自报锁。`RawArtifactReaderV1.read(relative_locator) -> bytes` 是注入的离线只读原始字节读取器，必须将 locator 限制在已登记的原始文件集合；没有实际字节就拒绝，不能仅相信自报 SHA。`validate_real_dataset` 必须重新绑定全部输入证据，不能只检查输出对象形状。

公共不变量：准备与拒绝输出均显式记录 `execution_authorized=false`、`statistics_computed=false`、`research_outcome_consumed=false`、`holdout_accessed=false`、`matrix=None`；另以 `outcome_bytes_examined` 如实记录验证器是否曾检查目标来源字节。仅拒绝输出有 `accepted_roles=()`，成功准备输出用 `quality_report` 记录覆盖。目标来源字节只能在独立封存的 outcome 前锁通过后检查；本轮纯设计没有读取任何真实 outcome。两类输出都没有矩阵行、统计量或正向执行授权，也不得被 `run_synthetic_pipeline` 消费。

需要新配置词汇：`RealIdentityPolicy(SECURITY_LEVEL_IDENTITY_V1)`、`RealMembershipPolicy(T_MINUS_1_KNOWN_AT_SIGNAL)`、`RealFactorKind`、`RealCalendarSource`、`RealReturnKind`。它们是**新类型**，需要 `M4_HYPOTHESIS_CONFIG_V2`（或等价的独立真实配置）与新编译器/计划版本；禁止向冻结 V1 的 `IdentityPolicy`、`MembershipPolicy`、`FactorKind` 追加成员，禁止只改 `mode` 复用 V1 入口。

## 2. 与合成 V1 的隔离

- 冻结不改：`hypothesis_config.CONFIG_SCHEMA_VERSION = "M4_HYPOTHESIS_CONFIG_V1"`、`datasets/synthetic.py` 的 `SCHEMA = "M4_BOUND_SYNTHETIC_DATASET_V1"`、`OUTPUT_SCHEMA = "M4_DATASET_PREPARATION_V1"`、`ADAPTER_VERSION = "M4_SYNTHETIC_ROLE_ADAPTER_V1"`，以及 `run_synthetic_pipeline`、矩阵构建器与有界执行器。
- 依赖方向：`real_daily` 可只读导入 `model_digest`、冻结合同/计划类型；`synthetic` 不得导入 `real_daily`；`real_daily` 不得构造 V1 dataclass，也不得返回 `DatasetPreparationV1`。
- 入口闸门：合成数据准备、矩阵、执行器与 `run_synthetic_pipeline` 遇到 `M4_REAL_*` schema 必须拒绝，不得因字段同名而接受；未来隔离测试应断言拒绝且无执行副作用，具体错误码取现有冻结入口实际定义，不能要求其抛出本拟议模块的新错误码。
- 身份隔离：真实证据不得使用 `SYNTHETIC_CALENDAR_V1`、`SYNTHETIC_FIXED_MEMBERSHIP_V1`，不得把合成 `evidence_digest` 当真实谱系证明；`execution_authorized` 不得被真实对象改成 true 后进入任一执行路径。
- 测试隔离：本设计的用例（见[验收用例 v1](m4_real_daily_source_acceptance_cases_v1.md)）未来实现时放在新的测试文件；不得放宽、改写或跳过既有合成测试。

## 3. 逐字段合同（`M4_REAL_SOURCE_BUNDLE_V1`）

### 3.1 信封与代码身份

| 字段 | 类型 | 必需 | 规则 |
| --- | --- | --- | --- |
| `bundle_id` | identifier | 是 | 不含宿主路径 |
| `schema_version` | 常量 | 是 | 必须等于 `M4_REAL_SOURCE_BUNDLE_V1` |
| `adapter_version` | 常量 | 是 | 必须等于 `M4_REAL_DAILY_ROLE_ADAPTER_V1` |
| `study_id` | identifier | 是 | 与冻结合同一致 |
| `contract_digest` | sha256 | 是 | 必须在读取 outcome 前生成 |
| `plan_digest` | sha256 | 是 | 确定性分析计划摘要 |
| `code_identity` | object | 是 | `git_commit`、`source_tree_digest`、`adapter_version` |
| `window` | object | 是 | `development_start`、`development_end`、`holdout_start`、`holdout_policy_id` |
| `roles` | tuple | 是 | 有序，与冻结合同角色顺序一致 |
| `source_runs` | list | 是 | 见 3.2，每角色至少一条 |
| `auxiliary_artifacts` | list | 是 | 日历、停牌、成员等非角色证据的 `raw_locator`、`raw_sha256`、长度、来源版本及发布时间；同样由读取器复算 |
| `calendar_evidence` | object | 是 | 见 3.3 |
| `membership_evidence` | object | 是 | 见 3.4 |
| `observations` | list | 是 | 见 3.5 |
| `domain` | object | 是 | 见 3.7 |
| `input_digest` | sha256 | 是 | 由内容复算，见第 5 节 |

禁止字段：宿主绝对路径、以“当前时间”生成的默认值、自报摘要。`created_at` 若出现只能来自输入，且不参与身份判定。

### 3.2 `SourceRunV1`：来源、版本、原始身份、传输边界

`run_id`、`role`、`provider_id`、`publisher`、`endpoint_id`、`method`、`dataset_id`、`request_params`（规范化）、`requested_start`、`requested_end`、`bounded_transport_proof`（`requested_window_only`、`response_dates_min`、`response_dates_max`、`proof_digest`）、`raw_locator`（登记根目录内的规范相对路径）、`raw_sha256`、`raw_bytes_length`、`retrieved_at`、`published_at`、`revision_id`、`vintage_id`、`supersedes_raw_sha256`、`license_id`、`normalization_rule_id`、`normalization_rule_version`。

规则：`raw_sha256` 必须与实际字节一致；适配器内按 `normalization_rule_id/version` 登记的确定性解析器须从这些字节重建规范化观测，并逐字段比对 bundle 的观测，不能只重新散列自报观测；解析器版本须受 `code_identity` 与外部锁约束。`bounded_transport_proof` 的日期边界也须与原始响应中解析出的日期比对，不信任自报证明。`revision_id`/`vintage_id` 必填，历史修订必须产生新身份并预先声明选择规则；`published_at` 必填；`retrieved_at` 是抓取记录，**不得**当作发布时间或可得性证明；缺少来源、版本或原始内容证明即拒绝，不自动换源；请求窗口外的响应内容即拒绝。

### 3.3 `CalendarEvidenceRealV1`：交易日历与时区

`calendar_id`、`calendar_version`、`exchange_scope`、`timezone`（示例合同取 `Asia/Shanghai`）、`session_close_local`、`signal_cutoff_local`、`trading_dates`、`trading_dates_digest`、`suspension_table_digest`、`half_day_table_digest`、`holiday_source_raw_sha256`。所引用的原始日历/停牌/半日文件必须登记在 `auxiliary_artifacts`，各规范表由版本化解析规则重建。

规则：`expected_dates` 只能来自经验证的日历；缺日历、日历冲突或日历证据摘要不符即拒绝；**不得**从已有行情行反推日历；日期、时间戳、时区三者分离；海外控制序列必须显式声明其自身日历与时区，禁止用海外同日日期静默连接。

### 3.4 证券身份与 t−1 成员

`SecurityRefV1`：`security_id`（证券级，含交易所限定）、`company_id`（仅参考，不得作主键）、`exchange`、`board`、`security_type`、`listed_from`、`listed_to`、`special_status`、`identity_rule_version`、`identity_evidence_sha256`。

`MembershipEvidenceRealV1`：`universe_id`、`membership_rule_version`、`as_of_rule = "T_MINUS_1_KNOWN_AT_SIGNAL"`、`membership_available_at_rule`、`per_date_membership_digest`、`per_date_membership_available_at`、`target_exclusion = true`、`membership_source_raw_sha256`。成员来源文件必须登记在 `auxiliary_artifacts`，逐日成员与可得时间须从其原始证据重建。

规则：逐日成员按信号时点可知信息判定；市场代理等需要时使用 t−1 成员并显式排除目标；公司代码与证券 ID 混用、上市/退市/证券类别冲突、成员历史不完整或成员规则漂移均拒绝；不得用当前（回填）成员替代历史成员。

### 3.5 `ObservationV1`（真实）与四时间戳

`role`、`trade_date`、`value`（Decimal 字符串，可为 null 表示显式缺口）、`value_semantics`、`unit`、`currency`、`adjustment_policy`、`return_kind`、`observation_at`、`published_at`、`available_at`、`available_at_basis`、`ingested_at`、`revision_id`、`source_record_id`、`source_run_id`、`raw_sha256`、`evidence_digest`、`gap_reason`（如 `SUSPENSION`、`NOT_PUBLISHED`）。

| 时间戳 | 语义 | 能证明什么 |
| --- | --- | --- |
| `observation_at` | 事件时间 | 观测所属时点，不等于可得 |
| `published_at` | 来源发布时间 | 来源侧发布时点，必需 |
| `available_at` | 合同证据下的首次可得时间 | PIT 判定依据 |
| `ingested_at` | 本地落入时间 | 仅记录管道，**单独不构成 PIT 证明** |

PIT 规则：`available_at_basis=SOURCE_PUBLICATION_VERIFIED` 且 `published_at <= available_at <= signal_cutoff(trade_date)`，证据绑定到来源记录。缺 `published_at` 或 `available_at` 即拒绝；`available_at_basis=INGESTION` 即使时间早于截止也以 `REAL_INGESTED_AT_AS_PIT` 拒绝。晚于截止的观测记为 `PIT_UNPROVEN` 并进入覆盖聚合，不得填零、不得顺延、不得换源替代。

### 3.6 单位、复权、收益、角色

- `value_semantics ∈ {PRICE, TOTAL_RETURN_INDEX, SIMPLE_RETURN, LOG_RETURN}`；价格不得自动当收益。价格转收益必须由 `RealStudyContractV1.return_transform` 预先声明版本化规则（例如 `SIMPLE_CLOSE_TO_CLOSE_V1: P_t/P_prev-1`）、前收盘锚点、同一证券及复权规则、目标 horizon；转换后 `TARGET_OUTCOME` 观测是 `SIMPLE_RETURN`，原始价格仅作为可追溯输入。
- `adjustment_policy` 每角色唯一（`UNADJUSTED`、`FORWARD_ADJUSTED`、`BACKWARD_ADJUSTED` 加规则版本）；同一角色混用即拒绝；复权/公司行动转换需要版本化公式与原始字段追溯。
- 百分数按小数（0.01 = 1%）；单位、币种与合同不一致即拒绝。
- 角色顺序冻结，`TARGET_OUTCOME` 与控制角色分离；目标 outcome 的 horizon、signal cutoff 与控制序列集合必须在冻结合同与计划中预先声明。

### 3.7 预期域与覆盖

`RealExpectedDomainV1`：`domain_id`、`universe_id`、`expected_dates`（日历与窗口的交集，规范化时去重升序；重复日期本身拒绝）、`required_roles`（有序）、`warmup_dates`（域外、显式声明）、`denominator_rule = "|expected_dates| * |required_roles|"`、`coverage_gate`（精确有理数，如 `1/1`、`19/20`）、`min_joint_dates`（整数）。

`RealQualityReportV1`：`denominator`、`per_role_present`、`per_role_missing`、`joint_complete_dates`、`duplicates`、`invalid_values`、`pit_unproven`、`gaps`（`trade_date`、`role`、`reason`）、`coverage_numerator`、`coverage_denominator`、`gate_result`。`joint_complete_dates` 只计全部必需角色都有有效且 PIT 合格观测的日期，不计角色-日期单元数。

规则：分母只来自冻结日历与角色清单；缺项不得填零、不得缩小分母；比率用整数交叉相乘比较（`numerator * gate_d >= gate_n * denominator`），禁止浮点；同时必须满足 `joint_complete_dates >= min_joint_dates`，否则 `REAL_JOINT_DATES_BELOW_MIN`；门限、warm-up、最小样本与失败处置预先声明；被拒绝的准备不得暴露部分可执行矩阵。

### 3.8 谱系与摘要

必须绑定：原始文件（`raw_sha256`）、规范化结果、冻结合同摘要、计划摘要、适配器/代码身份、数据集摘要。身份必须可由内容复算；宿主绝对路径、当前时间、自报摘要均不足以作为身份。

## 4. 验证顺序、首错与聚合质量

| 阶段 | 检查 | 错误码 |
| --- | --- | --- |
| 0 | 结构、schema/adapter 版本、授权标志 | `REAL_INVALID_INPUT_STRUCTURE`、`REAL_UNSUPPORTED_SCHEMA_VERSION`、`REAL_EXECUTION_NOT_AUTHORIZED` |
| 1 | 合同、计划、outcome 前锁与 bundle 绑定；holdout 窗口隔离 | `REAL_CONTRACT_PLAN_MISMATCH`、`REAL_POST_OUTCOME_MUTATION`、`REAL_HOLDOUT_INJECTION` |
| 2 | 来源、角色、版本、原始字节与观测证据摘要、传输边界 | `REAL_SOURCE_ROLE_MISSING`、`REAL_SOURCE_IDENTITY_MISMATCH`、`REAL_SOURCE_VERSION_MISSING`、`REAL_RAW_HASH_MISMATCH`、`REAL_DIGEST_MISMATCH`、`REAL_ENDPOINT_UNBOUNDED`、`REAL_RETRIEVED_AT_MISSING` |
| 3 | 日历、时区、交易日 | `REAL_CALENDAR_MISSING`、`REAL_CALENDAR_CONFLICT`、`REAL_NON_TRADING_DATE` |
| 4 | 证券身份与成员 | `REAL_SECURITY_IDENTITY_CONFLICT`、`REAL_COMPANY_SECURITY_ID_CONFUSION`、`REAL_MEMBERSHIP_DRIFT`、`REAL_MEMBERSHIP_INCOMPLETE` |
| 5 | 时间戳与 PIT | `REAL_PUBLISHED_AT_MISSING`、`REAL_AVAILABLE_AT_MISSING`、`REAL_INGESTED_AT_AS_PIT`；晚到观测记录 `PIT_UNPROVEN` 并进入聚合 |
| 6 | 数值、单位、复权、收益、角色绑定、重复 | `REAL_INVALID_VALUE`、`REAL_UNIT_MISMATCH`、`REAL_ADJUSTMENT_MIX`、`REAL_RETURN_KIND_MISMATCH`、`REAL_ROLE_BINDING_MISMATCH`、`REAL_DUPLICATE_OBSERVATION` |
| 7 | 域、覆盖、门槛（聚合） | `REAL_DOMAIN_EMPTY`、`REAL_COVERAGE_BELOW_GATE`、`REAL_JOINT_DATES_BELOW_MIN` |

**首错语义**：阶段 0–6 的首次结构/身份/证据失败立即抛出 `RealSourceError(code, stage, locator)`，不再执行后续阶段。阶段 0 先阻断非法输入标志；阶段 1 对照外部保存的 outcome 前锁，而非输入自报锁；阶段 2 用注入读取器复算原始字节及逐行证据摘要，阶段 6 后、质量聚合前复算 `input_digest`。实际检查目标字节的审计位 `outcome_bytes_examined` 必须置 true，不能用 `research_outcome_consumed=false` 掩盖源验证读取。**聚合语义**只用于阶段 7：先完整统计全部缺口与原因，再依次判覆盖 gate、完整日期最小数。两者都必须 fail closed：拒绝结果固定为 `M4_REAL_SOURCE_REJECTION_V1`，其中 `matrix = None`、`accepted_roles = ()`、`execution_authorized = false`、`statistics_computed = false`、`research_outcome_consumed = false`；允许携带逐角色缺口明细，但不得携带任何可执行矩阵或统计量。

禁止的补救：自动换源、过滤掉问题行、填零、用当前成员回填、隐式日历、读取 outcome 后修改合同、访问 holdout。

## 5. 规范序列化与摘要

- 规范化 JSON：UTF-8、键排序、无多余空白、Decimal 以字符串表示（禁 float）、日期 `YYYY-MM-DD`、时间戳含显式偏移量；`source_runs` 按 `(role, run_id)`，`observations` 按 `(role, trade_date, revision_id, source_record_id)`，`expected_dates` 按日期排序；同一唯一键重复先拒绝，不能去重后吞掉冲突；文档以 LF 结束。
- 摘要输入排除：宿主绝对路径、`created_at`、未提供的本地时钟默认值、自报摘要字段、诊断消息。`retrieved_at` 是采集事件事实，参与 `source_run_digest`，但不参与转换后观测的 `semantic_dataset_digest`；仅改抓取时刻会改变采集/输入/完整准备摘要，但不会改变语义数据集身份。`raw_sha256` 始终由 `RawArtifactReaderV1` 的实际字节复算，读取失败也拒绝。
- `source_run_digest = sha256(canonical_bytes(SourceRunV1 去掉 proof_digest 等自报摘要，包含相对 raw_locator、raw_sha256、retrieved_at、revision_id、vintage_id)))`；`evidence_digest = sha256(canonical_bytes(ObservationV1 去掉 evidence_digest，包含 source_run_digest、raw_sha256 与规范化观测字段))`；`input_digest = sha256(canonical_bytes(bundle 的复算投影：去掉 input_digest、created_at、所有自报摘要，以复算的 source_run_digest/evidence_digest 替代))`；`semantic_dataset_digest = sha256(canonical_bytes(规范化角色-日期值、缺口原因、日历/成员/转换规则与合同/计划/代码身份，排除 raw_locator 与 retrieved_at))`；`dataset_digest = sha256(canonical_bytes(preparation 去掉 dataset_digest，包含 input_digest 与 semantic_dataset_digest))`。各摘要的 payload 必须在实现中固定版本标签、防止跨 schema 碰撞；复算不一致即 `REAL_DIGEST_MISMATCH`。
- 重排不变性：摘要由输入集合而非顺序决定；重复项在规范化前即被拒绝（`REAL_DUPLICATE_OBSERVATION`）。
- 伪造防护：`raw_sha256` 与 `evidence_digest` 必须由内容复算；自报摘要不通过即拒绝。

## 6. 三日期数值示例（可手工复算）

设定：开发窗口 2022-01-04 至 2022-01-06；日历裁定 3 个交易日；`roles = (TARGET_OUTCOME, FACTOR)`；warm-up 锚点 2021-12-31（域外，仅作首个收益基准，不计入分母）；合同预先冻结 `return_transform=SIMPLE_CLOSE_TO_CLOSE_V1`、`horizon=当日收盘相对前一交易日收盘`、`coverage_gate=1/1`、`min_joint_dates=2`、`signal_cutoff=交易日 20:00+08:00`（均为示例值，非通用默认）。所有日期、价格与序列 ID 均为虚构，用于算术，不是获取的真实行情。

| 角色 | 证券/序列 | trade_date | 值 | 语义 | `available_at` | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| 原始价格锚点（非角色观测） | `XSHG_600519` | 2021-12-31 | 100.00 | PRICE, CNY, UNADJUSTED | 域外锚点 | 仅基准 |
| 原始价格（非角色观测） | `XSHG_600519` | 2022-01-04 | 102.00 | 同上 | 2022-01-04T19:10+08:00 | 转换输入 |
| 原始价格（非角色观测） | `XSHG_600519` | 2022-01-05 | 102.00 | 同上 | 2022-01-05T19:05+08:00 | 转换输入 |
| 原始价格（非角色观测） | `XSHG_600519` | 2022-01-06 | 103.02 | 同上 | 2022-01-06T19:20+08:00 | 转换输入 |
| TARGET_OUTCOME | `XSHG_600519` | 2022-01-04 | 0.02 | SIMPLE_RETURN, `SIMPLE_CLOSE_TO_CLOSE_V1` | 2022-01-04T19:10+08:00 | 可用 |
| TARGET_OUTCOME | `XSHG_600519` | 2022-01-05 | 0.00 | 同上 | 2022-01-05T19:05+08:00 | 可用 |
| TARGET_OUTCOME | `XSHG_600519` | 2022-01-06 | 0.01 | 同上 | 2022-01-06T19:20+08:00 | 可用 |
| FACTOR | `XSHG_000300` | 2022-01-04 | 0.005 | SIMPLE_RETURN | 2022-01-04T18:00+08:00 | 可用 |
| FACTOR | `XSHG_000300` | 2022-01-05 | -0.002 | SIMPLE_RETURN | 2022-01-05T18:30+08:00 | 可用 |
| FACTOR | `XSHG_000300` | 2022-01-06 | 0.004 | SIMPLE_RETURN | 2022-01-07T09:00+08:00 | 晚于 01-06 20:00，PIT_UNPROVEN |

收益复算（按合同冻结的前一交易日收盘价，且两端原始价格都须在对应信号截止前有来源证据）：2022-01-04 为 `102.00 / 100.00 - 1 = 0.02`；2022-01-05 为 `102.00 / 102.00 - 1 = 0.00`；2022-01-06 为 `103.02 / 102.00 - 1 = 0.01`。目标观测记录的是这些转换后的 `SIMPLE_RETURN`，转换链保留原始价格证据。

覆盖复算：分母 `= 3 × 2 = 6`；分子 `= 3 (TARGET_OUTCOME) + 2 (FACTOR) = 5`；覆盖率 `= 5/6 ≈ 0.833333…`（精确有理数 5/6）；`joint_complete_dates = 2`。按 `coverage_gate = 1/1` 交叉相乘：`5 × 1 = 5 < 1 × 6 = 6`，故 `REAL_COVERAGE_BELOW_GATE`，输出拒绝报告，缺口明细含 `{trade_date: 2022-01-06, role: FACTOR, reason: PIT_UNPROVEN}`。边界核对：若合同在 outcome 前另行冻结 `coverage_gate = 5/6`，则 `5 × 6 >= 5 × 6` 且 `joint_complete_dates=2 >= min_joint_dates=2`，准备可通过质量门槛，但仍不授权执行；不得在观察结果后改门槛。本文未执行任何摘要计算，示例中的摘要一律写作 `<sha256:...>` 占位符，实现时必须由规范化字节复算。

## 7. M3 复用边界

| 可复用（语义、原则、结构） | 不可复用（案例常量与数据） |
| --- | --- |
| 相对路径加内容哈希的来源登记原则（[M3 来源登记](../reports/m3_stage3b_source_registry_v1.json)） | M3 的具体 provider、端点、原始文件与抓取批次 |
| 四时间戳分离、禁止海外同日静默连接（[M3 日频时点合同](../reports/m3_stage3b_return_and_timing_contract_v1.json)） | M3 的目标收益/指数贡献收益具体约定、固定开发域与 2023-01-01 holdout 起点 |
| t−1 成员、证券级身份与失败门（[M3 主代理合同 v2](../reports/m3_stage3br1_primary_proxy_contract_v2.json)） | 上证/601857/既有修复清单、行业与 Brent 控制序列 |
| 合成适配器的全域左连接、精确比率与 `MISSING_OBSERVATION`/`PIT_UNPROVEN` 原因码思路（[合成适配器设计](m4_dataset_adapter_design_v1.md)） | 合成 `evidence_kind`、合成 `evidence_digest`、合成日历/成员证据、`SYNTHETIC` 模式与执行门 |
| 规范化摘要与冻结合同/计划摘要的算法命名与复算原则 | 合成 capsule 摘要与 PR #20 的合成验收结论 |

M3 的案例修复和已消耗 holdout 不能补真实日历、成员历史、revision/发布时间与目标收益约定的缺口。

## 8. 后续桥接与阻塞

另立 Goal 所需的最小桥接集合：

1. `M4_HYPOTHESIS_CONFIG_V2`（或等价的独立真实配置类型）与新编译器/计划版本及迁移规则；不得扩冻结 V1 枚举。
2. 可获取且可验证的真实日历、成员历史、来源 revision 与发布时间来源（含许可与授权）。
3. 新版本真实矩阵构建器与执行器及真实执行门；合成入口继续拒绝真实 schema。
4. 真实 study contract 的 outcome 前冻结流程与 holdout 一次性授权、独立封存流程。
5. 原始字节保留与缓存策略，确保身份由内容而非抓取时刻或自报摘要决定。

阻塞（当前冻结接口内无法解决）：真实日历与成员来源未证明；`published_at`/`available_at` 的供给未证明；目标收益语义与 horizon 未冻结；真实执行入口与执行器未授权；PR #20 未合并，其合成验收不能作为真实证据。

未决决策（实现前需由用户与评审冻结）：`signal_cutoff` 与开发域取值；coverage gate、最小样本与 warm-up 默认；复权与公司行动转换公式；多市场控制序列的日历对齐规则；真实来源许可与再分发限制。

本文件**不**构成 real research readiness、implementation readiness 或 execution authorization。
