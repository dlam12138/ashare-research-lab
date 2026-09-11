# M4 有界执行与证据处置验收场景 v1

状态：DESIGN_ONLY / ACCEPTANCE_CASES_NOT_IMPLEMENTED。本文是
[有界执行与证据处置设计 v1](m4_bounded_execution_and_evidence_design_v1.md) 的配套验收场景清单。

本文中的上游数值（合同/计划/输入/域/数据集/矩阵摘要、行、列、规则文本）都是 2026-09-11 在
本工作树用**既有真实实现**实测得到的；执行层自身的期望值是**设计口径**（由设计第 4–13 节
直接推得），**执行器产品实现尚不存在**，因此本文不声称任何执行实现测试已通过，也**不包含
任何系数、区间、p 值或处置结果的计算值**——设计阶段禁止计算这些量。

每个案例都写明四件事：**输入变化**、**预期输出或错误**、**验证阶段**（设计第 11 节编号）、
**授权解释**（该案例证明了哪一条授权边界）。

## 0. 验证入口与前置条件

### 0.1 唯一的来源验证入口

```text
validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)     # 既有五参数 API
```

其真实实现依次做：矩阵结构不变量与自摘要 -> 四参数 `validate_dataset`（重新 materialize 并
逐字节比较 `serialize_dataset`）-> 重投影 -> 逐字节比较 `serialize_matrix`。
任何"只比 `matrix_digest` 字符串"或"只跑 `serialize_matrix`"的变体都**不是**合格验证入口。

### 0.2 执行层的拟议入口（尚未实现）

```text
execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs) -> ExecutionArtifactV1
execution_artifact_to_canonical_dict(artifact) -> dict
serialize_execution_artifact(artifact) -> bytes
validate_execution_artifact(artifact, matrix, preparation, contract, plan, bound_inputs) -> None
prepare_registered_robustness_dispatch(matrix, preparation, contract, plan, bound_inputs,
                                       robustness_ids) -> RobustnessArtifactV1
robustness_artifact_to_canonical_dict(artifact) -> dict
serialize_robustness_artifact(artifact) -> bytes
validate_robustness_artifact(artifact, matrix, preparation, contract, plan, bound_inputs) -> None
```

- 唯一的**统计执行**入口是 `execute_bounded_analysis`。稳健性入口名为
  `prepare_registered_robustness_dispatch`，因为本阶段它只验证请求、绑定注册项并完整转发参数，
  **不执行任何统计**；其产物 `statistics_computed` / `outcome_read` 必须恒为 `False`。
- 两个入口都**必须**接收完整五元组；不存在只吃 `matrix` 的公开入口，不存在 `**kwargs`。
- 任何未声明的关键字参数（`holdout=`、`window=`、`split=`、`real_data=`）必须是 `TypeError`。
- 上游 `AdapterError` / `MatrixError` 原样传播；`ExecutionError` 只承载执行层自身的失败。

### 0.3 复现口径

fixture 使用既有测试模块 `tests/test_m4_stage4a1_typed_contract.py` 的 `_document()` /
`_compiled()` 与 `tests/test_m4_synthetic_dataset_adapter.py` 的 `_inputs()` / `_bound()`。
解释器：`D:/量化分析-m4a2i/.venv/Scripts/python.exe`（已确认存在，不自动安装依赖）。
`PYTHONPATH` 需包含工作树的 `src` 与 `tests`。探针只读、不写文件、不开数据库、
不调用 provider，也**不调用** `regression.py` / `bootstrap.py` / `robustness.py` / `evidence.py`。

### 0.4 基础上游身份（实测）

```text
contract_digest = ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457
plan_digest     = 45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981
input_digest    = c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602
domain_digest   = b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da
dataset_digest  = c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b
matrix_digest   = a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
sha256(serialize_dataset(preparation)) = 32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060
sha256(serialize_matrix(matrix))       = 70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa
len(rows) = 3 ; len(columns) = 5 ; response_role = "TARGET_OUTCOME"
ordered_terms = [alpha/INTERCEPT, beta_factor/FACTOR_CONTINUOUS,
                 beta_control_0001/CONTROL_0001, beta_control_0002/CONTROL_0002,
                 gamma_condition/CONDITION_INDICATOR]
bootstrap_plan = {enabled: true, method_id: MOVING_BLOCK_BOOTSTRAP_V1, replications: 1000,
                  seed: 42, rng: PCG64, confidence_level: "0.95",
                  block_length_policy_id: N_CUBERT_ROUNDED_CLAMP_1_20_V1}
robustness_plan.entries[0] = {robustness_id: SYNTH_ROBUSTNESS_1,
                              method_id: CONDITIONAL_DESCRIPTIVES_V1,
                              parameters: {trim: "0.0100", window: ["1","2","3"]}}
                              # 计划规范字典的形态（A.1 源文档为 window: [1,2,3]，
                              # 经 _canonical_json_value 规范化为十进制字符串数组）
evidence_plan = {rule_id: SYNTH_EVIDENCE_RULE_1, expected_direction: POSITIVE,
                 confidence_requirement: "0.95",
                 data_quality_failure_disposition: INCONCLUSIVE,
                 required_statistic_roles: [PRIMARY_EFFECT_ESTIMATE, PRIMARY_EFFECT_CI_LOWER,
                   PRIMARY_EFFECT_CI_UPPER, CONDITIONAL_MEAN_DIFFERENCE,
                   CONDITIONAL_MEDIAN_DIFFERENCE, PRIMARY_SAMPLE_COVERAGE],
                 outcome_read: false}
holdout_boundary = {policy_id: NO_HOLDOUT_AUTHORIZED, execution_authorized: false}
```

### 0.5 正例 fixture 的形状要求（设计推导，非实测数值）

基础 fixture 的矩阵是 `3 x 5`。对任意 `n x k` 矩阵恒有 `rank <= min(n, k)`，故
`rank <= 3 < 5`：**基础 fixture 必然 `SINGULAR_DESIGN`**，不能用作正例。因此：

```text
正例 fixture（AC-01、AC-08、AC-13、AC-14 使用）必须满足：
  n >= k（n 为完整行数，k 为 ordered_terms 长度）
  且 X 的 k 列线性无关（列满秩）
  且每一行的响应值来自 preparation.complete_rows 的同一行
```

正例断言只检查**结构与不变量**（系数按 position 顺序齐全、`Float64ValueV1` 自洽、
摘要可复算、两次执行逐字节相同、产物不含禁止内容），不包含任何数值期望——数值期望属于
实现阶段由真实实现产出后另行评审。

## 1. 案例索引

