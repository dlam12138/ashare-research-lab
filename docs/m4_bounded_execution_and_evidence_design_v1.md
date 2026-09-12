# M4 有界执行与证据处置设计 v1

状态：DESIGN_ONLY / READY_FOR_IMPLEMENTATION_REVIEW。本文是 M4-A 剩余流水线边界
`Bounded Execution -> Reproducible Artifacts -> Evidence Disposition` 的设计规范与**拟议接口
契约**，尚未实现。文中全部类名、函数名、字段名、常量名与错误码都标记为**拟议 API**，
不冒充现有实现，也不表示本阶段获得任何实现、统计执行、真实数据、holdout 或 M4-B 授权。

基线：工作树 `D:/量化分析-m4-executor-design`，分支 `codex/m4-bounded-execution-design`，
HEAD `82278f21c9fbe969a549cd7a07381794f3c5d4e7`（Goal 契约提交）。`main` 与 `origin/main`
均为 `f34adcb17c9995392690a1df6bb5a10ee102eb09`（PR #12 合并点，2026-09-11 经 GitHub API
实测）。PR #9、#11、#12 均已合并；当前没有开启的 PR。

依赖并保持冻结的既有设计与实现：

- [M4 数据适配器设计 v1](m4_dataset_adapter_design_v1.md)
- [M4 合成分析矩阵设计 v1](m4_analysis_matrix_design_v1.md)
- [M4 合成分析矩阵验收场景 v1](m4_analysis_matrix_acceptance_cases_v1.md)
- 既有 Goal `agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md`（本文不覆盖、不改写）

## 1. 目标、范围与非目标

### 1.1 目标

在已验证的不可变设计矩阵之上，冻结一个**有界执行器**的完整契约，使下列问题不再留给实现者
做选择：

1. 唯一的、来源绑定的执行入口，以及它对既有 `validate_design_matrix` 的强制复用；
2. 从计划冻结的 `ordered_terms` / `coefficient_role` 到估计器输入的机械映射；
3. 规范十进制到估计器数值的转换边界、有限性与范围门、精度边界、失败顺序与稳定错误码；
4. 允许列表化的 OLS 方法契约（不支持即失败，不降级）；
5. bootstrap 的方法、PCG64、种子/重复数、块长策略、整行重采样、置信端点语义与禁用路径；
6. 只允许**真正的**注册稳健性派遣：验证请求 ID 与顺序、绑定注册 method_id、完整且不可变地
   转发既有 canonical parameters（含未知嵌套键），**不**忽略、**不**改写、**不**补默认值、
   **不**自动执行/扩展/选择；本阶段不解释参数统计语义；
7. POSITIVE / NEGATIVE / TWO_SIDED 三向完整处置表、置信要求与数据质量失败处置；
8. 不可变结果与产物 schema、规范序列化，以及**两层身份**（承接第 6.2 节）：上游
   source-chain 身份只绑定规范十进制与摘要；两种产物的 `artifact_digest` 都覆盖完整来源链、
   方法配置、代码与 schema 版本与显式 `synthetic_test_only` 来源标记（且都不含主机与绝对路径
   身份），但**按产物种类分别绑定**（承接第 6.2 节表）：
   - `ExecutionArtifactV1`（主产物，`statistics_computed = True`）：**必须**绑定
     `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` 的**全部 float64
     统计输出**（经 `Float64ValueV1` 规范化）；
   - `RobustnessArtifactV1`（注册稳健性派遣产物，`statistics_computed = False`）：
     **必须**绑定完整 source chain、请求顺序与注册顺序、`method_id`、**完整 canonical
     parameters**（含未知嵌套键）、`provenance` 与代码/schema/runtime；它**不计算任何统计量**，
     因此**不存在** float64 统计输出，也**不得**被描述为绑定了 estimator / bootstrap /
     conditional / evidence 的 float 块；
9. 执行授权、统计已计算、结果已读取三个状态的精确含义与转换；holdout 边界保持不授权，
   任何 holdout 请求 fail-closed；
10. 合成执行就绪与真实研究授权之间的硬隔离。

### 1.2 非目标（本设计不授权）

- 不实现任何产品代码。本文只冻结接口、字段、常量与失败语义；实现需另立 Goal 并获用户授权。
- 不修改 A.1 合同 schema、A.2 计划 schema、dataset preparation schema、matrix schema、
  既有摘要算法、既有测试、既有冻结研究产物或保护哈希。
- 不做真实数据适配、不访问 provider、不打开数据库、不读取真实行情、不进入 M4-B。
- **本阶段不调用** `mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、
  `crash.py`；不计算任何系数、区间、p 值、秩或其他结果，合成数据也不例外。
- 不把合成来源证据升级为真实研究证据。
- 不声称可估计性、统计显著、经济有效、可交易或任何 A 股机制结论。

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| matrix | 现有 `MatrixPreparationV1`，由既有四参数 `materialize_design_matrix` 产出 |
| preparation | 现有 `DatasetPreparationV1`，矩阵的已验证上游 |
| plan | 现有 `DeterministicAnalysisPlan`（A.2I） |
| artifact | 本设计新增的执行产物（拟议），是执行层的唯一输出 |
| primary effect | `term_role == "CONDITION_INDICATOR"` 的那一列的 `coefficient_role` 系数 |
| disposition | 由冻结证据规则给出的五词结论之一（第 8 节） |
| 判定 | 任何"支持/不支持/不确定"的措辞都只在合成产物内部有效 |

## 2. 已验证基线与来源绑定

### 2.1 现有能力链（本设计只消费，不重定义）

```text
config --compile_hypothesis_config--> contract.contract_digest
contract --build_analysis_plan--> plan.plan_digest
(contract, plan, bound_inputs) --materialize_analysis_dataset--> preparation.{input_digest, domain_digest, dataset_digest}
(preparation, contract, plan, bound_inputs) --materialize_design_matrix--> matrix.{..., matrix_digest}
(matrix, preparation, contract, plan, bound_inputs) --execute_bounded_analysis--> artifact.{..., artifact_digest}
```

执行层**不引入新的来源概念**：它只继承并暴露既有身份，并把它们全部纳入产物摘要。

### 2.2 唯一来源验证入口是既有 `validate_design_matrix`

执行层的唯一对外入口必须先调用既有五参数：

```text
validate_design_matrix(matrix, preparation, contract, plan, bound_inputs) -> None
```

其真实实现（`mechanism/planning/matrix.py`）依次执行：矩阵结构不变量与自摘要、四参数
`validate_dataset`（重新 materialize 并逐字节比较 `serialize_dataset`）、重投影、逐字节比较
`serialize_matrix`。

因此执行层：

- **不得**只信 `matrix.matrix_digest` 字符串；
- **不得**只信 `matrix.execution_authorized is False`；
- **不得**只跑 `serialize_matrix(matrix)`；
- **不得**直接消费 `preparation` 而不先跑五参数入口。

### 2.3 本设计实测的基线身份（2026-09-11，只读探针）

使用既有 fixture（`tests/test_m4_stage4a1_typed_contract.py::_document()/_compiled()` 与
`tests/test_m4_synthetic_dataset_adapter.py::_inputs()/_bound()`），走既有真实函数实测：

```text
contract_digest = ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457
plan_digest     = 45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981
input_digest    = c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602
domain_digest   = b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da
dataset_digest  = c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b
matrix_digest   = a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
sha256(serialize_dataset(preparation)) = 32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060
sha256(serialize_matrix(matrix))       = 70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa
validate_dataset(preparation, contract, plan, bound_inputs)      = 通过（无异常）
validate_design_matrix(matrix, preparation, contract, plan, bound_inputs) = 通过（无异常）
matrix: len(rows) = 3 ; len(columns) = 5 ; response_role = "TARGET_OUTCOME"
matrix.execution_authorized = False ; matrix.statistics_computed = False
```

计划的相关冻结节（既有 `plan_to_canonical_dict` 实测输出，原样引用）：

```json
{"design_plan":{"model_family":"OLS","ordered_terms":[
  {"coefficient_role":"alpha","position":1,"source_series_role":null,"term_role":"INTERCEPT"},
  {"coefficient_role":"beta_factor","position":2,"source_series_role":"FACTOR","term_role":"FACTOR_CONTINUOUS"},
  {"coefficient_role":"beta_control_0001","position":3,"source_series_role":"CONTROL_0001","term_role":"CONTROL_0001"},
  {"coefficient_role":"beta_control_0002","position":4,"source_series_role":"CONTROL_0002","term_role":"CONTROL_0002"},
  {"coefficient_role":"gamma_condition","position":5,"source_series_role":"CONDITION_INDICATOR","term_role":"CONDITION_INDICATOR"}],
  "response_role":"TARGET_OUTCOME"}}
{"bootstrap_plan":{"confidence_level":"0.95","enabled":true,"method_id":"MOVING_BLOCK_BOOTSTRAP_V1",
  "moving_block_semantics":{"block_length_policy_id":"N_CUBERT_ROUNDED_CLAMP_1_20_V1",
  "method_id":"MOVING_BLOCK_BOOTSTRAP_V1","row_policy":"complete-row resampling",
  "sampling":"non-circular overlapping moving blocks"},"replications":1000,"rng":"PCG64","seed":42}}
{"robustness_plan":{"automatic_expansion":false,"automatic_selection":false,"dispatch_only":true,
  "entries":[{"method_id":"CONDITIONAL_DESCRIPTIVES_V1",
  "parameters":{"trim":"0.0100","window":["1","2","3"]},"robustness_id":"SYNTH_ROBUSTNESS_1"}]}}
安全提示：这是**计划对象的规范字典**（键已排序、数字已规范化为十进制字符串），不是 A.1 源文档
的字面文本；`_canonical_json_value` 已把嵌套的 `window: [1,2,3]` 规范化为 `["1","2","3"]`。
执行层必须逐字转发这一层，不得再规范化一次（第 12.2 节）。
{"evidence_plan":{"confidence_requirement":"0.95","data_quality_failure_disposition":"INCONCLUSIVE",
  "dispatch_only":true,"expected_direction":"POSITIVE","outcome_read":false,
  "required_statistic_roles":["PRIMARY_EFFECT_ESTIMATE","PRIMARY_EFFECT_CI_LOWER",
  "PRIMARY_EFFECT_CI_UPPER","CONDITIONAL_MEAN_DIFFERENCE","CONDITIONAL_MEDIAN_DIFFERENCE",
  "PRIMARY_SAMPLE_COVERAGE"],
  "rule_id":"SYNTH_EVIDENCE_RULE_1",
  "statistic_role_bindings":{"PRIMARY_EFFECT_CI_LOWER":"frozen bootstrap confidence interval lower bound for gamma_condition","PRIMARY_EFFECT_CI_UPPER":"frozen bootstrap confidence interval upper bound for gamma_condition","PRIMARY_EFFECT_ESTIMATE":"CONDITION_INDICATOR coefficient role gamma_condition"}}}
{"holdout_boundary":{"execution_authorized":false,"policy_id":"NO_HOLDOUT_AUTHORIZED"}}
{"conditional_summary_plan":{"condition_labels":["CONDITION","ORDINARY"],"dispatch_only":true,
  "required_statistic_roles":["CONDITION_COUNT","ORDINARY_COUNT","CONDITION_MEAN","ORDINARY_MEAN",
  "CONDITION_MEDIAN","ORDINARY_MEDIAN","CONDITION_MINUS_ORDINARY_MEAN","CONDITION_MINUS_ORDINARY_MEDIAN"],
  "source_roles":{"condition":"CONDITION_INDICATOR","outcome":"TARGET_OUTCOME"}}}
```

### 2.4 基线 fixture 的规模事实（决定了验收正例的形状）

基础 fixture 的矩阵是 **3 行 × 5 列**。对任意矩阵 `X`（n 行、k 列）恒有
`rank(X) <= min(n, k)`，故 `rank <= 3 < 5 = k`：**该矩阵在冻结的秩门下必然被拒绝**，
不存在"基础 fixture 直接执行成功"的路径。

这不是缺陷，而是设计想要的负例：它证明秩门必须真的存在。本设计因此把验收正例定义在
**n >= k 且列满秩**的合成 fixture 上（第 12.3 节），并把基础 fixture 固定为
`SINGULAR_DESIGN` 负例。

## 3. 冻结的常量

全部为**拟议**常量；实现不得改名、改值或新增同类常量。

```text
ARTIFACT_SCHEMA_VERSION            = "M4_BOUNDED_EXECUTION_ARTIFACT_V1"
ROBUSTNESS_ARTIFACT_SCHEMA_VERSION = "M4_REGISTERED_ROBUSTNESS_ARTIFACT_V1"
EXECUTOR_VERSION                   = "M4_BOUNDED_DAILY_CONDITIONAL_OLS_EXECUTOR_V1"
ESTIMATOR_CONTRACT_ID              = "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"
MODEL_FAMILY                       = "OLS"
NUMERIC_BACKEND                    = "numpy.linalg.lstsq"
MAX_ABS_CELL_DECIMAL               = "1000000"
BLOCK_LENGTH_POLICY_ID             = "N_CUBERT_ROUNDED_CLAMP_1_20_V1"
BOOTSTRAP_MIN_REPLICATIONS         = 2
PROVENANCE_CLASS                   = "SYNTHETIC_TEST_ONLY"
PRIMARY_TERM_ROLE                  = "CONDITION_INDICATOR"     # 唯一分派键，来自计划的 term_role
INTERCEPT_TERM_ROLE                = "INTERCEPT"               # 唯一分派键，来自计划的 term_role
```

`MAX_ABS_CELL_DECIMAL` 的理由：日频十进制收益的量级在 `1e-2` 附近；`1e6` 远高于任何合法
合成取值，又远低于 float64 溢出阈值，因此该门只拒绝"明显越界"的规范十进制值，不会静默
拒绝合法输入。边界含端点（`abs(value) == 1000000` 通过）。

## 4. 拟议公开接口

### 4.1 签名（本轮冻结）

```text
# 拟议新模块：ashare_research.mechanism.execution.bounded（落点属实现评审项）
execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs) -> ExecutionArtifactV1
execution_artifact_to_canonical_dict(artifact) -> dict          # 独立副本
serialize_execution_artifact(artifact) -> bytes                 # 规范字节
validate_execution_artifact(artifact, matrix, preparation, contract, plan, bound_inputs) -> None

prepare_registered_robustness_dispatch(matrix, preparation, contract, plan, bound_inputs,
                                       robustness_ids) -> RobustnessArtifactV1
robustness_artifact_to_canonical_dict(artifact) -> dict
serialize_robustness_artifact(artifact) -> bytes
validate_robustness_artifact(artifact, matrix, preparation, contract, plan, bound_inputs) -> None
```

这就是全部公开面（8 个入口）。硬性要求：

- 唯一的**统计执行**入口是 `execute_bounded_analysis`；稳健性入口的名字是
  `prepare_registered_robustness_dispatch`，因为本阶段它**不执行任何统计**，只做注册派遣的
  验证与不可变绑定（第 12 节）。名称里不得出现 "execute"，以免被读成"稳健性统计已运行"。
- 两个入口都**必须**同时接收 `matrix, preparation, contract, plan, bound_inputs`：
  `validate_design_matrix` 的第一个参数就是 `matrix`，`validate_dataset` 还需要
  `preparation, contract, plan, bound_inputs`。**不存在**只吃 `matrix` 的公开入口，
  也不存在 `**kwargs`：任何未声明的关键字参数（例如 `holdout=...`、`window=...`、
  `split=...`、`real_data=...`）都必须是 `TypeError`，而不是被忽略。
- `prepare_registered_robustness_dispatch` 的 `robustness_ids` 是**显式、有序、非空**的注册 ID
  元组；产物 `entries` 顺序严格等于请求顺序。没有"全部注册项"开关，没有自动补全，
  没有自动执行。它返回的是"已绑定的派遣计划"，不是统计结果。
- 8 个入口都不做 IO，不访问路径、环境、时钟、网络、provider、数据库或 holdout；随机性只来自
  计划冻结的 `seed` + `PCG64`（且只被 `execute_bounded_analysis` 使用）。
- 私有实现细节（例如 `_disposition`、`_block_length`、`_cell_to_float64`）不得导出、
  不得作为验收入口、不得被文档描述为 API。

### 4.2 公开面之外的拒绝面（结构性，而非约定）

```text
holdout 参数        -> 不存在（TypeError）
真实数据模式        -> bound_inputs.mode != "SYNTHETIC" 时 UNSUPPORTED_DATASET_MODE（且上游先以 UNSUPPORTED_MODE 拒绝）
授权提升参数        -> 不存在（TypeError）
结果选择/排序参数    -> 不存在（TypeError）
```

即"任何 holdout 请求 fail-closed"在本设计里首先由**签名本身**保证：接口没有可传 holdout 的
位置，传了就是 `TypeError`。

## 5. 执行输入映射（核心冻结项）

### 5.1 估计器输入的列来源只来自计划

设计矩阵的列顺序由计划机械决定（矩阵设计第 3.1 节）。执行层必须**逐项断言**：

```text
[(c.position, c.term_role, c.coefficient_role) for c in matrix.columns]
    ==
[(t["position"], t["term_role"], t["coefficient_role"]) for t in plan.design_plan.ordered_terms]
```

不成立即 `PLAN_TERM_ROLE_MISMATCH`。据此定义：

```text
k        = len(matrix.columns)                      # 设计列数
X[i][j]  = float64(matrix.rows[i].cells[j])         # j 从 0 起，等于 position-1
terms[j] = (position, term_role, coefficient_role)  # 与 X 的第 j 列一一对应
```

**映射规则只按位置 + `term_role` + `coefficient_role`**，取值只来自
`matrix.rows[*].cells`。明确禁止：

- 任何 M3 固定列名：`DESIGN_COLUMNS`、`ANALYSIS_COLUMNS`、`market_ex_target_return`、
  `oil_return`、`industry_return`、`Crash_t`、`target_analysis_return`、`gamma`；
- 任何固定开发期：`WARMUP_START`、`DEVELOPMENT_START`、`DEVELOPMENT_END`、`HOLDOUT_START`，
  以及 `contract.development` 的日期字面量；
- 任何按名字排序、按字母排序、按 `source_series_role` 建表、补列、删列或合并同名列；
- 任何从 `mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、
  `analysis_dataset.py`、`analysis_contracts.py` 导入的行为。

### 5.2 响应向量来自 preparation，且必须与矩阵逐行对齐

矩阵列**不含**响应角色（矩阵不变量：`response_role` 不得成为列），因此 `y` 只能来自
`preparation.complete_rows`：

```text
r = matrix.response_role                         # 必须等于 plan.design_plan.response_role
j = preparation.role_order.index(r)              # 必须命中
y[i] = float64(preparation.complete_rows[i][1][j])
```

强制对齐断言（任一失败即 `MATRIX_PREPARATION_ALIGNMENT_MISMATCH`）：

```text
len(matrix.rows) == len(preparation.complete_rows)
[r.trade_date for r in matrix.rows] == [td for td, _, _ in preparation.complete_rows]
int(matrix.rows[i].cells[condition_index]) == preparation.complete_rows[i][2]   # 指示列交叉校验
```

其中 `condition_index` 由 `term_role == PRIMARY_TERM_ROLE` 的唯一列给出（不得写死位置）。
`matrix.response_role != plan.design_plan.response_role` 即 `PLAN_TERM_ROLE_MISMATCH`。

### 5.3 primary effect 的机械定位

```text
condition_terms = [j for j, t in enumerate(terms) if t.term_role == PRIMARY_TERM_ROLE]
intercept_terms = [j for j, t in enumerate(terms) if t.term_role == INTERCEPT_TERM_ROLE]
```

要求 `len(condition_terms) == 1` 且 `len(intercept_terms) == 1`，否则
`PLAN_TERM_ROLE_MISMATCH`。于是：

```text
primary_effect_position = condition_terms[0] + 1
primary_effect_role     = terms[condition_terms[0]].coefficient_role
primary_effect          = beta[condition_terms[0]]
```

`plan.evidence_plan.statistic_role_bindings` 的三个键（`PRIMARY_EFFECT_ESTIMATE`、
`PRIMARY_EFFECT_CI_LOWER`、`PRIMARY_EFFECT_CI_UPPER`）必须存在且为非空字符串，且
`primary_effect_role` 必须是 `PRIMARY_EFFECT_ESTIMATE` 绑定文本的子串（一致性检查）。
**绑定文本不是分派来源**：分派只按 `term_role`/`coefficient_role`；绑定文本由
`validate_analysis_plan` 冻结，执行层不解析、不解释、不用它决定任何取值。

### 5.4 证据规则要求的统计角色必须全部可解析

`plan.evidence_plan.required_statistic_roles` 的六项必须逐一映射到产物内的确定位置：

| 统计角色 | 产物位置 |
| --- | --- |
| `PRIMARY_EFFECT_ESTIMATE` | `estimator.primary_effect` |
| `PRIMARY_EFFECT_CI_LOWER` | `bootstrap.primary_effect_lower` |
| `PRIMARY_EFFECT_CI_UPPER` | `bootstrap.primary_effect_upper` |
| `CONDITIONAL_MEAN_DIFFERENCE` | `conditional_descriptives["CONDITION_MINUS_ORDINARY_MEAN"]` |
| `CONDITIONAL_MEDIAN_DIFFERENCE` | `conditional_descriptives["CONDITION_MINUS_ORDINARY_MEDIAN"]` |
| `PRIMARY_SAMPLE_COVERAGE` | `sample.{coverage_numerator, coverage_denominator, coverage_gate}` |

任一不可解析即 `MISSING_REQUIRED_STATISTIC_ROLE`。`conditional_descriptives` 的键集合与顺序
必须**精确等于** `plan.conditional_summary_plan.required_statistic_roles`（八项）。

## 6. 数值边界与 OLS 方法契约

### 6.1 规范十进制到估计器的转换

```text
MAX_ABS_CELL_DECIMAL = "1000000"

def _cell_to_float64(text):              # 拟议，私有
    d = Decimal(text)                    # 规范十进制字符串，矩阵层已校验
    if not d.is_finite():    -> ExecutionError("NON_FINITE_CELL")
    if abs(d) > Decimal(MAX_ABS_CELL_DECIMAL): -> ExecutionError("CELL_OUT_OF_RANGE")
    v = float(d)                         # IEEE-754 正确舍入
    if not math.isfinite(v): -> ExecutionError("NON_FINITE_CELL")
    return v
```

- 转换**只发生一次**，方向单一：规范十进制 -> float64。执行层不得回写、不得"修好"任何单元格，
  也不得把 float 结果回灌进矩阵、数据集或计划的**上游**身份（第 6.2 节第一层）。
- 矩阵层已经保证每个单元格是规范十进制字符串（`"0"` 是唯一的零表示、整数不带小数点），
  因此 `Decimal(text)` 不会失败；若失败，属结构错误 `INVALID_INPUT_STRUCTURE`。

### 6.2 精度边界与**两层身份**（明确写入产物）

身份不是"一个"边界，而是**两层**：第一层的绑定对象是上游 source-chain，第二层的绑定对象是
执行层产物，且第二层**按产物种类分别绑定**（主产物 vs 注册稳健性派遣产物）。三者不得互相
代替、也不得互相否定：

| 层 | 覆盖对象 | 身份绑定什么 | 绝不绑定什么 |
| --- | --- | --- | --- |
| 上游 source-chain 身份（既有，本设计不改） | `contract_digest`、`plan_digest`、`input_digest`、`domain_digest`、`dataset_digest`、`matrix_digest` | 只绑定**规范十进制字符串**、规范 ISO 日期、整数/布尔与 SHA256 摘要 | float64；执行层不得改动任何一个上游摘要 |
| 执行产物身份（本设计新增，**按产物种类分别绑定**） | `artifact_digest` —— **(a) 主产物 `ExecutionArtifactV1`** | **必须**绑定完整来源链、`provenance`、完整 `method_configuration`（含 `numeric_runtime`、代码与 schema 版本）、`sample`、**以及估计器、bootstrap、条件描述统计与证据块里的全部 float64 统计输出**（经 `Float64ValueV1` 规范化渲染）与三个状态位 | 主机、工作目录、绝对路径、会话或环境身份 |
| 执行产物身份（同上） | `artifact_digest` —— **(b) 注册稳健性派遣产物 `RobustnessArtifactV1`** | **必须**绑定完整 source chain（六个上游摘要）、`provenance`、完整 `method_configuration`（含 `numeric_runtime`、代码与 schema 版本）、`sample`、`dispatch.requested_ids` / `dispatch.registered_ids`（请求顺序与注册顺序）、`entries[*].{robustness_id, request_ordinal, registration_ordinal, method_id, parameters, parameters_canonical_json}`（**完整 canonical parameters**，含未知嵌套键）、`artifact_schema_version`、`executor_version` 与三个状态位 | 主机、工作目录、绝对路径、会话或环境身份；**以及任何 float64 统计输出——该产物 `statistics_computed = False`，不计算、也不含 `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` 块，因此不存在可绑定的 float 统计量** |