| ID | 案例 | 类型 | 验证阶段 | 授权解释 |
| --- | --- | --- | --- | --- |
| AC-01 | 正例：满秩合成矩阵的完整产物 | 正常 | X1–X16 | 合成执行就绪 ≠ 真实研究授权 |
| AC-02 | 基础 fixture 秩不足 | 负例/秩 | X8 | 秩不足不降级 |
| AC-03 | 来源篡改（重哈希 preparation / 重哈希输入） | 负例/安全 | X2 | 来源必须先验证 |
| AC-04 | 矩阵伪造（自洽重算摘要 / 未重算摘要） | 负例/身份 | X2 / V1 | 内容不一致必须拒绝 |
| AC-05 | 验证顺序错误（多重缺陷同时存在） | 负例/顺序 | X2 先于 X3–X15 | 结构错误不得掩盖来源错误 |
| AC-06 | 不支持的方法 / 模型族 | 负例/方法 | X3 | 不支持即失败，不降级 |
| AC-07 | 单元格越界与非有限 | 负例/转换 | X7 / X10 | 数值边界 fail-closed |
| AC-08 | bootstrap 启用（含精确端点序号） | 正常/端点 | X11–X13 | 端点语义精确、无容差 |
| AC-10 | 三个方向的完整处置表 | 正常/处置 | X15 + D3–D10 | 处置只在合成产物内有效 |
| AC-11 | 质量拒绝与质量失败处置词 | 负例/质量 | X2 / X4 | 质量拒绝不产出可用产物 |
| AC-12 | 注册稳健性派遣：请求、顺序与完整转发 | 负例/派遣 | R7 / R8 / R9 | 只做注册派遣，不自动扩展 |
| AC-13 | holdout 拒绝 | 负例/授权 | 签名层 / X2 / X5 | holdout 不可达 |
| AC-14 | 输入排列、键序与工作目录不变性 | 等价性 | X16 | 身份只由内容决定 |
| AC-15 | 产物字节可复现与重执行校验 | 等价性 | V1–V4 | 产物可独立复核 |
| AC-16 | 嵌套修改（合同内层字段） | 负例/身份 | X2 / X16 | 身份绑定全量内容 |
| AC-17 | 显式合成来源标记与禁止内容 | 结构/来源 | X16 | 不可能被读成真实研究 |
| AC-18 | 两层身份：上游规范十进制 vs 产物**按种类**绑定（主产物 float64 / 派遣产物无统计量） | 结构/身份 | X16 / V1 | float64 只进**主产物**身份，不回写上游；派遣产物不含 float 统计输出 |
| AC-19 | `bootstrap.enabled` 严格复制计划声明 | 结构/授权 | X11 / X16 | 不存在"声明启用、实际禁用"的运行时降级 |

编号说明：本清单编号是稳定标识，**不得**留下"索引里有条目、正文里没有对应小节"的孤儿编号。
R0 曾列出 `AC-09 bootstrap 禁用路径`，但正文从未写出该小节，且其内容已被 AC-19 完整覆盖，
故 R2 **删除 AC-09 编号及其全部引用**（不保留空号，也不重编号其它案例）。合同要求的
"bootstrap disabled/enabled 覆盖"明确归于：

| 合同要求的覆盖 | 承载案例 |
| --- | --- |
| bootstrap **禁用**路径 | **AC-19b**（`enabled=false` / `method_id="DISABLED"`：端点全 `null`、不建 generator、处置 `INCONCLUSIVE`/`BOOTSTRAP_DISABLED`） |
| bootstrap **启用**路径 | **AC-08**（启用时执行并逐项核对端点序号与 `interval_alpha`）与 **AC-19a**（`enabled` 为计划声明的严格复制且端点非 `None`） |
| **无运行时降级** | **AC-19c**（计划层 `INVALID_BOOTSTRAP_POLICY` 原样传播）与 **AC-19d**（诱导失败必须整体 fail-closed，不得产出"无区间产物"） |

## 2. 正常案例

### AC-01 正例：满秩合成矩阵的完整产物

**输入变化**：构造满足第 0.5 节的合成合同/计划/bound_inputs（`n >= k` 且列满秩），
其余字段沿用基础 fixture 的语义（合成模式、`PCG64`、`seed=42`、`confidence_level="0.95"`、
方向 `POSITIVE`、`confidence_requirement="0.95"`）。

**预期输出**：

```text
execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs) 返回 ExecutionArtifactV1，且：
  source_chain == {contract_digest, plan_digest, input_digest, domain_digest, dataset_digest, matrix_digest}
                  逐字段等于该次输入的既有实测值
  provenance == {provenance_class: "SYNTHETIC_TEST_ONLY", synthetic_test_only: true,
                 dataset_mode: "SYNTHETIC", real_data_used: false, holdout_accessed: false}
  execution_authorized is False ; statistics_computed is True ; outcome_read is True
  method_configuration.terms 顺序 == ordered_terms 顺序，且每项 (position, term_role, coefficient_role) 一致
  method_configuration.primary_effect_role == "gamma_condition"
  estimator.coefficients 长度 == k，顺序 == ordered_terms 顺序，每项 value 自洽
  estimator.rank == k ; estimator.n_terms == k ; estimator.n_rows == len(matrix.rows)
  bootstrap.enabled is True（严格复制 plan.bootstrap_plan.enabled，见 AC-19）
  bootstrap.method_id == "MOVING_BLOCK_BOOTSTRAP_V1"
  bootstrap.replications == 1000 ; bootstrap.seed == 42 ; bootstrap.rng == "PCG64"
  bootstrap.block_length == L(n)（设计第 7.3 节整数规则；n=1000 时为 10）
  bootstrap.primary_effect_lower/upper 均为 Float64ValueV1
  conditional_descriptives 的角色集合与顺序 == conditional_summary_plan.required_statistic_roles（八项）
  evidence.disposition ∈ DISPOSITIONS ; evidence.disposition_reason ∈ REASONS
  evidence.interval_lower/upper == bootstrap 端点（同一 float64_hex）
  evidence.interpretation_boundary == 设计第 10.5 节冻结字面量（逐字相同）
  artifact_digest == canonical_digest(payload − artifact_digest)
  serialize_execution_artifact(artifact) 以单个 "\n" 结尾、UTF-8、无 BOM、无缩进
  validate_execution_artifact(artifact, matrix, preparation, contract, plan, bound_inputs) 返回 None
```

**验证阶段**：X1–X16（全链通过）。

**授权解释**：本案例只证明合成输入上执行层可用。`execution_authorized is False` 与
`provenance.synthetic_test_only is True` 同时存在，证明"合成执行就绪"没有被写成"真实研究授权"。

### AC-08 bootstrap 启用与精确端点序号

**输入变化**：`bootstrap_policy` 取下列组合（其余不变）并重新冻结、编译：