两层的连接方式是**单向**的：主产物的 float64 值只由 `source_chain` 里的规范十进制经第 6.1 节
的**唯一一次**确定性转换得到，因此产物身份可复算；反过来，float64 值**永不**写入上游矩阵、
数据集、合同或计划，也**永不**参与任何上游摘要。即：

- "float64 永不进入身份"这一说法只对**上游 source-chain 身份**成立；
- 对**主产物的 `artifact_digest`**，float64 统计输出是必须被绑定的内容（第 10.4 节把
  `estimator`/`bootstrap`/`conditional_descriptives`/`evidence` 全部列入主产物摘要覆盖范围）。
  若主产物摘要不绑定 float64 输出，"改动一个系数而不改摘要"就能通过校验，产物将无法被独立复核；
- 对**注册稳健性派遣产物的 `artifact_digest`**，被绑定的不是统计量（它一个都不算），
  而是来源链、请求/注册顺序、`method_id`、完整 canonical parameters、`provenance` 与
  代码/schema/runtime。把不存在的 float 统计输出写成它的绑定内容，等于把"已绑定"谎报成
  "已计算"（第 9.1、12 节）。

| 边界 | 规则 |
| --- | --- |
| 上游身份边界 | 只有规范十进制字符串与 SHA256 摘要（上述六个上游摘要）。float64 **永不**进入上游身份 |
| 主产物身份边界 | 全部数值结论以 `Float64ValueV1{float64_hex, canonical_decimal}` 规范化后进入 `artifact_digest`；判定只用 float64 值与 `float64_hex` |
| 派遣产物身份边界 | `artifact_digest` 绑定来源链、请求/注册顺序、`method_id`、完整 canonical parameters、`provenance`、代码/schema/runtime 与状态位；**不含任何 float64 统计输出**（无统计块，`statistics_computed = False`） |
| float64 进入身份的形式（仅主产物） | 主产物的 float64 输出只以 `Float64ValueV1` 的两个**文本**渲染（`float64_hex` + `canonical_decimal`）进入 `artifact_digest`，**不是**平台相关的原始内存字节；`numeric_runtime` 同时进入身份，使跨运行时差异可检测（第 16 节）。派遣产物没有 float64 输出，因此该行对它不适用 |
| 估计器算术边界 | float64（numpy），无扩展精度、无 `float128`、无 decimal 估计 |
| 比较边界 | 严格比较，**禁止**任何 epsilon / `isclose` / `allclose` / 容差 |
| 零 | 恰好 `0.0`；`-0.0` 在比较上等于 `0.0`，但在 `float64_hex` 上不同（`-0x0.0p+0`），因此主产物身份不同 |
| 输出渲染 | `Float64ValueV1{float64_hex, canonical_decimal}`，两者必须自洽 |

```text
float64_hex       = float.hex(value)                  # 精确、无歧义
canonical_decimal = canonical_decimal(repr(value))    # 复用既有 hypothesis_config.canonical_decimal
自洽检查：float.fromhex(float64_hex) == value 且 canonical_decimal(repr(float.fromhex(float64_hex))) == canonical_decimal
非有限值：canonical_decimal(repr(inf)) 抛 HypothesisConfigError -> 必须映射为 NON_FINITE_ESTIMATE
```

`canonical_decimal` 是**伴随渲染**，不是精确身份渲染，但它**不是**"固定 17 位有效数字、尾数被
丢弃"：它作用于 Python `float` 的 `repr`，而 `repr` 给出的是**最短 round-trip 十进制**
（shortest round-trip decimal）——唯一确定该 float64 的**最少位数**十进制文本，位数随取值变化。
两者都是纯函数；区别只在身份强度：

- `float64_hex = float.hex(value)` 是**精确二进制身份**渲染，但本设计**不把它**当作唯一身份
  渲染：`float64_hex` 与 `canonical_decimal` 两个字符串**并行**进入 `artifact_digest`
  （第 10.4 节），因此两条渲染路径都必须逐字节稳定；
- `canonical_decimal` 由 `repr` 派生，同一 float64 值恒得同一文本。但它**不是单射**：
  `float(repr(-0.0)) == float(repr(0.0)) == 0.0`，而 `repr(-0.0) == "-0.0"` 与 `repr(0.0)
  == "0.0"` 是两个不同文本，经既有 `canonical_decimal` 折叠后**同为 `"0"`**——即符号位不进入
  `canonical_decimal`。因此"这是哪一个 float64"由 `float64_hex` 唯一确定，不由
  `canonical_decimal` 确定；`0.0` 与 `-0.0` 的产物身份不同靠的是 `float64_hex`
  （`"0x0.0p+0"` vs `"-0x0.0p+0"`）。

**本会话只读实测**（2026-09-11，直接调用既有 `hypothesis_config.canonical_decimal`，不涉及任何统计计算）：

```text
value                     repr                     float.hex                    canonical_decimal
0.0                       0.0                      0x0.0p+0                     0
-0.0                      -0.0                     -0x0.0p+0                    0
0.5                       0.5                      0x1.0000000000000p-1         0.5
0.1                       0.1                      0x1.999999999999ap-4         0.1
1.0/3.0                   0.3333333333333333       0x1.5555555555555p-2         0.3333333333333333
1e16                      1e+16                    0x1.1c37937e08000p+53        10000000000000000
1e-5                      1e-05                    0x1.4f8b588e368f1p-17        0.00001
123456789.123456789       123456789.12345679       0x1.d6f34547e6b75p+26        123456789.12345679
float("inf")              —                        —                            raises HypothesisConfigError
```

三点由此确定：`canonical_decimal` 的位数随取值变化（**不存在固定的 17 位**；`1.0/3.0` 的 16 位
与 `123456789.12345679` 的 17 位都只是 shortest-round-trip 的结果）；`repr` 的指数形态
（`"1e+16"`、`"1e-05"`）会被既有 `canonical_decimal` 折叠成规范十进制文本，因此产物里的
`canonical_decimal` 形态只由**既有函数**决定；`0.0` 与 `-0.0` 的 `canonical_decimal` 相同而
`float64_hex` 不同。

因此判定只用 float64 值与 `float64_hex`，`canonical_decimal` 只用于人读；上述表述**不得**被
改写成"固定 17 位有效数字且尾部被截断"这类陈述。`float64_hex` 与 `canonical_decimal`
**并行进入产物身份**（第 10.4 节），两者都是同一 float64 值的确定性函数，因此身份可复算；
但两者之间的一致性只在 `float.fromhex(float64_hex) == 原值` 这一层校验：

```text
float.fromhex(float64_hex) == 原 float64 值    -> 不成立即 INVALID_INPUT_STRUCTURE
canonical_decimal(repr(float.fromhex(float64_hex))) == canonical_decimal   -> 不成立即 INVALID_INPUT_STRUCTURE
```

即：`float64_hex` 是精确、无歧义的**身份**渲染，`canonical_decimal` 是可读的**伴随**渲染；
一致性校验验证的是"两者来自同一个 float64 值"，**不是**要求两者字符串相等
（`"-0x0.0p+0"` 与 `"0"` 是合法的同一对，且它们共同定义的产物身份不同于 `"0x0.0p+0"` 与 `"0"`）。

### 6.3 OLS 方法允许列表

```text
ALLOWED = {"DAILY_CONDITIONAL_CONTROLLED_OLS_V1"}      # 只有一项
plan.analysis_method_id not in ALLOWED      -> UNSUPPORTED_ANALYSIS_METHOD
plan.design_plan.model_family != "OLS"      -> UNSUPPORTED_MODEL_FAMILY
```

不支持的方法**必须失败**：不得回退到其它估计器、不得回退到 M3 路径、不得跳过、不得降级为
描述统计。

### 6.4 估计步骤与秩门

```text
X = numpy.asarray(rows_as_float64, dtype=numpy.float64)     # n x k
y = numpy.asarray(response_as_float64, dtype=numpy.float64) # n
rank_primary = int(numpy.linalg.matrix_rank(X))
if rank_primary != k:                        -> ExecutionError("SINGULAR_DESIGN")
beta, residuals, rank_secondary, singular_values = numpy.linalg.lstsq(X, y, rcond=None)
if int(rank_secondary) != k:                 -> ExecutionError("SINGULAR_DESIGN")
if len(residuals) not in (0, 1):             -> ExecutionError("ESTIMATOR_FAILURE")
coefficients[j] = (terms[j].position, terms[j].term_role, terms[j].coefficient_role, beta[j])
```

硬性语义：

- **秩不足即拒绝**：不返回最小范数解（不使用 `pinv` 的降级路径）、不丢控制项、不改列、
  不做变量选择、不做任何"降级成功"。
- **不得**调用 `statsmodels`、`mechanism/regression.py`、`mechanism/bootstrap.py`、
  `mechanism/robustness.py`、`mechanism/evidence.py`：它们绑定 M3 固定列名、固定开发期与
  固定阈值，复用即回归 M3，属禁止范围。
- 检查规模：`n >= 2`（否则连截距都无法识别，秩门已经拒绝，无需额外常量）。
- 主样本的秩门与每个 bootstrap 重采样的秩门使用同一规则，但错误码不同（第 6.5 节）。

### 6.5 数值输出校验

`beta`、`singular_values`、`residuals`（若存在）、bootstrap 端点、条件描述统计值全部经过：

```text
if not math.isfinite(value):  -> ExecutionError("NON_FINITE_ESTIMATE")
```

`NaN` 与 `±inf` 一律 fail-closed，不得写成 `null`、不得写成 `0`、不得记为"不可用"后继续。

## 7. Bootstrap 契约

### 7.1 声明与执行必须分开记录，但**不得分叉**

计划里 `bootstrap_plan` 是**声明**（`bootstrap_enabled` 记入 `method_configuration`）；产物里
`bootstrap` 块是**实际执行**。两者必须分别可读，但**不得互相矛盾**：

```text
actual_enabled = plan.bootstrap_plan.enabled        # 严格复制，不做任何转换、不重新推导
产物 bootstrap.enabled is actual_enabled            # 不成立即 INVALID_INPUT_STRUCTURE
```

冻结语义（消除"计划启用、实际禁用"的未授权运行时降级）：

1. `plan.bootstrap_plan.enabled is True` -> 执行层**必须**执行 bootstrap，并把
   `bootstrap.enabled = True` 与真实端点写入产物；
2. 该路径上任何失败（方法/RNG/重复数/块长/重采样秩/数值有限性）都让**整个执行 fail-closed**，
   不产出产物，**不存在**"先按 enabled=false 出一个无区间产物"的降级路径；
3. `plan.bootstrap_plan.enabled is False`（A.1 已强制此时 `method_id == "DISABLED"`）才进入
   第 7.7 节禁用路径，`bootstrap.enabled = False` 且端点全为显式 `null`；
4. 执行层**不得**自行推导或改写 `enabled`：不得因为"端点无法算出""重采样秩不足""重复数太低"
   而把 `True` 改成 `False`，也不得把 `False` 改成 `True` 去补算一个区间；
5. 计划层已保证 `enabled` 与 `method_id` 一致（`enabled=True` 必非 `DISABLED`，
   `enabled=False` 必为 `DISABLED`，既有 `hypothesis_config` 的 `INVALID_BOOTSTRAP_POLICY`），
   执行层不得放宽该配对，也不得据此发明第三种组合。