| 子案例 | `confidence_level` | `replications` | 预期 `interval_alpha` | 预期 `lower_index` | 预期 `upper_index` |
| --- | --- | --- | --- | --- | --- |
| 8a | `"0.95"` | 1000 | `"0.025"` | 25 | 974 |
| 8b | `"0.95"` | 8 | `"0.025"` | 0 | 7 |
| 8c | `"0.95"` | 3 | `"0.025"` | 0 | 2 |
| 8d | `"0.5"` | 8 | `"0.25"` | 2 | 5 |
| 8e | `"0.99"` | 1000 | `"0.005"` | 5 | 994 |
| 8f | `"0.9"` | 20 | `"0.05"` | 1 | 18 |
| 8g | `"0.95"` | 2 | `"0.025"` | 0 | 1 |

（以上七个 `alpha` 与序号由设计第 7.6 节的精确十进制规则推出，2026-09-11 用 `Decimal` 的
`ROUND_FLOOR` / `ROUND_CEILING` 实测复核：`k_lo = floor(B*alpha)`、
`k_hi = ceil(B*(1-alpha)) - 1`。）

**预期输出**：产物的 `bootstrap.{interval_alpha, lower_index, upper_index}` 与上表逐项相等；
端点是排序后重采样主效应样本的**精确次序统计量**，无插值；`lower <= upper`；
`evidence.confidence_requirement_satisfied` 为
`Decimal(confidence_level) >= Decimal(confidence_requirement)` 的精确结果。

**关键断言**：

1. 必须**不**使用 `numpy.quantile` / `percentile` 的任何默认 `method`（不得出现插值端点）。
2. `interval_alpha` 必须是规范十进制字符串（`"0.025"` 而不是 `"0.0250"` 或 `"2.5E-2"`）。
3. 重复执行必须给出逐位相同的端点（同一 `seed` + `PCG64` + 同一抽样调用顺序）。
4. `replications == 1` 时必须是 `INSUFFICIENT_REPLICATIONS`（`BOOTSTRAP_MIN_REPLICATIONS = 2`），
   而不是退化区间。
5. 本案例只覆盖**启用分支**（`plan.bootstrap_plan.enabled is True`）。**禁用分支**
   （`enabled=false` / `method_id="DISABLED"`）不在本案例内，其验收在 **AC-19b**：产物端点全为
   显式 `null`、不创建 generator、不访问随机数 API、处置 `INCONCLUSIVE`/`BOOTSTRAP_DISABLED`；
   "禁用不是任何失败的后备出口"由 **AC-19d** 断言。

**验证阶段**：X11–X13（启用分支；另加 D2/D3 的置信要求比较）。

**授权解释**：端点的精确性只影响合成产物内部的一致性；本案例不声称任何统计有效性。

### AC-10 三个方向的完整处置表

**输入变化**：`evidence_rule.expected_direction` 分别取 `POSITIVE` / `NEGATIVE` / `TWO_SIDED`，
`confidence_requirement` 与 `confidence_level` 分别取"满足"与"不满足"两种组合，并构造
`lower`/`upper` 落在零的三种相对位置（严格上侧、严格下侧、包含零）的重采样样本。

**预期处置**（设计第 8.3 节，D 编号即优先级）：

| 子案例 | `direction` | 端点关系 | `level` vs `requirement` | `disposition` | `disposition_reason` |
| --- | --- | --- | --- | --- | --- |
| 10a | `POSITIVE` | `lower > 0` | `level >= requirement` | `POSITIVE_SUPPORTED` | `INTERVAL_ABOVE_ZERO` |
| 10b | `POSITIVE` | `lower <= 0` | `level >= requirement` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |
| 10c | `NEGATIVE` | `upper < 0` | `level >= requirement` | `NEGATIVE_SUPPORTED` | `INTERVAL_BELOW_ZERO` |
| 10d | `NEGATIVE` | `upper >= 0` | `level >= requirement` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |
| 10e | `TWO_SIDED` | `lower > 0` | `level >= requirement` | `TWO_SIDED_SUPPORTED` | `INTERVAL_ABOVE_ZERO` |
| 10f | `TWO_SIDED` | `upper < 0` | `level >= requirement` | `TWO_SIDED_SUPPORTED` | `INTERVAL_BELOW_ZERO` |
| 10g | `TWO_SIDED` | `lower <= 0 <= upper` | `level >= requirement` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |
| 10h | 任意 | 任意 | `level < requirement` | `INCONCLUSIVE` | `CONFIDENCE_BELOW_REQUIREMENT` |
| 10i | 任意 | 端点恰为 `0.0`（或 `-0.0`） | `level >= requirement` | `NOT_SUPPORTED` | `INTERVAL_INCLUDES_ZERO` |

**关键断言**：

1. **无容差**：`lower == 0.0`、`lower == -0.0`、`upper == 0.0`、`upper == -0.0` 一律判为
   "包含零"，绝不产出 `*_SUPPORTED`（实测：`-0.0 > 0` 为 `False`，`0.0 > 0` 为 `False`，
   `-0.0 < 0` 为 `False`，`0.0 < 0` 为 `False`）。禁止出现 epsilon、`isclose`、`allclose`。
2. D2/D3 的优先级高于 D4–D10：`level < requirement` 时无论端点如何都是 `INCONCLUSIVE`。
3. `direction` 取三词之外的值必须是 `UNSUPPORTED_EVIDENCE_DIRECTION`，不得默认 `TWO_SIDED`。
4. `disposition` 与 `disposition_reason` 必须同时落在设计第 8.2 节的封闭词表内，
   产物中不得出现第六个处置词（例如 `FAIL`）。

**验证阶段**：X15（D2–D10）。

**授权解释**：处置词只是合成产物内部对"本产物自身统计量"的机械处置，不是研究结论，
不构成 estimability / significance / 经济有效性 / 可交易性声明。

## 3. 秩、来源与身份案例

### AC-02 基础 fixture 秩不足

**输入变化**：无。直接使用基础 fixture（`n = 3`，`k = 5`）。

**预期输出**：

```text
execute_bounded_analysis(base_matrix, base_preparation, base_contract, base_plan, base_inputs)
    -> ExecutionError("SINGULAR_DESIGN")，无产物返回
```

**关键断言**：`rank(X) <= min(n, k) = 3 < 5 = k` 是纯维度事实，因此拒绝是**必然**的，
不是数值偶然。拒绝必须发生在 X8，且：

1. 不得返回最小范数解、不得使用 `pinv`、不得丢列、不得丢控制项、不得改用其它估计器；
2. 不得因为"基础 fixture 是项目 canonical fixture"而放松秩门；
3. 不得返回带部分系数或全 `null` 系数的对象。

**验证阶段**：X8。

**授权解释**：秩门是"合成执行就绪"的必要条件；拒绝秩不足输入不等于任何研究结论。

### AC-03 来源篡改（重哈希 preparation / 重哈希输入）

**输入变化**（两组，均沿用矩阵阶段的实测结论）：