因此"声明 enabled=true、实际 enabled=false/None"在本设计里是**不可表达**的状态：
产物里 `bootstrap.enabled` 只可能是计划声明的那个布尔值；`None` 不再是合法取值。
`bootstrap` 块中与方法相关的字段（`method_id`、`block_length`、`replications`、`seed`、
`rng`、`confidence_level`、`interval_alpha`、`lower_index`、`upper_index`、
`primary_effect_lower`、`primary_effect_upper`）在 `enabled=True` 时**必须**全部非 `None`，
在 `enabled=False` 时**必须**全部为 `None`；任一不成立即 `INVALID_INPUT_STRUCTURE`。

### 7.2 方法与 RNG 允许列表

```text
启用时： plan.bootstrap_plan.enabled is True   -> 产物 bootstrap.enabled 必须为 True
        bootstrap_plan.method_id == "MOVING_BLOCK_BOOTSTRAP_V1"   -> 否则 UNSUPPORTED_BOOTSTRAP_METHOD
        bootstrap_plan.rng == "PCG64"                             -> 否则 UNSUPPORTED_BOOTSTRAP_RNG
        bootstrap_plan.replications >= BOOTSTRAP_MIN_REPLICATIONS -> 否则 INSUFFICIENT_REPLICATIONS
        generator = numpy.random.Generator(numpy.random.PCG64(seed))   # 每次执行只建一次
禁用时： plan.bootstrap_plan.enabled is False 且 method_id == "DISABLED"
        -> 产物 bootstrap.enabled 必须为 False，不建 generator、不抽样、不访问任何随机数 API
```

`enabled` 是**唯一的分派开关**，且只由计划提供；两个分支互斥且穷尽。既不存在
"计划启用但实际禁用"，也不存在"计划禁用但实际补算"。

`seed` 与 `replications` **只**来自计划；执行层不得提供覆盖、不得自动增大重复数、不得
"补跑"。

### 7.3 块长策略（精确整数规则）

计划冻结 `block_length_policy_id = "N_CUBERT_ROUNDED_CLAMP_1_20_V1"`。
`N_CUBERT_ROUNDED_CLAMP_1_20_V1` 的**注册实现**是本节的精确整数规则（不是浮点 `pow`）：

```text
L(n) = max(1, min(20, k))，其中 k 是唯一满足 (2k-1)^3 <= 8n < (2k+1)^3 的整数
等价的整数算法： k = 0; while (2k+1)**3 <= 8n: k += 1
```

理由：`n ** (1/3)` 依赖 libm 的 `pow`，其最后一位在不同平台/版本上不保证一致；上述整数判据
只用到整数立方与比较，结果在任意平台上逐位相同。

**实测一致性**（2026-09-11，纯算术探针，未调用任何统计模块）：对 `n = 1..200000`，整数规则
与 `int(numpy.floor(numpy.float64(n) ** (1/3) + 0.5))` 的钳位结果**逐值相同**（不一致数 = 0），
与 Python `math.floor(n ** (1.0/3.0) + 0.5)` 的钳位结果也逐值相同（不一致数 = 0）。
抽样值：

```text
n : 1  2  3  4  5  6  8  10 20 27 64 125 216 1000 10000
L : 1  1  1  2  2  2  2  2  3  3  4  5   6   10   20
```

执行层必须断言 `L <= n`，否则 `BLOCK_LENGTH_EXCEEDS_ROWS`。

### 7.4 整行重采样（complete-row resampling）

一次重采样是**行索引序列**，不是逐列抽样：

```text
n = len(matrix.rows) ; L = L(n) ; blocks = ceil(n / L) = (n + L - 1) // L
第 r 次重复（r = 0..replications-1，升序，每次一次调用）：
    starts = generator.integers(0, n - L + 1, size=blocks, endpoint=False)   # 非循环、可重叠、均匀
    idx    = concat([range(s, s + L) for s in starts])[:n]
    X_r    = X[idx] ; y_r = y[idx]
```

冻结理由与后果：

- 抽样单位是**整行**：响应、因子、控制项与指示列必须来自同一行，否则会破坏日频条件结构的
  联合分布；
- 块起点在 `[0, n-L]` 上均匀且**非循环**（不跨样本首尾环绕），与计划的
  `sampling = "non-circular overlapping moving blocks"` 一致；
- 抽样调用序列（每次重复一次 `integers`、升序、`size=(blocks,)`）本身是契约的一部分：
  换成分批调用或不同顺序会让端点变化，属实现错误；
- 重采样样本**不进入产物**：产物只保留重复数、块长、种子、RNG、端点与端点序号，
  从结构上排除"用样本做二次选择/聚合"。

### 7.5 每次重复的估计与秩门

每次重复都用与主样本相同的 OLS 契约（第 6.4 节）重拟合，并单独过秩门：

```text
if int(numpy.linalg.matrix_rank(X_r)) != k:  -> ExecutionError("SINGULAR_RESAMPLE")
if 重采样秩门通过但 lstsq 二次秩 != k:        -> ExecutionError("SINGULAR_RESAMPLE")
primary_r = beta_r[primary_effect_position - 1]
if not math.isfinite(primary_r):              -> ExecutionError("NON_FINITE_ESTIMATE")
```

**不做静默跳过**：秩不足的重采样不是"跳过并继续"，而是整个执行 fail-closed。
备选方案（记录计数 + 最小可估计重复数阈值）被否决，因为它需要一个人为阈值常量，属于
"设计留下了实现关键选择"。后果（诚实记录）：主样本满秩不保证每次重采样都满秩，因此
小样本上 `SINGULAR_RESAMPLE` 是**一等、可复现的结果**，而不是隐藏的降级。

### 7.6 置信端点语义（精确次序统计量）

```text
level = Decimal(bootstrap_plan.confidence_level)          # 规范十进制，0 < level < 1
alpha = (Decimal(1) - level) / Decimal(2)                 # 精确，必为有限十进制
B     = replications
样本  = sorted(primary_0..primary_(B-1))，升序（float64 比较；无 NaN，已 gate）
k_lo  = floor(B * alpha)                                   # Decimal -> ROUND_FLOOR，精确
k_hi  = ceil(B * (1 - alpha)) - 1                           # Decimal -> ROUND_CEILING，精确
k_lo  = max(0, min(B - 1, k_lo)) ; k_hi = max(0, min(B - 1, k_hi))
if k_lo > k_hi:  -> ExecutionError("INVALID_INTERVAL_ORDER")
lower = 样本[k_lo] ; upper = 样本[k_hi]
```

硬性语义：

- **不使用任何库的分位数默认值**（`numpy.quantile` / `percentile` 的 `method` 默认为实现细节，
  禁止依赖）；端点是**精确次序统计量**，无插值、无浮点权重。
- `alpha` 由精确十进制算出，并以规范十进制记入产物 `interval_alpha`。
- `level` 与 `B` 只来自计划；禁止在证据层"顺便"改用另一个置信水平。
- 端点必须满足 `lower <= upper`（float64 比较），否则 `INVALID_INTERVAL_ORDER`。

### 7.7 禁用路径

禁用路径**只**由计划声明触发：`plan.bootstrap_plan.enabled is False`
（A.1 已强制此时 `method_id == "DISABLED"`）。此时产物 `bootstrap.enabled is False`：

```text
产物 bootstrap 块 = {enabled: false, method_id: "DISABLED",
                     block_length: null, replications: null, seed: null, rng: null,
                     confidence_level: null, interval_alpha: null,
                     lower_index: null, upper_index: null,
                     primary_effect_lower: null, primary_effect_upper: null}
```

并强制：

- 该路径**不是**任何失败的后备出口：计划启用时的任何 bootstrap 失败都是整体 fail-closed
  （第 7.1 节第 2 条），不得落到这里；
- endpoint 为 `null`，**不得**用解析标准误、t 分布或任何近似替代；
- 证据处置固定为 `INCONCLUSIVE` / 原因 `BOOTSTRAP_DISABLED`（第 8 节优先级 D2）；
- 不得因为"CI 缺失"而省略 `PRIMARY_EFFECT_CI_LOWER/UPPER` 两个统计角色：它们以 `null` 存在，
  角色可解析性检查仍然通过（`null` 是显式的"未计算"，不是缺失字段）。

## 8. 证据处置表（完整冻结）

### 8.1 输入

```text
direction             = plan.evidence_plan.expected_direction ∈ {POSITIVE, NEGATIVE, TWO_SIDED}
requirement           = Decimal(plan.evidence_plan.confidence_requirement)      # 0 < r <= 1
level                 = Decimal(plan.bootstrap_plan.confidence_level)           # 0 < l < 1
lower, upper          = bootstrap 端点（float64）
primary               = estimator.primary_effect（float64）
quality_failure_word  = plan.evidence_plan.data_quality_failure_disposition ∈ {FAIL, INCONCLUSIVE}
coverage_complete     = (sample.coverage_numerator == sample.coverage_denominator)
bootstrap_enabled     = plan.bootstrap_plan.enabled     # 与产物 bootstrap.enabled 恒等（第 7.1 节）
```

### 8.2 处置词表（封闭五词）

```text
DISPOSITIONS = ("POSITIVE_SUPPORTED", "NEGATIVE_SUPPORTED", "TWO_SIDED_SUPPORTED",
                "NOT_SUPPORTED", "INCONCLUSIVE")
REASONS      = ("INTERVAL_ABOVE_ZERO", "INTERVAL_BELOW_ZERO", "INTERVAL_INCLUDES_ZERO",
                "BOOTSTRAP_DISABLED", "CONFIDENCE_BELOW_REQUIREMENT")
```

`direction` 不在三词之内即 `UNSUPPORTED_EVIDENCE_DIRECTION`（不猜测、不默认 TWO_SIDED）。

### 8.3 处置表（按冻结优先级求值，命中即停）

| 优先级 | 条件 | `disposition` | `disposition_reason` |
| --- | --- | --- | --- |
| D1 | 质量前提不成立（第 11.1 节 X4） | **不产出产物** | 拒绝错误携带 `quality_failure_word` |
| D2 | `plan.bootstrap_plan.enabled is False`（产物 `bootstrap.enabled` 同步为 `False`） | `INCONCLUSIVE` | `BOOTSTRAP_DISABLED` |
| D3 | `level < requirement`（精确十进制比较） | `INCONCLUSIVE` | `CONFIDENCE_BELOW_REQUIREMENT` |
| D4 | `direction == POSITIVE` 且 `lower > 0` | `POSITIVE_SUPPORTED` | `INTERVAL_ABOVE_ZERO` |
| D5 | `direction == POSITIVE` 且 `lower <= 0` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |
| D6 | `direction == NEGATIVE` 且 `upper < 0` | `NEGATIVE_SUPPORTED` | `INTERVAL_BELOW_ZERO` |
| D7 | `direction == NEGATIVE` 且 `upper >= 0` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |
| D8 | `direction == TWO_SIDED` 且 `lower > 0` | `TWO_SIDED_SUPPORTED` | `INTERVAL_ABOVE_ZERO` |
| D9 | `direction == TWO_SIDED` 且 `upper < 0` | `TWO_SIDED_SUPPORTED` | `INTERVAL_BELOW_ZERO` |
| D10 | `direction == TWO_SIDED` 且 `lower <= 0 <= upper` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |

端点硬语义（无容差）：

- `lower > 0` 是**严格**大于；`lower == 0.0` 或 `lower == -0.0` 视为落在零内；
- `upper < 0` 是**严格**小于；`upper == 0.0` 或 `upper == -0.0` 视为落在零内；
- 因此端点恰为 `0` 一律得到 `NOT_SUPPORTED`，绝不得到 `*_SUPPORTED`；
- 判定只用 float64 值，不用 `canonical_decimal` 渲染；`-0.0` 与 `0.0` 的判定相同，
  但 `float64_hex` 不同，因此**主产物身份不同**（第 6.2 节第二层：主产物的 float64 输出进入
  `artifact_digest`）。判定相同与身份相同是两件事，不得互相推导。该段只描述**主产物**：
  注册稳健性派遣产物不产出任何处置词，也不含端点等 float64 统计量（第 9.1、12.4 节）。

### 8.4 数据质量失败处置的精确落点

`plan.evidence_plan.data_quality_failure_disposition`（`FAIL` / `INCONCLUSIVE`）在**质量前提
不成立**时生效，且只以拒绝本身承载：