```text
3a preparation 自洽篡改：把 complete_rows 的三行 condition_indicator 全部取反并重算 dataset_digest
   tampered.dataset_digest = 721584843f0f10448b0e1aecc28cc30a52018844be4c5852923c0acdab57b79f
   serialize_dataset(tampered) = ACCEPTED（内部自洽）
   validate_dataset(tampered, contract, plan, bound_inputs) = IDENTITY_CONFLICT
3b 原始输入重哈希篡改：把 FACTOR@2020-01-03 由 "-0.01" 改为 "-0.05"，同步重算 evidence_digest 与 input_digest
   rehashed.input_digest = e877c147b58b53ee3283e87bcce49592470643c161e7a675af1e06a51943b464
   validate_dataset(rehashed_preparation, contract, plan, 原始 bound_inputs) = IDENTITY_CONFLICT
```

**预期输出**：

```text
execute_bounded_analysis(*, tampered 或 rehashed, *) -> 上游 AdapterError("IDENTITY_CONFLICT")，原样传播
```

**关键断言**：

1. 错误发生在 X2，**不是** `ExecutionError`；执行层不得包装、改码、吞掉或替换；
2. 篡改体的自报摘要形状合法、serializer 通过，都**不能**作为放行依据；
3. 不存在只吃 `preparation` 或只吃 `matrix` 的公开旁路。

**验证阶段**：X2。

**授权解释**：来源验证是执行的前置条件，不是执行层可选的自检。

### AC-04 矩阵伪造

**输入变化**：取合法输入，先按既有口径得到合法矩阵 `M`，再伪造：

- `M1`：修改 `M.rows[0].cells` 的指示格后**重算** `matrix_digest`（对象自身自洽）；
- `M2`：只改 `M.rows[0].cells` 而**不**重算 `matrix_digest`；
- `M3`：只把 `M.execution_authorized` 改成 `True`（若构造允许）并重算摘要。

**预期输出**：

| 对象 | 调用 | 预期结果 |
| --- | --- | --- |
| `M1` | `execute_bounded_analysis(M1, ...)` | `MatrixError("IDENTITY_CONFLICT")`（X2 重投影字节不一致） |
| `M2` | `execute_bounded_analysis(M2, ...)` | `MatrixError("MATRIX_DIGEST_MISMATCH")`（X2 自摘要不符） |
| `M3` | `execute_bounded_analysis(M3, ...)` | `MatrixError("INVALID_INPUT_STRUCTURE")`（矩阵不变量 9：两个布尔必须恒 False） |
| `M1` | `validate_execution_artifact(合法产物, M1, ...)` | `MatrixError("IDENTITY_CONFLICT")`（V2） |
| 伪造产物 `A1`（改 `evidence.disposition` 且重算摘要） | `validate_execution_artifact(A1, ...)` | `ExecutionError("IDENTITY_CONFLICT")`（V4） |
| 伪造产物 `A2`（改字段但不重算摘要） | `validate_execution_artifact(A2, ...)` | `ExecutionError("ARTIFACT_DIGEST_MISMATCH")`（V1） |

**关键断言**：来源合法时执行层仍必须独立拒绝伪造矩阵与伪造产物；`ARTIFACT_DIGEST_MISMATCH`（V1）、
上游 `IDENTITY_CONFLICT`（V2）与执行层 `IDENTITY_CONFLICT`（V4）分属三个不同阶段，不得混淆、
不得降级为通过。

**验证阶段**：X2 / V1 / V2 / V4。

**授权解释**：产物是终态；篡改后的产物无法被"重新解释"为合法授权证据。

### AC-05 验证顺序错误

**输入变化**：同时制造多个缺陷，检验首个错误是否唯一且顺序固定。

| 子案例 | 同时存在的缺陷 | 预期首个错误 | 预期阶段 |
| --- | --- | --- | --- |
| 5a | 来源被篡改 + `analysis_method_id` 不在允许列表 | 上游 `AdapterError("IDENTITY_CONFLICT")` | X2 |
| 5b | `matrix.execution_authorized=True` + 单元格越界 | `MatrixError("INVALID_INPUT_STRUCTURE")` | X2 |
| 5c | 合法来源 + 方法不在允许列表 + 方向非法 + 稳健性未注册 | `ExecutionError("UNSUPPORTED_ANALYSIS_METHOD")` | X3 |
| 5d | 合法来源 + 合法方法 + 质量前提不成立 + 单元格越界 | `ExecutionError("DATA_QUALITY_REJECTED")` | X4 |
| 5e | `prepare_registered_robustness_dispatch(..., ())` + 合法来源 | `ExecutionError("EMPTY_ROBUSTNESS_DISPATCH")` | R7 |
| 5f | 来源被篡改 + 请求未注册 ID | 上游 `AdapterError("IDENTITY_CONFLICT")` | X2（**先于** R7） |
| 5g | 合法来源 + 未注册 ID + 非法 `method_id` 注册项 | `ExecutionError("UNREGISTERED_ROBUSTNESS_ID")` | R7（先于 R8） |

**关键断言**：

1. **来源未验证就不允许讨论方法、质量、派遣或数值**：X2 必须早于 X3–X16 与 R7–R9；
2. 同一输入重复调用必须命中**同一个首个错误**（确定性）；
3. 结构错误不得被来源错误掩盖，来源错误不得被方法/质量错误掩盖；
4. 不允许先做"廉价检查"再验证来源的优化。

**验证阶段**：X2 与 X3/X4/R7/R8 的相对顺序。

**授权解释**：顺序本身是授权边界的一部分：任何"先算后验"的实现都会让未验证数据进入估计器。

### AC-16 嵌套修改（合同内层字段）

**输入变化**：在 `_document()` 内层做三组独立修改，各自重新冻结与编译：

```text
16a robustness_registry[0].parameters.trim: "0.0100" -> "0.0200"
16b evidence_rule.confidence_requirement:   "0.95"   -> "0.90"
16c bootstrap_policy.seed:                  42       -> 43
16d robustness_registry[0].parameters.window: [1,2,3] -> [1,2,999]（嵌套数组元素）
```

**预期输出**（16a 为矩阵阶段实测值，用于说明"内层字段也进入身份"）：

```text
16a nested.contract_digest = f4c193cbbc9a32e9bc7d17bf9ba494c7702fc46acd3c723102d025e8084eed9f
    nested.plan_digest     = 8833ed844a7f50d9665945b7d18c07d2e1d72bde97b13cf8aeefcad24e2cc677
    nested.dataset_digest  = dfa395bb1dff0c694cad4d8cc3438d07c2896f92bdb72d20fdbcfe663eaf5c6d
    nested.matrix_digest   = b75877ee489f1a08bdcbbcc6fa0f0c57a9a1e1fcc940844ca04ea5ea7c2ddd5e
    materialize_analysis_dataset(nested_contract, base_plan, base_inputs) -> AdapterError("CONTRACT_PLAN_MISMATCH")
```