```text
ExecutionError("DATA_QUALITY_REJECTED") 的 .disposition 属性 == quality_failure_word（原样）
```

硬性语义：

- 该路径**不产出任何产物对象**：没有 0 行产物、没有部分产物、没有"带降级标记"的产物；
- 该词**不出现**在 `DISPOSITIONS` 里，因此不可能被误当成一项研究结论；
- 由于适配器在 `REJECTED_QUALITY` 时已让矩阵层以 `DATASET_NOT_READY` 拒绝，执行层能看到
  的拒绝态只有"矩阵质量事实与门槛不符"这一类，门本身是 defense-in-depth。

### 8.5 覆盖不完整不改变处置，但必须显式可见

`coverage_complete == False`（`RETAIN_IN_DENOMINATOR` 下保留缺口的合法矩阵）**不**改写处置：
适配器已经判定该样本通过冻结质量门，执行层不得擅自发明新的降级规则。但产物必须同时携带
`sample.{coverage_numerator, coverage_denominator, coverage_gate, coverage_gate_satisfied,
coverage_complete}` 与 `evidence.coverage_complete`，使任何读者都无法把部分覆盖误读为完整覆盖。

## 9. 授权状态与转换

### 9.1 三个状态的精确含义

| 状态 | 载体 | 精确含义 | 本设计下的取值 |
| --- | --- | --- | --- |
| `execution_authorized` | `MatrixPreparationV1`、`ExecutionArtifactV1`、`RobustnessArtifactV1` | **在真实（非合成）输入上执行研究**的授权 | 恒 `False` |
| `statistics_computed` | `MatrixPreparationV1`、`ExecutionArtifactV1`、`RobustnessArtifactV1` | 冻结估计器是否真的在本对象所绑定的来源链上运行过 | 矩阵恒 `False`；**只有主产物 `True`**；稳健性派遣产物恒 `False` |
| `outcome_read` | `DeterministicAnalysisPlan.evidence_plan`、两个产物 | 冻结证据规则是否已被应用到本对象的统计量上 | 计划恒 `False`；**只有主产物 `True`**；稳健性派遣产物恒 `False` |

稳健性派遣产物两个状态位都必须是 `False`，因为
`prepare_registered_robustness_dispatch` **不运行任何统计量**（第 12 节）：它只验证请求、
绑定注册项、完整转发参数并构造不可变派遣产物。若把它标成 `statistics_computed=True`，
就是把"派遣计划已绑定"谎报成"稳健性统计已计算"，并会让 `outcome_read=True` 的语义
（证据规则已应用到统计量）失去唯一的统计量来源。

`outcome_read=True` 的作用域被 `provenance.synthetic_test_only=True` 严格限定：
它表示"已对**本合成产物自身**的统计量应用冻结证据规则"，**不表示**读取了任何真实研究结果。

### 9.2 状态转换表

```text
S0 计划       DeterministicAnalysisPlan
S1 矩阵       MatrixPreparationV1
S2 主产物     ExecutionArtifactV1
S3 派遣产物   RobustnessArtifactV1（已绑定、未执行：statistics_computed=False）
S4 真实研究   不存在
S5 holdout    不存在
```

| 转换 | 允许 | 执行者 | 前置条件 |
| --- | --- | --- | --- |
| S0 -> S1 | 是（已合并且不在本设计范围） | 既有 `materialize_design_matrix` | 来源验证 + 质量门 |
| S1 -> S2 | 是（本设计） | `execute_bounded_analysis` | X1..X16 全部通过，`mode == "SYNTHETIC"` |
| S1 -> S3 | 是（本设计） | `prepare_registered_robustness_dispatch` | R0..R9 全部通过，`mode == "SYNTHETIC"` |
| S2 -> S0/S1 | **否** | — | 产物是终态：没有任何函数把产物写回计划或矩阵 |
| S2/S3 -> S2/S3 | **否** | — | 没有"再执行一次以挑选结果"的接口 |
| 任意 -> S4 | **否** | — | 没有函数、没有参数、没有标志位能授予真实研究授权 |
| 任意 -> S5 | **否** | — | 没有 holdout 参数；签名层 `TypeError`；计划层 `holdout_boundary.execution_authorized` 恒 `False` |

S1 -> S3 是"绑定"而不是"执行"：该转换不运行估计器、不运行 bootstrap、不计算任何稳健性统计量，
因此产物状态位为 `statistics_computed = False` / `outcome_read = False`（第 9.1、12 节）。

合成执行的授权不来自上述任一字段，而来自**来源链本身**：`bound_inputs.mode == "SYNTHETIC"`
（适配器已强制，执行层再断言一次，否则 `UNSUPPORTED_DATASET_MODE`）、合同由合成配置编译、
计划状态为 `DETERMINISTIC_PRE_EXECUTION_PLAN`。执行层把这一事实写成
`provenance.provenance_class = "SYNTHETIC_TEST_ONLY"` 与 `provenance.dataset_mode`，
从而让"合成"成为身份的显式组成部分，而不是隐含假设。

### 9.3 holdout 门（fail-closed）

```text
plan.holdout_boundary.execution_authorized is not False        -> HOLDOUT_NOT_AUTHORIZED
若 plan.holdout_boundary 含 "window"：
    任一 matrix.rows[*].trade_date 落在 [window.start, window.end] 内 -> HOLDOUT_NOT_AUTHORIZED
bound_inputs.mode != "SYNTHETIC"                                -> UNSUPPORTED_DATASET_MODE
```

诚实边界：由于 A.1 已强制 `DEVELOPMENT_HOLDOUT_OVERLAP` 与
`validate_analysis_plan` 的 `HOLDOUT_EXECUTION_NOT_AUTHORIZED`，**合法构造的输入永远不会命中
这两个门**。它们存在的意义是：一旦上游合同/适配器放宽，执行层必须显式拒绝，而不是静默把
holdout 行喂进估计器。因此验收对这两个门只做**结构与顺序**断言（存在、位于来源验证之后），
不构造端到端命中；当前可构造的 holdout 拒绝是签名层的 `TypeError` 与计划层的
`HOLDOUT_EXECUTION_NOT_AUTHORIZED`/`CONTRACT_PLAN_MISMATCH`。

## 10. 不可变产物 schema、序列化与摘要

### 10.1 嵌套类型（全部拟议）

```text
@dataclass(frozen=True)
class Float64ValueV1:
    float64_hex: str          # float.hex(value)，精确
    canonical_decimal: str    # canonical_decimal(repr(value))，规范十进制渲染

@dataclass(frozen=True)
class SourceChainV1:
    contract_digest: str      # 继承 matrix.source_contract_digest
    plan_digest: str          # 继承 matrix.plan_digest
    input_digest: str         # 继承 matrix.input_digest
    domain_digest: str        # 继承 matrix.domain_digest
    dataset_digest: str       # 继承 matrix.dataset_digest
    matrix_digest: str        # 继承 matrix.matrix_digest

@dataclass(frozen=True)
class ProvenanceV1:
    provenance_class: str     # 固定 "SYNTHETIC_TEST_ONLY"
    synthetic_test_only: bool # 严格 True
    dataset_mode: str         # 复制 bound_inputs.mode，必须 "SYNTHETIC"
    real_data_used: bool      # 严格 False
    holdout_accessed: bool    # 严格 False

@dataclass(frozen=True)
class TermRefV1:
    position: int
    term_role: str
    coefficient_role: str

@dataclass(frozen=True)
class MethodConfigurationV1:
    artifact_schema_version: str
    executor_version: str             # EXECUTOR_VERSION
    estimator_contract_id: str         # ESTIMATOR_CONTRACT_ID
    model_family: str                  # "OLS"
    numeric_backend: str               # "numpy.linalg.lstsq"
    numeric_runtime: str               # numpy.__version__
    response_role: str
    terms: tuple[TermRefV1, ...]
    primary_effect_position: int
    primary_effect_role: str
    bootstrap_enabled: bool            # 计划声明（与产物 bootstrap.enabled 恒等，第 7.1 节）
    bootstrap_method_id: str           # 计划声明
    block_length_policy_id: str        # 计划声明
    bootstrap_replications: int        # 计划声明
    bootstrap_seed: int                # 计划声明
    bootstrap_rng: str                 # 计划声明
    bootstrap_confidence_level: str    # 计划声明（规范十进制）
    evidence_rule_id: str
    evidence_direction: str
    evidence_confidence_requirement: str
    data_quality_failure_disposition: str
    block_length: int | None           # 实际使用的块长

@dataclass(frozen=True)
class SampleBlockV1:
    row_count: int
    trade_dates: tuple[str, ...]
    coverage_numerator: int
    coverage_denominator: int
    coverage_gate: str
    coverage_gate_satisfied: bool
    coverage_complete: bool
    missingness_policy: str
    failure_disposition: str
    reason_counts: tuple[tuple[str, int], ...]
    rejected_dates: tuple[str, ...]

@dataclass(frozen=True)
class CoefficientV1:
    position: int
    term_role: str
    coefficient_role: str
    value: Float64ValueV1

@dataclass(frozen=True)
class EstimatorBlockV1:
    n_rows: int
    n_terms: int
    rank: int
    coefficients: tuple[CoefficientV1, ...]        # 顺序 == ordered_terms 顺序
    singular_values: tuple[Float64ValueV1, ...]
    residual_sum_of_squares: Float64ValueV1 | None # n == k 时为 None
    primary_effect: Float64ValueV1

@dataclass(frozen=True)
class BootstrapBlockV1:
    enabled: bool                    # 严格复制 plan.bootstrap_plan.enabled（第 7.1 节）
    method_id: str
    block_length: int | None         # enabled=True 时非 None；enabled=False 时必须为 None
    replications: int | None
    seed: int | None
    rng: str | None
    confidence_level: str | None
    interval_alpha: str | None
    lower_index: int | None
    upper_index: int | None
    primary_effect_lower: Float64ValueV1 | None
    primary_effect_upper: Float64ValueV1 | None

@dataclass(frozen=True)
class StatisticValueV1:
    role: str                    # 必须来自计划的 required_statistic_roles
    kind: str                    # "COUNT" | "MEAN" | "MEDIAN" | "DIFFERENCE"
    count: int | None            # kind == "COUNT" 时为严格 int，否则 None
    value: Float64ValueV1 | None # kind != "COUNT" 时为数值；样本为空时 None

@dataclass(frozen=True)
class EvidenceBlockV1:
    rule_id: str
    expected_direction: str
    confidence_requirement: str
    data_quality_failure_disposition: str   # 原样记录，不在此处生效
    bootstrap_confidence_level: str | None
    confidence_requirement_satisfied: bool
    primary_effect_role: str
    primary_effect: Float64ValueV1
    interval_lower: Float64ValueV1 | None
    interval_upper: Float64ValueV1 | None
    disposition: str
    disposition_reason: str
    coverage_complete: bool
    interpretation_boundary: str            # 冻结字面量（第 10.5 节）

@dataclass(frozen=True)
class ExecutionArtifactV1:
    artifact_schema_version: str            # ARTIFACT_SCHEMA_VERSION
    executor_version: str                   # EXECUTOR_VERSION
    source_chain: SourceChainV1
    provenance: ProvenanceV1
    method_configuration: MethodConfigurationV1
    sample: SampleBlockV1
    estimator: EstimatorBlockV1
    bootstrap: BootstrapBlockV1
    conditional_descriptives: tuple[StatisticValueV1, ...]
    evidence: EvidenceBlockV1
    execution_authorized: bool              # 严格 False
    statistics_computed: bool               # 严格 True
    outcome_read: bool                      # 严格 True
    artifact_digest: str
```

### 10.2 稳健性派遣产物（独立 schema，结构性禁止"最佳结果"）

```text
@dataclass(frozen=True)
class RobustnessEntryDispatchV1:
    robustness_id: str
    request_ordinal: int                         # 0 起，等于调用方请求顺序
    registration_ordinal: int                    # 0 起，等于 plan.robustness_plan.entries 中的位置
    method_id: str                               # 计划注册项的 method_id，逐字复制
    parameters: FrozenJSONObject                 # 计划注册项的 parameters，完整、不可变、逐字复制
    parameters_canonical_json: str               # 规范化 JSON 文本（紧凑、键序=冻结顺序，可逐字节复核）

@dataclass(frozen=True)
class RobustnessDispatchV1:
    requested_ids: tuple[str, ...]      # == 调用方请求顺序
    registered_ids: tuple[str, ...]     # 计划注册表顺序（完整注册表，用于证明"未自动扩展"）
    automatic_expansion: bool           # 严格 False
    automatic_selection: bool           # 严格 False
    parameters_interpreted: bool        # 严格 False（本阶段不解释任何参数语义）

@dataclass(frozen=True)
class RobustnessArtifactV1:
    artifact_schema_version: str        # ROBUSTNESS_ARTIFACT_SCHEMA_VERSION
    executor_version: str
    source_chain: SourceChainV1
    provenance: ProvenanceV1
    method_configuration: MethodConfigurationV1
    sample: SampleBlockV1
    dispatch: RobustnessDispatchV1
    entries: tuple[RobustnessEntryDispatchV1, ...]   # 顺序 == requested_ids 顺序
    execution_authorized: bool          # 严格 False
    statistics_computed: bool           # 严格 False（本阶段不计算任何稳健性统计量）
    outcome_read: bool                  # 严格 False
    artifact_digest: str
```

`parameters` 的类型是既有 `FrozenJSONObject`（`hypothesis_config` 的冻结 JSON 值域）：
它保留**完整**注册参数，包括未知的嵌套键、混合类型的数组与嵌套对象。产物必须是纯数据
（`FrozenJSONObject` / `FrozenJSONList` / `FrozenJSONNumber` / 字符串 / 布尔 / `None`），
且**构造产物时不允许任何拷贝丢失**。

**摘要取数路径（R2 修正，必须照此实现）**：既有 `canonical_digest(payload)` 就是对 `payload`
调用 `json.dumps(..., sort_keys=True, separators=(",", ":"))`，而 `FrozenJSONObject` /
`FrozenJSONList` / `FrozenJSONNumber` 是 frozen dataclass，**不是** JSON 可序列化对象。
因此 **`FrozenJSONObject` 不能被 `canonical_digest` 直接序列化**：把冻结形态原样放进摘要
载荷会抛 `TypeError`，而不是得到摘要。冻结形态必须先投影为**纯 JSON 形态**（对象->dict、
数组->list、`FrozenJSONNumber` -> 其规范十进制字符串），再进入摘要载荷。两种等价实现：

```text
① 纯 JSON 投影 = 既有 planning/compiler 的 _thaw 语义（FrozenJSONObject -> dict、
   FrozenJSONList -> list、FrozenJSONNumber -> value.value），执行层必须实现同一语义；
② 或 纯 JSON 投影 = json.loads(entries[i].parameters_canonical_json)
```

两条路径必须给出同一纯 JSON 值，因此也给出同一摘要。冻结形态仅用于"逐字、不可变"的保存
与自洽检查（第 10.4 节末）；`artifact_digest` 计算的是它的纯 JSON 投影，而不是冻结 dataclass
的 `repr`。**本会话只读实测**（2026-09-11，未写入任何文件）：

```text
canonical_digest({"parameters": FrozenJSONObject(...)})                       -> TypeError:
        Object of type FrozenJSONObject is not JSON serializable
canonical_digest({"parameters": <纯 JSON 投影>})                              -> b8a23abe4fdc6d6ed2e1d6045a49cfd89eae2b0c4b5ab3658f2b1bbe0f3a8375
同一投影下把嵌套 window 元素 "3" 改成 "999"                                     -> 0b4f38cf2ce8436689c4e672be7768060ef8e7e00c3336eee4ab19a5161d4764
同一投影重复计算                                                              -> 摘要相同（确定性）
纯 JSON 投影 == json.loads('{"trim":"0.0100","window":["1","2","3"]}')         -> True
```

结构性约束（写入 schema，而不是靠约定）：

1. 稳健性产物**没有** `evidence` 块，因此稳健性派遣不能产出任何处置词；
2. 稳健性产物**没有** `best` / `selected` / `winner` / `aggregate` / `ranking` 字段，
   且序列化器拒绝这些键名（第 10.4 节）；
3. 稳健性产物**没有**任何统计量字段（没有 `statistics`、没有 `count`、没有 `value`、
   没有 `trim` 这样的"已解释参数"字段），因此"派遣被读成稳健性结论"在结构上不可表达；
4. 稳健性产物不参与主产物的任何字段：主产物执行时不知道稳健性请求的存在，
   `execute_bounded_analysis` 的签名里没有 `robustness_ids`；
5. `parameters` 与 `parameters_canonical_json` 必须互相自洽
   （重新序列化 `parameters` 必须逐字节等于 `parameters_canonical_json`），
   任一不成立即 `INVALID_INPUT_STRUCTURE`。

### 10.3 规范序列化

```text
execution_artifact_to_canonical_dict(artifact) -> 独立 dict（不含 artifact_digest 自身）
serialize_execution_artifact(artifact) =
    (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
```

与既有 `serialize_dataset` / `serialize_analysis_plan` / `serialize_matrix` 同形：无 BOM、无缩进、
UTF-8、结尾恰好一个 `\n`。序列化前必须完成全部不变量校验与第 10.4 节的内容检查。

### 10.4 摘要身份与内容禁止项

```text
artifact_digest = canonical_digest(payload − artifact_digest)
```

**主产物（`ExecutionArtifactV1`）的摘要覆盖**：`artifact_schema_version`、`executor_version`、
完整 `source_chain`（六个上游摘要）、`provenance`、完整 `method_configuration`（含方法配置、
计划声明的 bootstrap 参数、块长策略、代码与 schema 版本、`numeric_runtime`）、`sample`、
`estimator`（含全部系数与奇异值）、`bootstrap`、`conditional_descriptives`、`evidence`
（含冻结解释边界），以及三个布尔状态位。

**注册稳健性派遣产物（`RobustnessArtifactV1`）的摘要覆盖**：`artifact_schema_version`、
`executor_version`、完整 `source_chain`（六个上游摘要）、`provenance`、完整
`method_configuration`（含 `numeric_runtime` 与代码/schema 版本）、`sample`、
`dispatch`（`requested_ids` = 请求顺序、`registered_ids` = 完整注册顺序、
`automatic_expansion` / `automatic_selection` / `parameters_interpreted` 三个恒 `False` 的位）、
`entries[*]`（`robustness_id`、`request_ordinal`、`registration_ordinal`、`method_id`、
**完整 canonical `parameters`**、`parameters_canonical_json`），以及三个布尔状态位。
该产物**不计算任何统计量**（`statistics_computed = False`），其 schema 里**没有** `estimator`、
`bootstrap`、`conditional_descriptives`、`evidence` 块——因此它的 `artifact_digest`
**不存在**、也**不得声称**绑定任何 float64 统计输出（第 6.2 节第二层 (b)）。

**float64 输出如何进入身份（承接第 6.2 节两层身份，只适用于主产物）**：主产物的
`estimator`、`bootstrap`、`conditional_descriptives`、`evidence` 里的每一个数值都以
`Float64ValueV1` 落盘，因此 `float64_hex` 与 `canonical_decimal` **两个字符串都进入
`artifact_digest`**。这不是第 6.2 节第一层的上游身份：上游六个摘要仍然只绑定规范十进制，
主产物的摘要必须绑定 float64 统计输出，否则"改一个系数、重写渲染、保留摘要"能通过校验。
配套的结果是：

- `estimator.primary_effect`、系数、奇异值、bootstrap 端点、区间序号、条件描述统计与
  `evidence.interval_lower/upper` 的任何 float64 变化都必须改变 `artifact_digest`；
- `-0.0` 与 `0.0` 的**处置判定相同**（第 8.3 节），但 `float64_hex` 不同，
  因此**主产物身份不同**——两者不是同一产物，不得互相替代；
- 摘要只覆盖规范化渲染（`float.hex` 文本），不覆盖原始内存字节或 numpy dtype 元数据，
  因此同一 `numeric_runtime` 下逐字节可复现，跨运行时差异由 `numeric_runtime` 显式暴露。

**稳健性派遣产物如何绑定注册参数（它绑定的就是这些，而不是统计量）**：
`entries[*].parameters` 是完整、不可变的 `FrozenJSONObject`，进入摘要的是它在第 10.2 节
"摘要取数路径"下的**纯 JSON 投影**（对象/数组/规范十进制字符串），`canonical_digest` 再以
固定 `sort_keys=True` 递归序列化该投影，因此**未知嵌套键也进入 `artifact_digest`**。
后果：

- 改动注册参数的任何一个值、键或嵌套层级都必须改变 `artifact_digest`；
- 因此"派遣时静默改写/丢弃一个执行器没有实现的参数"不可能不被发现；
- `source_chain.plan_digest` 已经绑定计划里的 `robustness_plan.entries`，
  与产物内逐字转发的 `parameters` 互为交叉校验：两者不一致即 `INVALID_INPUT_STRUCTURE`。

序列化与构造时必须执行两项内容检查（任一命中即 `FORBIDDEN_ARTIFACT_CONTENT`）：

```text
FORBIDDEN_KEYS = {"cwd","worktree","hostname","username","user","home","abspath",
                  "absolute_path","root_path","env","environment","path","session",
                  "best","best_result","best_id","selected","selected_id","winner",
                  "aggregate","ranking","optimize","tuned","search"}
ABSOLUTE_PATH = Windows 盘符路径或 POSIX 绝对路径（正则），出现在任何字符串值中即拒绝
```

即：产物**不能**包含主机/工作目录/绝对路径身份，也**不能**包含任何"挑选/聚合/最优"字段。

### 10.5 冻结的解释边界字面量

每个产物（主产物与稳健性产物）都必须携带同一段逐字相同的字符串：

```text
"SYNTHETIC_TEST_ONLY: output of the frozen bounded executor on validated synthetic inputs. "
"Not a research finding; not evidence of estimability, significance, economic validity or "
"tradability; not an A-share mechanism result; not an authorization to execute on real data, "
"on holdout data, or to enter M4-B."
```

不一致即 `INVALID_INPUT_STRUCTURE`。这是把"设计完成不等于研究结论"从散文变成机器可查字段。

## 11. 验证顺序与稳定错误码

### 11.1 主执行入口的冻结顺序

```text
X1  结构与类型                frozen dataclass / tuple / 严格 bool/int 陷阱        INVALID_INPUT_STRUCTURE
X2  validate_design_matrix    既有五参数入口；上游 AdapterError / MatrixError 原样抛出
X3  方法允许列表              plan.analysis_method_id / model_family             UNSUPPORTED_ANALYSIS_METHOD / UNSUPPORTED_MODEL_FAMILY
X4  质量前提                  status == READY_SYNTHETIC、rows 非空、覆盖门精确成立 DATA_QUALITY_REJECTED（携带 .disposition）
X5  数据模式与 holdout 边界     mode == SYNTHETIC；holdout 不授权；行日期不入窗   UNSUPPORTED_DATASET_MODE / HOLDOUT_NOT_AUTHORIZED
X6  术语与对齐                ordered_terms <-> columns；唯一 INTERCEPT/INDICATOR；
                              response_role；行对齐与指示列交叉校验               PLAN_TERM_ROLE_MISMATCH / MATRIX_PREPARATION_ALIGNMENT_MISMATCH
X7  单元格转换与范围           Decimal -> 范围门 -> float64 -> 有限性              CELL_OUT_OF_RANGE / NON_FINITE_CELL
X8  设计秩门                  matrix_rank(X) == k，lstsq 二次秩 == k              SINGULAR_DESIGN
X9  主估计                    numpy.linalg.lstsq；残差形状                        ESTIMATOR_FAILURE
X10 数值输出校验              全部输出有限                                       NON_FINITE_ESTIMATE
X11 bootstrap 前提            方法/RNG/重复数/块长                                UNSUPPORTED_BOOTSTRAP_METHOD / UNSUPPORTED_BOOTSTRAP_RNG /
                                                                                 INSUFFICIENT_REPLICATIONS / BLOCK_LENGTH_EXCEEDS_ROWS
X12 bootstrap 执行            逐次重采样 + 重拟合 + 重采样秩门                    SINGULAR_RESAMPLE / NON_FINITE_ESTIMATE / BOOTSTRAP_FAILURE
X13 区间校验                  k_lo/k_hi 与 lower <= upper                         INVALID_INTERVAL_ORDER
X14 条件描述统计              指示值严格 0/1；角色集合与顺序；均值/中位数规则      INVALID_CONDITION_INDICATOR / MISSING_REQUIRED_STATISTIC_ROLE
X15 证据处置                  方向白名单 + 第 8.3 节表                            UNSUPPORTED_EVIDENCE_DIRECTION
X16 产物构造与序列化          不变量、自摘要、内容禁止项                          ARTIFACT_DIGEST_MISMATCH / FORBIDDEN_ARTIFACT_CONTENT
```