**关键断言**：

1. 16a 不改变任何单元格数值、也不改变主样本的估计结果，但 `contract_digest` / `plan_digest` /
   `dataset_digest` / `matrix_digest` / `artifact_digest` **必须全部改变**；
2. 16b 必须改变 `evidence.confidence_requirement_satisfied` 的判定与产物摘要
   （`"0.90"` 与默认 `"0.95"` 在精确十进制比较下不同）；
3. 16c 必须改变全部 bootstrap 端点与产物摘要（种子进入身份）；
4. 16d 必须改变 `artifact_digest`，即使主产物完全不受影响：稳健性派遣产物逐字转发嵌套参数，
   因此"静默丢弃或改写一个未知嵌套键"必然可检测（设计第 10.4、12.2 节）；
5. 把新合同与旧计划混用必须在 X2 得到 `AdapterError("CONTRACT_PLAN_MISMATCH")`。

**验证阶段**：X2 / X16。

**授权解释**：身份绑定内容的全量，而不是"看起来相关的字段"。

## 4. 数值与质量案例

### AC-06 不支持的方法与模型族

**输入变化**：

| 子案例 | 变化 | 预期错误 | 阶段 |
| --- | --- | --- | --- |
| 6a | `analysis_method.method_id` 改为另一个标识符并重新冻结编译（若 A.1 允许），或以 `replace` 构造 `analysis_method_id` 非允许值的计划对象 | `ExecutionError("UNSUPPORTED_ANALYSIS_METHOD")` | X3 |
| 6b | `plan.design_plan.model_family` 改为 `"WLS"` 并重算 `plan_digest`（若计划校验放行），或构造等价的计划对象 | `ExecutionError("UNSUPPORTED_MODEL_FAMILY")` | X3 |
| 6c | `bootstrap_plan.method_id` 改为未注册方法（`enabled=true`） | `ExecutionError("UNSUPPORTED_BOOTSTRAP_METHOD")` | X11 |
| 6d | `bootstrap_plan.rng` 改为未注册 RNG 标识 | `ExecutionError("UNSUPPORTED_BOOTSTRAP_RNG")` | X11 |

**关键断言**：

1. 不支持即失败：**不得**回退到另一种估计器、不得回退到 M3 的 `statsmodels` 路径、
   不得静默改用普通最小二乘之外的近似、不得跳过 bootstrap 后继续出产物；
2. `ExecutionError` 只在执行层抛出；若缺陷先在计划校验层被发现，则必须是上游错误原样传播
   （例如 `AdapterError("CONTRACT_PLAN_MISMATCH")`），执行层不得把它改写成自己的码；
3. 计划层已冻结的取值（`DAILY_CONDITIONAL_CONTROLLED_OLS_V1`、`OLS`、`MOVING_BLOCK_BOOTSTRAP_V1`、
   `PCG64`）不得被本设计放宽。

**验证阶段**：X3 / X11。

**授权解释**：方法允许列表是"有界"二字的实质；放宽即越界。

### AC-07 单元格越界与非有限

**输入变化**：

| 子案例 | 变化 | 预期错误 | 阶段 |
| --- | --- | --- | --- |
| 7a | 某合成 observation 的 `value` 取 `"1000001"`（规范十进制、有限但越界；合同/计划不变） | `ExecutionError("CELL_OUT_OF_RANGE")` | X7 |
| 7b | 某 `value` 取 `"1000000"`（恰好等于上界） | 通过 X7（含端点） | X7 |
| 7c | 某 `value` 取 `"1000000000000000000"`（`1e18`，规范十进制、越界） | `ExecutionError("CELL_OUT_OF_RANGE")` | X7 |
| 7d | 直接构造非有限的 `Float64ValueV1` 渲染输入 | `ExecutionError("NON_FINITE_ESTIMATE")` | X10 |

**关键断言**：

1. 越界门使用**精确十进制**比较（`abs(Decimal(text)) > Decimal("1000000")`），
   不使用 float 比较；实测 `abs(Decimal("1000000")) > Decimal("1000000")` 为 `False`（含端点），
   `abs(Decimal("1000001")) > Decimal("1000000")` 为 `True`；
2. 非有限值一律 fail-closed：不得写成 `null`、`0`、`"NaN"` 或"不可用后继续"；
3. 冻结的输出渲染规则本身在非有限输入上必须失败：`canonical_decimal(repr(float("inf")))`
   抛 `HypothesisConfigError`（既有实现），执行层必须把它映射为 `NON_FINITE_ESTIMATE`；
4. 越界值与"非规范十进制"是两件事：`"1E+18"`、`"0.0100"`、`"-0"` 在矩阵层就以
   `INVALID_INPUT_STRUCTURE` 被拒绝，执行层不应看到它们。

**验证阶段**：X7 / X10。

**授权解释**：数值边界是 fail-closed 的输入门，不是数据清洗步骤。

### AC-11 质量拒绝与质量失败处置词

**输入变化**：构造质量前提不成立的输入：

| 子案例 | 构造 | 预期矩阵层行为 | 预期执行层行为 | 阶段 |
| --- | --- | --- | --- | --- |
| 11a | gate 0.99 / `FAIL_CLOSED` / 缺 `CONTROL_0002@2020-01-03` | `materialize_design_matrix` 抛 `MatrixError("DATASET_NOT_READY")`（无矩阵对象） | 无输入可执行 | X2 之前 |
| 11b | gate 0.67 / `RETAIN_IN_DENOMINATOR` / 同上缺口 | `DatasetPreparationV1.status = REJECTED_QUALITY`，`complete_rows = ()` | 同 11a | X2 之前 |
| 11c | 构造"对象自称 `READY_SYNTHETIC` 且行非空，但 `coverage_numerator/denominator/gate` 精确比较不成立"的自洽伪造矩阵 | 自摘要自洽 | `ExecutionError("DATA_QUALITY_REJECTED")`，且 `.disposition == plan.evidence_plan.data_quality_failure_disposition`（`"INCONCLUSIVE"`） | X4 |
| 11d | gate 0.66 / `RETAIN_IN_DENOMINATOR` / 缺一行（合法 READY，`n/N = 2/3`） | 返回 2 行矩阵 | 正常执行；`sample.coverage_complete is False`、`coverage_gate_satisfied is True`，处置**不因覆盖不完整而改写** | X4 / X16 |

**关键断言**：

1. 质量拒绝**不产出任何产物对象**：没有 0 行产物、没有部分产物、没有"带降级标记"的产物；
2. 计划声明的 `data_quality_failure_disposition` 只以拒绝本身的 `.disposition` 出现；
   它**不是** `DISPOSITIONS` 的成员，因此不可能被误读成一项研究结论；
3. `FAIL_CLOSED` 下把 gate 从 `0.99` 降到 `0.66` **不能**绕过质量门（矩阵阶段已实测两者都是
   `REJECTED_QUALITY`）；