### 11.2 稳健性派遣入口的冻结顺序

```text
R0..R6 = X1..X7 完全同序（同一来源验证、同一方法允许列表、同一质量门、同一 holdout 门、
          同一术语/对齐检查、同一单元格转换与范围门）
R7  派遣校验                   ids 非空、无重复、全部注册                         EMPTY_ROBUSTNESS_DISPATCH / DUPLICATE_ROBUSTNESS_ID /
                                                                                 UNREGISTERED_ROBUSTNESS_ID
R8  注册项绑定                method_id 合法标识符；parameters 是 JSON 对象；       UNSUPPORTED_ROBUSTNESS_METHOD
                              完整转发（不解释语义、不检查键集合）
R9  派遣产物构造              按请求顺序；完整转发参数；自摘要与内容禁止项；        ARTIFACT_DIGEST_MISMATCH / FORBIDDEN_ARTIFACT_CONTENT
                              statistics_computed = False
```

`R0..R6` 必须在 `R7` 之前：**来源未验证就不允许讨论派遣**。请求未注册的 ID 时，
错误必须是 `UNREGISTERED_ROBUSTNESS_ID`，而不是更早的结构或来源错误（除非来源本身失败）。

R8 **不做**参数键集合匹配、也**不做**参数取值校验：本阶段没有既有 handler contract 可供对照，
发明 `trim` 或 `window` 的合法性规则就是发明统计语义（第 12.2 节）。R8 只拒绝"根本不是
注册项"的输入（空/非法 `method_id`、非对象的 `parameters`）。

### 11.3 `validate_execution_artifact` 的冻结顺序

```text
V1 产物结构 + 全部不变量 + 自摘要        INVALID_INPUT_STRUCTURE / ARTIFACT_DIGEST_MISMATCH
V2 validate_design_matrix(...)          上游 AdapterError / MatrixError 原样抛出
V3 重新执行（同一矩阵、同一计划、同一种子）
V4 逐字节比较 serialize_execution_artifact  IDENTITY_CONFLICT
```

`validate_robustness_artifact` 同序，但 V3 用 `prepare_registered_robustness_dispatch`
（**重新派遣，不重新计算统计量**）并以产物内的 `dispatch.requested_ids` 作为请求顺序。

### 11.4 错误类型与错误码表（全部拟议）

```text
class ExecutionError(ValueError):
    code: str
    message: str | None
    disposition: str | None     # 仅 DATA_QUALITY_REJECTED 时为计划声明的质量失败处置词
```

| 错误族 | 错误码 | 触发条件 | 是否可降级 |
| --- | --- | --- | --- |
| `ExecutionError` | `INVALID_INPUT_STRUCTURE` | 对象类型/shape/布尔陷阱/字段缺失/解释边界字面量不符 | 否 |
| `ExecutionError` | `UNSUPPORTED_ANALYSIS_METHOD` | `analysis_method_id` 不在允许列表 | 否 |
| `ExecutionError` | `UNSUPPORTED_MODEL_FAMILY` | `design_plan.model_family != "OLS"` | 否 |
| `ExecutionError` | `DATA_QUALITY_REJECTED` | 质量前提不成立（携带 `.disposition`） | 否 |
| `ExecutionError` | `UNSUPPORTED_DATASET_MODE` | `bound_inputs.mode != "SYNTHETIC"` | 否 |
| `ExecutionError` | `HOLDOUT_NOT_AUTHORIZED` | holdout 授权位非 False，或行日期落入 holdout 窗口 | 否 |
| `ExecutionError` | `PLAN_TERM_ROLE_MISMATCH` | 列/术语/响应角色与计划不一致，或缺唯一 INTERCEPT/INDICATOR | 否 |
| `ExecutionError` | `MATRIX_PREPARATION_ALIGNMENT_MISMATCH` | 矩阵行与 `complete_rows` 不对齐，或指示列交叉校验失败 | 否 |
| `ExecutionError` | `CELL_OUT_OF_RANGE` | 规范十进制单元格绝对值超过 `MAX_ABS_CELL_DECIMAL` | 否 |
| `ExecutionError` | `NON_FINITE_CELL` | 单元格十进制非有限，或转 float64 后非有限 | 否 |
| `ExecutionError` | `SINGULAR_DESIGN` | 主设计秩 < 列数（含 `lstsq` 二次秩不一致） | 否 |
| `ExecutionError` | `ESTIMATOR_FAILURE` | 残差形状非 0/1 等估计器契约违规 | 否 |
| `ExecutionError` | `NON_FINITE_ESTIMATE` | 任一数值输出非有限 | 否 |
| `ExecutionError` | `UNSUPPORTED_BOOTSTRAP_METHOD` | 启用的 bootstrap 方法不在允许列表 | 否 |
| `ExecutionError` | `UNSUPPORTED_BOOTSTRAP_RNG` | `rng != "PCG64"` | 否 |
| `ExecutionError` | `INSUFFICIENT_REPLICATIONS` | `replications < 2` | 否 |
| `ExecutionError` | `BLOCK_LENGTH_EXCEEDS_ROWS` | `L(n) > n` | 否 |
| `ExecutionError` | `SINGULAR_RESAMPLE` | 某次重采样秩不足（**不跳过**） | 否 |
| `ExecutionError` | `BOOTSTRAP_FAILURE` | 抽样/重拟合结构失败 | 否 |
| `ExecutionError` | `INVALID_INTERVAL_ORDER` | `k_lo > k_hi` 或 `lower > upper` | 否 |
| `ExecutionError` | `INVALID_CONDITION_INDICATOR` | 指示列取值不是严格 `"0"`/`"1"`，或分组计数和不等于 n | 否 |
| `ExecutionError` | `MISSING_REQUIRED_STATISTIC_ROLE` | 计划要求的统计角色缺失或顺序不符 | 否 |
| `ExecutionError` | `UNSUPPORTED_EVIDENCE_DIRECTION` | 方向不在 `{POSITIVE, NEGATIVE, TWO_SIDED}` | 否 |
| `ExecutionError` | `EMPTY_ROBUSTNESS_DISPATCH` | `robustness_ids` 为空 | 否 |
| `ExecutionError` | `DUPLICATE_ROBUSTNESS_ID` | 请求中出现重复 ID | 否 |
| `ExecutionError` | `UNREGISTERED_ROBUSTNESS_ID` | 请求的 ID 不在 `plan.robustness_plan.entries` | 否 |
| `ExecutionError` | `UNSUPPORTED_ROBUSTNESS_METHOD` | 注册项的 `method_id` 不是合法标识符，或其 `parameters` 不是 JSON 对象 | 否 |
| `ExecutionError` | `ARTIFACT_DIGEST_MISMATCH` | 自摘要与自身载荷不符 | 否 |
| `ExecutionError` | `IDENTITY_CONFLICT` | `validate_*_artifact` 中字节与重执行结果不符 | 否 |
| `ExecutionError` | `FORBIDDEN_ARTIFACT_CONTENT` | 载荷命中禁止键名或绝对路径模式 | 否 |
| `AdapterError`（上游） | 全部既有码 | X2 步 `validate_dataset` 失败 | 否 |
| `MatrixError`（上游） | 全部既有码 | X2 步 `validate_design_matrix` 失败 | 否 |

硬性语义：**失败不产生部分产物**。任何错误都必须抛出，不得返回带空 `coefficients`、
`null` 端点（除禁用路径的显式 `null`）或截断 `entries` 的"部分成功"对象。确定性要求：
同一输入必须命中同一首个错误。

## 12. 注册稳健性派遣契约（真正 registered dispatch-only）

本阶段稳健性入口的职责被收窄为三件事：**验证请求**、**按注册表绑定**、**完整不可变转发**。
它**不计算任何稳健性统计量**，也**不解释任何参数语义**；入口名因此是
`prepare_registered_robustness_dispatch`（第 4.1 节），产物状态
`statistics_computed = False`、`outcome_read = False`（第 9.1 节）。

### 12.1 请求验证与注册表绑定

```text
entries = plan.robustness_plan.entries                    # 计划注册表，顺序冻结
plan.robustness_plan.dispatch_only is True                # 否则 INVALID_INPUT_STRUCTURE（计划校验已保证）
plan.robustness_plan.automatic_expansion is False          # 否则 INVALID_INPUT_STRUCTURE
plan.robustness_plan.automatic_selection is False          # 否则 INVALID_INPUT_STRUCTURE
```

- `robustness_ids` 必须是非空、无重复、**全部已注册**的字符串元组；请求的每个 ID 必须在
  `entries` 中出现**恰好一次**（ID 唯一性由既有 `hypothesis_config` 的
  `DUPLICATE_ROBUSTNESS_ID` 保证）；
- 产物的 `entries` 顺序 == 请求顺序；每个条目的 `request_ordinal` 记录请求位置，
  `registration_ordinal` 记录它在计划注册表中的位置；
- 产物 `dispatch.registered_ids` 记录**完整**注册表顺序（含未被请求的项），
  使"没有自动扩展"成为可复核事实，而不是承诺；
- **没有** "run all registered" 开关、没有自动扩展、没有按方法族自动补齐、
  没有自动执行、没有"取最强结果"。

### 12.2 方法标识与参数的绑定规则（不发明统计语义）

本阶段**只**派遣注册表中**已经存在**的条目。执行层不持有、也不得引入任何
"稳健性方法允许列表"或"参数 schema"，因为它没有既有 handler contract 可以对照：

```text
对每个请求的 ID：
    条目 = entries 中 robustness_id 等于该 ID 的唯一项
    条目.method_id 必须是已注册的标识符（既有 _identifier 语义：非空、规范、字符串）
        -> 否则 UNSUPPORTED_ROBUSTNESS_METHOD
    条目.parameters 必须是既有 _canonical_json_value 语义下的 JSON 对象
        （FrozenJSONObject）
        -> 否则 UNSUPPORTED_ROBUSTNESS_METHOD
    产物条目 = 完整转发 {method_id, parameters} —— 逐字、不可变、不解释
```

冻结的四条硬性语义：

1. **完整转发**：`parameters` 的**全部**键、值、嵌套对象与数组（包括本设计未提及的未知键，
   例如既有 fixture 的 `window`）都必须进入产物，且通过 `parameters_canonical_json`
   逐字节可复核；
2. **不得忽略**：不存在"未实现的键就丢掉"的路径——丢弃一个键会改变
   `artifact_digest`，从而不可能不被发现；
3. **不得改写或补默认值**：执行层不得重排、重命名、规范化、拆分、合并或补全任何参数值；
   产物中的参数必须与计划注册项**逐字相同**（唯一允许的差异是键序，且既有
   `_canonical_json_value` 已把键序固定为排序序，执行层不得再排一次）；
4. **不得自动执行/扩展/选择**：不存在对注册项的解释、求值、调用或结果字段。

关于 `trim`、`window` 等既有参数名：本阶段**不为它们发明统计语义**。项目当前没有稳健性
handler contract（`mechanism/robustness.py` 绑定 M3 固定列名、固定开发期与固定阈值，
是明确不得触碰的模块，第 14.3 节），因此为 `trim` 定义裁剪规则、为 `window` 定义窗口规则
都属于"设计凭空发明统计语义"。这些参数在本阶段只是**被完整转发的注册数据**；
它们的统计含义必须在另立的实现 Goal 里与真实 handler contract 一并冻结。

**与既有 fixture 的关系（诚实记录）**：既有 A.1 fixture 的注册项是

```json
{"method_id":"CONDITIONAL_DESCRIPTIVES_V1",
 "parameters":{"trim":"0.0100","window":[1,2,3]},
 "robustness_id":"SYNTH_ROBUSTNESS_1"}
```