4. 覆盖门比较必须是精确有理数比较（`n*q >= d*p`），不是浮点或显示百分比；
5. 覆盖不完整（11d）由适配器的冻结质量门判定，执行层不得发明新的降级规则，但必须把
   `coverage_complete = False` 写进产物，使部分覆盖不可能被误读为完整覆盖。

**验证阶段**：X2（11a/11b 在上游就已拒绝）/ X4 / X16。

**授权解释**：质量拒绝是"没有可执行输入"，不是"以更弱的证据继续执行"。

## 5. 稳健性、holdout 与不变性案例

### AC-12 注册稳健性派遣：请求、顺序与完整转发

**输入变化**：

| 子案例 | `robustness_ids` | 注册表 | 预期结果 | 阶段 |
| --- | --- | --- | --- | --- |
| 12a | `("SYNTH_ROBUSTNESS_1",)` | **未修改** fixture 注册表（参数含 `trim` 与 `window`） | **成功**；产物 `entries` 长度为 1，`parameters_canonical_json == '{"trim":"0.0100","window":["1","2","3"]}'` | R8 / R9 |
| 12b | `("SYNTH_ROBUSTNESS_1",)` | 参数恰为 `{"trim": "0.0100"}` 的合成注册项 | 成功；产物完整转发该参数 | R8 / R9 |
| 12c | `("SYNTH_UNREGISTERED",)` | 任意 | `ExecutionError("UNREGISTERED_ROBUSTNESS_ID")` | R7 |
| 12d | `()` | 任意 | `ExecutionError("EMPTY_ROBUSTNESS_DISPATCH")` | R7 |
| 12e | `("SYNTH_ROBUSTNESS_1", "SYNTH_ROBUSTNESS_1")` | 任意 | `ExecutionError("DUPLICATE_ROBUSTNESS_ID")` | R7 |
| 12f | `("SYNTH_ROBUSTNESS_1", "SYNTH_ROBUSTNESS_2")` | 两条都已注册 | 成功；`entries` 顺序 == 请求顺序，`request_ordinal` = 0/1 | R9 |
| 12g | `("SYNTH_ROBUSTNESS_1",)` | 注册项 `method_id` 为空或非字符串（需 `dataclasses.replace` 构造，合法计划不可达） | `ExecutionError("UNSUPPORTED_ROBUSTNESS_METHOD")` | R8 |
| 12h | `("SYNTH_ROBUSTNESS_1",)` | 注册项 `parameters` 不是 JSON 对象（例如数组；需 `replace` 构造，合法计划不可达） | `ExecutionError("UNSUPPORTED_ROBUSTNESS_METHOD")` | R8 |
| 12i | `("SYNTH_ROBUSTNESS_1",)` | 注册表为空（既有 A.2I 允许 `robustness_registry = []`） | `ExecutionError("UNREGISTERED_ROBUSTNESS_ID")` | R7 |

**预期产物不变量**（12a/12b/12f）：

```text
artifact_schema_version == "M4_REGISTERED_ROBUSTNESS_ARTIFACT_V1"
dispatch.requested_ids   == 调用方请求顺序
dispatch.registered_ids  == plan.robustness_plan.entries 的完整顺序（含未被请求项）
dispatch.automatic_expansion is False ; dispatch.automatic_selection is False
dispatch.parameters_interpreted is False
entries[i].parameters    == 计划注册项 parameters 的完整不可变转发（含未知嵌套键）
entries[i].parameters_canonical_json == 重新序列化 parameters 的紧凑 JSON 文本
execution_authorized is False ; statistics_computed is False ; outcome_read is False
产物不含 evidence 块、不含任何统计量字段
artifact_digest == canonical_digest(payload − artifact_digest)
```

**关键断言**：

1. **只做注册派遣**：`entries` 中未被请求的注册项不得出现在 `entries` 里；没有 "run all" 开关；
2. **不自动选择**：产物没有 `best` / `selected` / `winner` / `aggregate` / `ranking` 字段，
   序列化器遇到这些键名必须抛 `FORBIDDEN_ARTIFACT_CONTENT`；
3. **完整转发**：参数的**全部**键与嵌套值（包括设计未提及的 `window`）必须逐字进入产物；
   不得忽略、不得改写、不得补默认值、不得重新规范化；
4. **不解释统计语义**：本阶段没有任何"稳健性方法允许列表"或"参数 schema"；
   执行层不得为 `trim`/`window` 发明含义，也不得据参数取值拒绝注册项——
   参数只被绑定与转发（12a 必须成功，而不是 fail-closed）；
5. **不执行**：产物 `statistics_computed is False`、`outcome_read is False`，
   且没有任何 `count`/`value`/`statistics` 字段，因此派遣不可能被读成稳健性结论；
6. **整单失败**：任一非法请求使整次调用 fail-closed，不返回截断的 `entries`；
7. **嵌套变异必须改变身份**：嵌套参数变异（AC-16 的 16d）必须改变 `artifact_digest`，
   否则"静默丢弃一个未知参数"将不可检测；
8. **12g/12h 是对计划放宽的 defense-in-depth**：既有 A.1/A.2I 已强制合法 `method_id` 与
   规范 JSON 对象，所以这两条对合法计划不可达，验收只断言门存在且位于 R8；
   可构造的负例是 12c/12d/12e/12i。

**验证阶段**：R7 / R8 / R9。

**授权解释**：注册派遣只证明"请求的注册项被完整、可复核地绑定"，
既不表示稳健性统计已运行，也不构成"从多个结果中挑一个"的能力。

### AC-13 holdout 拒绝

**输入变化**：三条互相独立的路径：

| 子案例 | 构造 | 预期结果 |
| --- | --- | --- |
| 13a | 调用 `execute_bounded_analysis(..., holdout=...)` 或任何未声明关键字参数 | Python `TypeError`（签名不存在该参数，且不接受 `**kwargs`） |
| 13b | 构造 `holdout_policy`（`2023-01-01..2023-12-31`）并编译；`plan.holdout_boundary.execution_authorized` 必须仍为 `False` | 执行通过 X5；`holdout_boundary.execution_authorized is False` 被断言；行日期全部在开发期窗口内 |
| 13c | 用 `dataclasses.replace` 把 `plan.holdout_boundary.execution_authorized` 改为 `True` 后调用 | X2 中 `validate_analysis_plan` 抛 `ValueError("HOLDOUT_EXECUTION_NOT_AUTHORIZED")`，被适配器包装为 `AdapterError("CONTRACT_PLAN_MISMATCH")` 原样传播 |
| 13d | 结构断言：X5 的 holdout 行窗口检查必须位于 X2 之后（来源验证通过后才检查），且存在 | 结构性检查通过（该门对合法输入不可达，属 defense-in-depth） |

**关键断言**：

1. holdout 的**第一道拒绝是签名本身**：没有 holdout 位置参数、没有关键字参数、没有 `**kwargs`；
2. 计划层已经 fail-closed（`HOLDOUT_EXECUTION_NOT_AUTHORIZED`）；
3. 执行层的行窗口门只作为 defense-in-depth，**不构造端到端命中**，验收只断言其存在与顺序；
4. 任何产物都不含 holdout 数据：`provenance.holdout_accessed is False`；
5. 本设计不存在任何"用 holdout 复核"的入口。

**验证阶段**：签名层 / X2 / X5。

**授权解释**：holdout 边界保持不授权，且没有可传递的请求面。

### AC-14 输入排列、键序与工作目录不变性

**输入变化**：

1. `bound_inputs.observations` 整体逆序；
2. 计划/产物规范字典的键顺序按 `sha256(键名)` 重排（值不变）；
3. 把当前工作目录切换到 `src/ashare_research` 后重新执行。

**预期输出**（矩阵阶段已实测 1、2、3 对上游身份无影响）：

```text
permutation.input_digest_equal   = True
permutation.dataset_digest_equal = True
permutation.matrix_digest_equal  = True
keyshuffled.artifact_digest_equal = True
other_cwd.artifact_digest_equal   = True
other_cwd.serialize_bytes_equal   = True
```

**关键断言**：

1. 观测行排列不进入身份（`_input_payload` 在计算 `input_digest` 前已按 `(trade_date, 角色序位)` 排序）；
2. 键顺序不进入身份（`canonical_digest` 内部固定 `sort_keys=True`）；
3. 工作目录与绝对路径不进入身份，也不出现在产物字节中（见 AC-17 的禁止内容检查）；
4. 行序只由 `domain.expected_dates` 决定，不由输入排列或执行顺序决定。

**验证阶段**：X16。

**授权解释**：跨目录身份是同一身份，不产生新的"授权副本"。

### AC-15 产物字节可复现与重执行校验

**输入变化**：

1. 对同一输入连续执行两次（同一进程、同一 cwd）；
2. 在另一个进程中执行一次；
3. 对产物做 `execution_artifact_to_canonical_dict` -> 重新构造 -> 再序列化（往返）。

**预期输出**：

```text
twice.serialize_bytes_equal      = True
twice.artifact_digest_equal      = True
cross_process.bytes_equal        = True      # 同一 numeric_runtime 下
roundtrip.canonical_dict_equal   = True
roundtrip.artifact_digest_equal  = True
roundtrip.bytes_equal            = True
validate_execution_artifact(artifact, ...) = 通过（V1..V4）
```

**关键断言**：

1. 同一输入 + 同一 `numeric_runtime` 下逐字节可复现；跨 numpy/BLAS 版本**不作保证**，
   但产物记录了 `method_configuration.numeric_runtime`（实测环境为 `2.5.3`），
   因此"不一致"是可检测的事实而不是不可解释的漂移；
2. `validate_execution_artifact` 必须重新跑 X2 与 X3 并逐字节比较，不能只比 `artifact_digest` 字符串；
3. 重复执行不得消耗额外随机性：RNG 只由计划冻结的 `seed` + `PCG64` 决定；
4. `execution_artifact_to_canonical_dict` 必须返回**独立副本**：修改返回值不得影响产物，
   也不得影响后续序列化结果。

**验证阶段**：V1–V4。

**授权解释**：可复现性是产物可被独立复核的前提，与授权无关，但缺了它复核不可能成立。

### AC-17 显式合成来源标记与禁止内容

**输入变化**：不改变输入，只检查产物的来源与内容约束。

**预期输出**：

```text
provenance.provenance_class       == "SYNTHETIC_TEST_ONLY"
provenance.synthetic_test_only    is True
provenance.dataset_mode           == "SYNTHETIC"
provenance.real_data_used         is False
provenance.holdout_accessed       is False
execution_authorized              is False
evidence.interpretation_boundary  == 设计第 10.5 节冻结字面量（逐字相同）
payload 中不存在 FORBIDDEN_KEYS 中的任何键名
payload 的任何字符串值都不匹配绝对路径模式（Windows 盘符路径 / POSIX 绝对路径）
payload 中不出现 worktree 路径、主机名、用户名、会话标识或环境变量值
```

**关键断言**：

1. 序列化器必须**主动拒绝**命中的载荷（`FORBIDDEN_ARTIFACT_CONTENT`），而不是仅仅"没有出现"；
2. 禁止键名集合包含挑选类键（`best`/`selected`/`winner`/`aggregate`/`ranking`），
   因此"最佳结果"在结构上无法被表达；
3. 解释边界字面量是产物身份的组成部分（进入 `artifact_digest`）；
4. 任何把 `provenance_class` 改成其它值、或把 `synthetic_test_only` 改成 `False` 的产物都不能
   被 `serialize_*` 接受（`INVALID_INPUT_STRUCTURE`）；
5. 产物**不得**被声明为 estimability / significance / 经济有效性 / 可交易性 / A 股机制结论。

**验证阶段**：X16。

**授权解释**：合成来源是显式身份字段，不能被静默升级为真实研究证据。

### AC-18 两层身份：上游规范十进制 vs 产物 float64 输出

**输入变化**：不改变输入，只断言两层身份的绑定对象不同（设计第 6.2、10.4 节）。

| 子案例 | 断言 | 预期结果 | 阶段 |
| --- | --- | --- | --- |
| 18a | 执行前后 `serialize_matrix(matrix)` / `matrix_digest` / `plan_digest` 逐字节不变 | 相等：执行层不向上游写回任何 float64 | X16 |
| 18b | **主产物** `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` 中每个数值字段都是 `Float64ValueV1`（含 `float64_hex`） | 无裸 float、无 `null` 之外的缺省 | X16 |
| 18c | 改动单个系数的 `float64_hex`（保留 `canonical_decimal`）并重算摘要 | 主产物 `artifact_digest` 改变；不改摘要则 `ARTIFACT_DIGEST_MISMATCH` | V1 |
| 18d | 构造 `-0.0` 与 `0.0` 两个端点的主产物 | `evidence.disposition` 相同（都判"包含零"），但主产物身份不同 | X15 / V1 |
| 18e | 检查 `method_configuration.numeric_runtime` 是否进入**主产物**摘要 | 进入：改动它必须改变 `artifact_digest` | V1 |
| 18f | 断言 `RobustnessArtifactV1` 的 schema 中**不存在** `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` 块，也不存在任何 float64 统计字段 | 结构断言通过；`statistics_computed is False`；其 `artifact_digest` **不绑定、也不声称绑定** float 统计输出 | 结构 / R9 / V1 |
| 18g | 派遣产物摘要**必须**绑定的内容逐项进入身份：完整 source chain、`dispatch.requested_ids`（请求顺序）、`dispatch.registered_ids`（注册顺序）、`entries[*].method_id`、完整 canonical `parameters`（含未知嵌套 `window`）、`provenance`、代码/schema/`numeric_runtime` | 分别改动其中任一项（含请求顺序倒置、`window` 嵌套元素变异、`method_id` 变异）都必须改变 `artifact_digest`；两处都不存在 float64 统计输出可改 | R9 / V1 |