在计划里它被 `_canonical_json_value` 规范化（键排序；数字变为规范十进制字符串）后冻结为：

```text
method_id = "CONDITIONAL_DESCRIPTIVES_V1"
parameters = FrozenJSONObject(items=(("trim", "0.0100"), ("window", FrozenJSONList(("1","2","3")))))
```

本设计下 `prepare_registered_robustness_dispatch(..., ("SYNTH_ROBUSTNESS_1",))` 必须在
**未修改的 fixture** 上**成功**，产物包含
`parameters_canonical_json == '{"trim":"0.0100","window":["1","2","3"]}'`
（紧凑 JSON、无空格、键序=冻结顺序），且 `statistics_computed is False`。
为了让每一个嵌套层级都能被身份绑定，AC-16 的变异集**必须**包含嵌套参数变异
（`window` 数组元素 `"3" -> "999"`），并断言 `artifact_digest` 随之改变。

### 12.3 未注册请求与非法注册项的失败语义

```text
robustness_ids 为空                          -> EMPTY_ROBUSTNESS_DISPATCH
robustness_ids 含重复 ID                     -> DUPLICATE_ROBUSTNESS_ID
robustness_ids 含未注册 ID                   -> UNREGISTERED_ROBUSTNESS_ID
条目 method_id 不是合法标识符                -> UNSUPPORTED_ROBUSTNESS_METHOD
条目 parameters 不是 JSON 对象               -> UNSUPPORTED_ROBUSTNESS_METHOD
```

不存在"部分成功"：任一非法请求使**整次调用** fail-closed，不返回截断的 `entries`。

`plan.robustness_plan.entries` 可以为空（既有 A.2I 允许 `robustness_registry = []`）：
此时任何非空请求都必然得到 `UNREGISTERED_ROBUSTNESS_ID`，而空请求得到
`EMPTY_ROBUSTNESS_DISPATCH`。这两条路径都不产生派生产物。

**可达性（诚实标注）**：既有 A.1/A.2I 已经强制 `method_id` 是合法标识符
（`hypothesis_config._identifier`）且 `parameters` 是规范 JSON 对象
（`_canonical_json_value` + `NON_CANONICALIZABLE_VALUE`），因此
`UNSUPPORTED_ROBUSTNESS_METHOD` 对**合法构造的计划**不可达，属与第 9.3 节 holdout 门同类的
defense-in-depth：一旦上游放宽，执行层必须显式拒绝这种条目，而不是把它当成"已注册派遣"
转发出去。验收对该门只做结构与顺序断言，不构造端到端命中。

### 12.4 派遣不得被"选用"，也不得被读成统计结论

- 派遣产物没有 `evidence` 块，因此不可能产生处置词；
- 派遣产物没有任何统计量字段（没有 `statistics`、`count`、`value` 或"已解释参数"字段），
  且 `statistics_computed` / `outcome_read` 严格为 `False`；
- 派遣产物没有排序、评分、聚合或"最佳"字段，序列化器还会拒绝这些键名；
- 主执行入口的签名里没有稳健性参数，主产物的摘要里没有稳健性请求；
- 因此"用稳健性结果挑选主结论"在本设计里没有可表达的路径，而不是靠文档约束。
- 派遣产物的状态语义是"S3 已绑定的派遣计划"，**不是**"稳健性统计已运行"；
  把它读成后者即违反第 9.1 节的状态定义。

## 13. 条件描述统计（主产物的一部分）

### 13.1 冻结计算规则

```text
分组标签       = plan.conditional_summary_plan.condition_labels == ["CONDITION", "ORDINARY"]
条件来源角色   = plan.conditional_summary_plan.source_roles.condition == "CONDITION_INDICATOR"
结果来源角色   = plan.conditional_summary_plan.source_roles.outcome  == matrix.response_role
                 （不相等即 PLAN_TERM_ROLE_MISMATCH）
CONDITION_COUNT = 指示列 == "1" 的行数（严格 int）
ORDINARY_COUNT  = 指示列 == "0" 的行数（严格 int）
二者之和必须等于 n，否则 INVALID_CONDITION_INDICATOR
MEAN            = 按行序的 float64 左结合累加后再除以计数（total = 0.0; for v: total += v; total / k）
                  —— 明确禁止 numpy.mean 的成对求和：其结果可能随 SIMD 宽度/数组布局变化
MEDIAN          = 升序排序后：奇数取正中；偶数取两个中心值的 (a + b) / 2.0
DIFFERENCE      = 条件值 - 普通值（float64 减法）；任一侧为 null 则结果为 null
空组            = 对应 MEAN/MEDIAN/DIFFERENCE 记 null（不是 0，不是缺失字段）
```

### 13.2 角色完备性

`conditional_descriptives` 的角色集合与顺序必须精确等于
`plan.conditional_summary_plan.required_statistic_roles`；同时第 5.4 节的六项证据统计角色
必须可解析。任一不满足即 `MISSING_REQUIRED_STATISTIC_ROLE`。

## 14. 实现落点、复用与不得触碰

### 14.1 拟议落点

拟议新增纯模块（例如 `src/ashare_research/mechanism/execution/bounded.py`，包 `execution`），
其唯一职责是把已验证矩阵映射为估计器输入、执行冻结估计与 bootstrap、计算条件描述统计与
证据处置、构造不可变产物。落点属实现评审项；无论落在何处，都**不得**为落点修改既有
`__init__` 的既有导出语义。

### 14.2 复用（只调用，不修改）

- `mechanism.planning.matrix.validate_design_matrix`（五参数，唯一来源验证入口）
- `mechanism.model_digest.canonical_digest`
- `mechanism.hypothesis_config.canonical_decimal`
- `mechanism.hypothesis_config.FrozenJSONObject/FrozenJSONList/FrozenJSONNumber` 的**纯 JSON
  投影语义**（等价于既有 `mechanism.planning.compiler._thaw`：对象->dict、列表->list、
  `FrozenJSONNumber` -> 其规范十进制字符串）。该投影是第 10.2 节要求的摘要取数路径；
  执行层必须实现同一语义（不得改动该既有私有函数，也不得把冻结 dataclass 直接交给
  `canonical_digest`，见第 10.2 节实测）
- 现有 `MatrixPreparationV1`、`DatasetPreparationV1`、`DeterministicAnalysisPlan` 只读消费
- `numpy.linalg`（`matrix_rank`、`lstsq`）与 `numpy.random.PCG64/Generator`

### 14.3 明确不得触碰

`mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、`crash.py`、
`analysis_dataset.py`、`analysis_contracts.py`（含 `DESIGN_COLUMNS`、`ANALYSIS_COLUMNS`、
固定开发期与 holdout 常量）、`datasets/synthetic.py`（除经五参数入口间接调用）、
`statsmodels`、`pandas`，以及全部 M3 冻结产物与哈希。执行层不得引入 pandas 作为规范序列化
边界，也不得把 statsmodels 作为估计器。

### 14.4 schema 变更

本设计**不需要**任何 A.1 / A.2 / dataset / matrix schema 变更。实现过程中如发现确有必要变更
任何已冻结 schema，必须**停止并报告**，不得把变更藏进设计或实现。

## 15. 实现前置条件与验收边界

实现（另立 Goal、另获授权）前必须满足：

1. 本设计与 [有界执行验收场景 v1](m4_bounded_execution_acceptance_cases_v1.md) 通过独立审查，
   接口、常量、顺序与失败语义无关键待定项；
2. 全部验收案例先复现负例再实现正例；
3. 既有 adapter / matrix / plan / contract 回归与保护门保持通过；
4. 不新增镜像式产品测试来替代真实最小实现验证；
5. 实现落地后若某个摘要或端点与设计不一致，必须先判断是"实现偏离冻结契约"还是
   "设计需修订"，不得直接改期望值。

本设计的验收**不是**实现授权，也不是统计执行、真实数据、holdout、M4-B、push、PR 或 merge 授权。

## 16. 未决与风险

| 项 | 状态 | 说明 |
| --- | --- | --- |
| 模块落点 | 待实现评审 | `mechanism/execution/bounded.py` 为拟议；不得为落点改动既有导出 |
| 估计器实现选择 | 已冻结 | `numpy.linalg.lstsq` + 显式秩门；禁止 statsmodels 与 M3 路径 |
| 块长规则 | 已冻结 | 精确整数判据；已实测与 M3 时期浮点表达式在 `n=1..200000` 上逐值一致 |
| 重采样秩不足 | 已冻结为 fail-closed | 不做静默跳过；备选的"计数 + 最小可估计阈值"因需要人为常量被否决 |
| 分位数方法 | 已冻结 | 精确次序统计量；禁止依赖任何库的分位数默认值 |
| 注册稳健性派遣 | 已冻结为"只绑定、不执行" | 入口为 `prepare_registered_robustness_dispatch`；验证请求 ID/顺序/注册关系，完整不可变转发既有 canonical parameters（含未知嵌套键）；不解释参数语义、**不计算统计量**；`statistics_computed`/`outcome_read` 恒 `False`；其 `artifact_digest` 绑定的是完整 source chain、请求顺序与注册顺序、`method_id`、完整 canonical parameters、`provenance` 与代码/schema/runtime，**不含任何 float64 统计输出**（第 6.2 节第二层 (b)、第 10.4、12 节） |
| 产物身份摘要绑定范围 | 已冻结为**按产物种类分别绑定** | 主产物 `artifact_digest` **必须**绑定 `estimator`/`bootstrap`/`conditional_descriptives`/`evidence` 的全部 float64 输出；派遣产物因 `statistics_computed = False` **不存在**这类输出，故不得被描述为绑定 float 统计块（第 6.2、10.4 节） |
| 冻结参数进入摘要的取数路径 | 已冻结（R2 实测修正） | `FrozenJSONObject`/`FrozenJSONList`/`FrozenJSONNumber` 是 frozen dataclass，**不能**被 `canonical_digest` 直接序列化（实测抛 `TypeError`）；必须先投影为纯 JSON 形态（等价于既有 `planning/compiler._thaw` 语义，或 `json.loads(parameters_canonical_json)`）再进入摘要载荷（第 10.2、10.4、14.2 节） |
| `canonical_decimal` 语义 | 已冻结（R2 措辞修正） | `canonical_decimal(repr(v))` 是**最短 round-trip 十进制伴随渲染**，位数随取值变化，**不存在固定的 17 位**，也不是"超出 17 位的尾数被丢弃"；精确二进制身份由 `float.hex` 保留，两者并行进入主产物身份（第 6.2 节实测表） |
| 稳健性参数统计语义 | 明确不在本设计内 | 项目当前没有稳健性 handler contract（`mechanism/robustness.py` 绑定 M3 固定列名/开发期/阈值，不得触碰），因此 `trim`、`window` 等参数本阶段只是被完整转发的注册数据；其统计含义必须与真实 handler contract 在另立实现 Goal 中一并冻结（第 12.2 节） |
| 跨运行时字节复现 | 有限声明 | 同一输入 + 同一 `numeric_runtime` 下逐字节可复现；跨 numpy/BLAS 版本不作保证，产物记录 `numeric_runtime` 使差异可检测 |
| 覆盖不完整 | 不改写处置 | 由适配器质量门决定；产物显式暴露 `coverage_complete`，并由冻结解释边界限定读法 |
| 真实数据 | 不在本设计 | 无 provenance 升级路径；`execution_authorized` 恒 False |
| holdout | 不可达 | 无参数、无函数；计划层已 fail-closed；执行层门为 defense-in-depth |
| 实现与测试 | 未开始 | 本文件是设计，不是实现；不存在可通过的执行实现测试 |

### 16.1 明确不在本设计内的事情

- 本设计**没有**实现 `execute_bounded_analysis` 等任何函数；第 4、10 节全部为拟议 API。
- 本设计**没有**新增或修改任何产品测试；第 2.3、7.3 节的实测值、第 6.2 节的渲染实测表与
  第 10.2 节的摘要取数路径实测均来自一次性**只读**探针（标准输入，不写文件），探针未纳入交付，
  也**没有**计算任何系数、区间、p 值、秩或处置结果。
- 本设计**没有**调用 `regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`。
- 本设计**没有**访问数据库、provider、真实行情或 holdout。
- 本设计**不构成**执行授权、统计有效性声明或任何阶段的合并依据。