**关键断言**：

1. **两层不得互相否定，且第二层按产物种类分别绑定**：上游六个摘要只绑定规范十进制与摘要
   （float64 永不进入上游身份）；**主产物** `artifact_digest` **必须**绑定 float64 统计输出的
   规范化渲染（`float64_hex` + `canonical_decimal`），否则"改系数不改摘要"能通过校验；
   **注册稳健性派遣产物**的 `artifact_digest` 绑定的是来源链、请求顺序与注册顺序、
   `method_id`、完整 canonical `parameters`、`provenance` 与代码/schema/runtime——
   它 `statistics_computed = False`，**没有** `estimator` / `bootstrap` /
   `conditional_descriptives` / `evidence` 块，因此**不存在** float 统计输出可绑定。
   "派遣产物绑定 float 输出"是错误陈述，"派遣产物绑定不存在的 float blocks"同样是错误陈述；
2. `float64_hex` 与 `canonical_decimal` 的一致性校验只验证"二者来自同一 float64 值"
   （`float.fromhex(float64_hex) == 原值`），**不是**要求两个字符串相等；
   `"-0x0.0p+0"` 与 `"0"` 是合法的同一对；
3. 判定只使用 float64 值与 `float64_hex`，`canonical_decimal` 只用于人读；`canonical_decimal`
   是 `repr` 派生的**最短 round-trip 十进制伴随渲染**（位数随取值变化，**不存在固定 17 位**），
   精确二进制身份由 `float64_hex` 保留；`0.0` 与 `-0.0` 的 `canonical_decimal` 同为 `"0"`
   而 `float64_hex` 不同，因此**这个符号差异只体现在主产物身份上**；
4. 执行层不得把 float64 结果回灌进矩阵、数据集、合同或计划，也不得"修复"任何单元格。

**验证阶段**：X16 / V1。

**授权解释**：主产物身份绑定"本产物自己算出的数值"，上游身份绑定"输入的规范十进制文本"；
两者单向相连，因此产物可复算且不可被篡改成另一份证据。派遣产物**没有**算出的数值，
它绑定的是"被完整、不可变转发的注册请求与参数"——把它的绑定内容写成 float 块，等于宣称
本阶段执行了稳健性统计，而它 `statistics_computed = False`。

### AC-19 `bootstrap.enabled` 严格复制计划声明

**输入变化**：三组计划状态 + 一组诱导失败。

| 子案例 | 计划 `bootstrap_plan` | 预期结果 | 阶段 |
| --- | --- | --- | --- |
| 19a | 基础 fixture（`enabled=true`、`MOVING_BLOCK_BOOTSTRAP_V1`、`replications=1000`、`seed=42`） | 产物 `bootstrap.enabled is True` 且端点非 `None`；`method_configuration.bootstrap_enabled is True` | X11–X13 |
| 19b | `enabled=false`、`method_id="DISABLED"`（既有 A.2I 已实测可编译） | 产物 `bootstrap.enabled is False`，端点全为显式 `null`；处置 `INCONCLUSIVE`/`BOOTSTRAP_DISABLED` | X11–X13 + D2 |
| 19c | `enabled=true` 但 `method_id="DISABLED"` 或 `enabled=false` 但非 `DISABLED` | 计划层 `HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")` 原样传播，执行层不得放宽 | 计划编译 / X2 |
| 19d | `enabled=true` 且 `replications=1`（诱导 bootstrap 失败） | `ExecutionError("INSUFFICIENT_REPLICATIONS")`，**不产出任何产物**；不得降级为 `enabled=false` 的无区间产物 | X11 |

**关键断言**：

1. 产物 `bootstrap.enabled` **只可能**是 `plan.bootstrap_plan.enabled` 的严格复制，
   不得重新推导、不得因失败而改写；`None` 不再是合法取值；
2. 计划启用时的任何 bootstrap 失败（方法/RNG/重复数/块长/重采样秩/有限性）都让**整个执行**
   fail-closed，**不存在**"先按 disabled 出一个无区间产物"的运行时降级路径；
3. `enabled=True` 时方法相关字段必须全部非 `None`；`enabled=False` 时必须全部为 `None`；
4. 计划层已保证 `enabled` 与 `method_id` 一致，执行层不得放宽该配对，也不得发明第三种组合；
5. 19d 是"未授权运行时降级"的直接反例：失败必须暴露，不得被静默改写成一个更弱的产物。

**验证阶段**：X11 / X16。

**授权解释**：`enabled` 是计划冻结声明的一部分；执行层改写它就是在没有授权的情况下
改变研究设计，因此该降级在结构上不可表达。

## 6. 文档阶段实际执行的验证（非执行实现测试）

本阶段**没有**执行器产品实现，因此只运行既有 adapter / matrix / plan / contract / 保护门回归，
外加一次性只读探针（不含任何统计计算）。实际命令、退出码与结果记录在
[工作记录](../agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md) 与
[验收文档](../acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md) 中。

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py
```

## 7. 实现阶段的验收顺序要求

实现（另立 Goal、另获授权）时必须：

1. **先复现全部负例**（AC-02 至 AC-07、AC-11 至 AC-13、AC-16、AC-17、AC-18c/18d/18e/18f、AC-19c/19d）确认门禁真的拒绝；
2. 再实现正例（AC-01、AC-08、AC-10、AC-12a/12b/12f、AC-14、AC-15、AC-18a/18b/18g、AC-19a/19b）；
3. 负例必须在**未实现**状态下先确认"当前没有对应 API"或"当前实现会错误放行"，
   不允许为了让测试变绿而放宽门禁；
4. 不得新增镜像式测试来替代真实最小实现验证；
5. 本清单不含任何数值期望（设计阶段禁止计算系数与区间）；实现落地后产出的首批数值必须由
   独立复核确认，并先判断"实现偏离冻结契约"还是"设计需修订"，不得直接改期望值；
6. 秩门、来源门、方法允许列表、holdout 门、注册派遣门与内容禁止项六者缺一不可，
   且保持设计第 11 节的冻结顺序。

## 8. 边界声明

- 本清单**不构成**实现授权、统计执行授权、真实数据授权、holdout 授权或 M4-B 授权。
- 有界执行就绪只表示"来源已验证 + 映射与数值边界就绪 + 产物可复现"，不表示任何统计性质。
- 处置词只在 `synthetic_test_only` 产物内部有效，不得升级为 A 股机制结论。
- 合成来源证据不得升级为真实研究证据。
