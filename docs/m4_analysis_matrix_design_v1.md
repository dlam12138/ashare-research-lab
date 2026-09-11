# M4 合成分析矩阵设计 v1

状态：DESIGN_ONLY / READY_FOR_IMPLEMENTATION_REVIEW。本文是 synthetic analysis
matrix preparation 的设计规范与拟议接口契约，尚未实现。文中的类名、函数名、字段名和
错误码全部标记为**拟议 API**，不冒充现有实现，也不表示本阶段获得任何实现或执行授权。

基线：工作树 `D:/量化分析-m4-matrix-design`，分支 `codex/m4-analysis-matrix-design`，
HEAD `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`（与 origin 及实时远端一致）。
`main` 为 `bab24f981fef9336b84280544ce709702b9df116`。PR #11 仍未合并。

依赖并保持冻结的既有设计：

- [M4 数据适配器设计 v1](m4_dataset_adapter_design_v1.md)
- [M4 数据适配器合成验收场景 v1](m4_dataset_adapter_acceptance_cases_v1.md)
- 既有 Goal `agent/goals/2026-09-10_m4_analysis_matrix_design.md`（本文不覆盖、不改写）
- 首阶段任务契约 `D:/量化分析/agent/goals/2026-09-10_ds_matrix_design_closeout.md`

## 1. 目标、范围与非目标

### 1.1 目标

把已通过 `validate_dataset(preparation, contract, plan, bound_inputs)` 来源验证的
`DatasetPreparationV1`，按**同一计划**的 `design_plan.ordered_terms` 投影为一张日频设计
矩阵，并给出：

1. 唯一的列顺序来源（计划，而非固定开发期或固定 M3 列表）；
2. 规范十进制数值身份（不以 float 作为身份边界）；
3. 不可变输出、独立副本、确定性摘要与序列化；
4. 明确的失败语义，包括质量拒绝时不存在可绕过的部分矩阵；
5. 矩阵准备与满秩/可估计/统计显著/可交易/执行授权之间的硬边界。

### 1.2 非目标（本设计不授权）

- 不实现任何产品代码；本文只冻结接口、字段与失败语义。实现需另立 Goal 并获用户授权。
- 不修改 A.1 合同 schema、A.2 计划 schema、dataset preparation schema、既有摘要算法、
  既有测试、既有冻结研究产物或保护哈希。
- 不做真实数据适配、不访问 provider、不打开数据库、不读取真实行情。
- 不调用或复用 M3 的回归、bootstrap、robustness、evidence 路径；不执行 holdout；不进入 M4-B。
- 不计算回归、系数、p 值、标准误、秩、条件数、bootstrap 区间或 evidence 判定。
- 不执行任何统计研究，不产生研究结论，不构成执行授权。

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| preparation | 现有 `DatasetPreparationV1`，由现有四参数适配器产出 |
| plan | 现有 `DeterministicAnalysisPlan`（A.2I） |
| matrix | 本设计新增的 `MatrixPreparationV1`（拟议） |
| term_role | 计划 `ordered_terms[*].term_role`，列的权威名称 |
| role_order | preparation 的 `role_order`，列的取值来源顺序 |

## 2. 已验证基线与来源绑定

### 2.1 输入身份链

矩阵准备不引入新的来源概念，只**继承并暴露**已有身份：

```text
config --compile_hypothesis_config--> contract.contract_digest
contract --build_analysis_plan--> plan.plan_digest
(contract, plan, bound_inputs) --materialize_analysis_dataset--> preparation.{input_digest, domain_digest, dataset_digest}
(preparation, contract, plan, bound_inputs) --materialize_design_matrix--> matrix.{..., source_contract_digest, plan_digest, input_digest, domain_digest, dataset_digest, matrix_digest}
```

即：矩阵没有自己的来源概念。唯一的对外材料化入口
`materialize_design_matrix(preparation, contract, plan, bound_inputs)` **必须**先执行四参数
`validate_dataset`，再做质量门检查与投影；矩阵层不提供任何"只吃 `preparation`"的公开入口。

### 2.2 来源验证入口是既有四参数接口

`validate_dataset(preparation, contract, plan, bound_inputs)` 是**唯一**来源验证前提。其
现有实现重新 materialize 并比较 `serialize_dataset` 字节；因此：

- 只检查 `preparation.dataset_digest` 字符串形状**不能**证明来源；
- 只调用 `serialize_dataset(preparation)` **不能**证明来源；
- serializer 的内部一致性检查**不能**替代四参数入口。

本设计因此规定：矩阵准备与矩阵验证都必须能访问原始 `contract, plan, bound_inputs`，并
在任何投影工作之前先调用四参数 `validate_dataset`。

`validate_dataset` 的实现口径（真实代码，`datasets/synthetic.py`）：

```text
expected = materialize_analysis_dataset(contract, plan, bound_inputs)
if serialize_dataset(preparation) != serialize_dataset(expected):  -> IDENTITY_CONFLICT
```

即：**重新 materialize 并逐字节比较规范序列化结果**。矩阵层不得用任何更弱的检查替换它。

### 2.3 `serialize_dataset` 不是来源门禁（实测边界）

已有实现允许一个"内部自洽但被篡改"的 preparation 通过 `serialize_dataset`，只有四参数
入口能拒绝它。本轮在真实代码上实测（见第 7.8 节复算）：把基础 fixture 的
`complete_rows` 的 `condition_indicator` 全部取反、重算 `dataset_digest` 后，

```text
tampered.dataset_digest = 721584843f0f10448b0e1aecc28cc30a52018844be4c5852923c0acdab57b79f  （≠ 原始）
serialize_dataset(tampered)          -> ACCEPTED（内部自洽，无异常）
validate_dataset(tampered, ...)      -> IDENTITY_CONFLICT
```

这不是缺陷，而是分工：serializer 负责输出结构与自一致性，四参数入口负责来源绑定。

### 2.4 适配器已固定的质量语义（矩阵必须继承）

- `status` 只有 `READY_SYNTHETIC` / `REJECTED_QUALITY` 两种；
- 仅 `READY_SYNTHETIC` 有 `complete_rows`；`REJECTED_QUALITY` 的 `complete_rows` 恒为空元组；
- `coverage_denominator` 恒等于 `len(domain.expected_dates)`，即 N 个预期交易日的全域分母；
  任何缺口都不缩小分母；
- `coverage_numerator` 恒等于 `len(complete_rows)`，即"全部角色当日有效"的完整行数；
- `complete_rows` 的元素形状固定为 `(trade_date, values, condition_indicator)`，
  `values` 按 `role_order` 排列，`condition_indicator` 为严格 `int` `0`/`1`；
- `reason_counts` 内部为 `tuple[tuple[str, int], ...]`（按原因名排序），
  `rejected_dates` 为按日期序的 `tuple[str, ...]`；
- `failure_disposition` 原样取自 `contract.evidence_rule.data_quality_failure_disposition`，
  在既有 fixture 中为 `INCONCLUSIVE`；
- `execution_authorized` 恒为 `False`；
- 覆盖率比较使用 `Decimal` 精确整数运算 `n*q >= d*p`（`gate = p/q`），不使用显示百分比。
- 指示值取 `int(factor <op> threshold)`，其中 factor 与阈值都是 `Decimal`，**不做浮点容差**。

矩阵层不重新判断质量，也不"修复"质量：它只消费 `complete_rows`，并把
`status`、`n/N`、`reason_counts`、`rejected_dates` 原样带入自己的身份。

## 3. 列映射规范（本设计的核心冻结项）

### 3.1 列顺序只来自计划

权威来源是 `plan.design_plan.ordered_terms`（A.2I 编译器机械生成，并由
`validate_analysis_plan` 逐项校验）。矩阵列必须按 `position` 升序取 `term_role`：

```text
position 1 : INTERCEPT
position 2 : FACTOR_CONTINUOUS
position 3..k : 注册顺序的 CONTROL_0001, CONTROL_0002, ...
最后一项   : CONDITION_INDICATOR
```

必须显式断言：

```text
[term_role for term in ordered_terms] ==
    ["INTERCEPT", "FACTOR_CONTINUOUS",
     *(role for role in preparation.role_order if role.startswith("CONTROL_")),
     "CONDITION_INDICATOR"]
```

该断言失败即 `PLAN_TERM_ROLE_MISMATCH`。**不得**使用固定 M3 列表（例如
`analysis_dataset.ANALYSIS_COLUMNS`）、固定开发期、固定控制项数量或按字母排序来构造列。

计划由编译器机械生成，因此断言恒成立；断言存在的意义不是"预期它会失败"，而是把
"列顺序只能来自计划"从约定升级为**实现必须执行的运行时门禁**：一旦未来的计划形状、
控制注册或角色命名发生变化，矩阵层必须显式拒绝，而不是静默产出错位矩阵。

### 3.2 取值只能按 `term_role` 分派（不得按 `source_series_role`）

`term_role` 是矩阵列的**语义身份**，也是**投影规则的权威标识**：它来自计划的
`ordered_terms`，在计划内唯一、完备、顺序确定，并且正是第 3.1 节断言与
`validate_analysis_plan` 校验的对象。`source_series_role` 只表达该列的**输入来源**（绑定到
哪个上游序列或角色），它本身无法说明该列应当如何取值——是取常量 `1`、直接从
`complete_rows[*].values` 取值，还是取 `complete_rows[*].condition_indicator` 的派生值。
因此分派键必须是 `term_role`。真实编译器 `mechanism/planning/compiler.py::_terms` 与
`tests/test_m4_stage4a2i_analysis_plan.py` 给出的绑定关系（第 7.1 节原始输出复核）是：

- `INTERCEPT`：`source_series_role = null`——截距列不对应任何序列；`null` 在
  `role_order`/`values` 中没有可解析的取值位置，而它的投影规则（字面量 `"1"`）也不在来源
  信息里；
- `FACTOR_CONTINUOUS`：`source_series_role = "FACTOR"`——与 `term_role` **不同名**，连续因子
  列的来源是 `role_order` 中的 `FACTOR` 序列；
- `CONTROL_00nn`：`source_series_role` 恰好等于自身角色名——这是控制项按注册顺序命名的
  结果；名称相同只是命名结果，不构成"来源角色即列语义"的一般规则；
- `CONDITION_INDICATOR`：`source_series_role = "CONDITION_INDICATOR"`，但该名字是 transform
  plan 的**输出角色**，不是 `role_order` 成员（基础 fixture 的 `role_order` 为
  `("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002")`）；指示值来自
  `complete_rows[*].condition_indicator` 这个独立元素，**不在** `values` 中。因此"按
  `source_series_role` 建字典、再从 `role_order`/`values` 取值"在截距列与指示列上都解析不出
  正确来源：截距的来源是 `null`，指示列的来源角色不是任何序列角色。

也就是说：`term_role` 决定"这一列在矩阵里是什么、该怎么取值"，`source_series_role` 只说明
"它的输入序列叫什么"。就当前 `ordered_terms` 集合而言，`term_role → source_series_role`
的取值（`null`、`FACTOR`、`CONTROL_0001`、`CONTROL_0002`、`CONDITION_INDICATOR`）两两不同，
恰好是一一映射；但该一一映射是当前角色命名的结果，不是投影契约的一部分，也不是取值依据——
投影规则由 `term_role` 的语义给出，不能从 `source_series_role` 反推。分派规则必须且只能按
`term_role`：

| 条件（`term_role`） | 单元格取值 | 备注 |
| --- | --- | --- |
| `INTERCEPT` | 字面量 `"1"` | 规范十进制表示，`source_series_role` 为 `null`，不读取任何角色 |
| `FACTOR_CONTINUOUS` | `role_order` 中 `FACTOR` 位序的 `complete_rows[*].values` 元素 | 来源绑定是 `"FACTOR"`，列语义名是 `FACTOR_CONTINUOUS` |
| `CONTROL_0001`…`CONTROL_00nn` | 同名角色在 `values` 中的元素 | 顺序即合同 controls 注册顺序 |
| `CONDITION_INDICATOR` | `complete_rows[*].condition_indicator` 的严格 `int` `0`/`1`，格式化为 `"0"`/`"1"` | 不在 `values` 中；来源角色是 transform 输出角色，不是序列角色 |

未知 `term_role` 一律 `UNSUPPORTED_TERM_ROLE`，不猜测、不忽略该列、不补零。

`INTERCEPT` 的规范表示冻结为字符串 `"1"`；它由常量产生，不从数据读取，也不受
`true_value`/`false_value` 影响。

### 3.3 目标向量与响应角色

`response_role` 必须等于 `plan.design_plan.response_role`（当前恒为 `"TARGET_OUTCOME"`），
且必须是 `preparation.role_order` 的成员。目标向量按 `complete_rows` 的行顺序取
`values[role_order.index(response_role)]`，并且**不进入矩阵列**。不相等或缺失即
`PLAN_TERM_ROLE_MISMATCH`。

### 3.4 无 controls 与多 controls

- 无 controls：`role_order == ("TARGET_OUTCOME", "FACTOR")`，`ordered_terms` 长度为 3，
  矩阵为 3 列（`INTERCEPT`、`FACTOR_CONTINUOUS`、`CONDITION_INDICATOR`）。
- 多 controls：控制列数量必须与计划一致；控制越多列越多。

计划由合同机械编译，因此更换控制顺序会同时改变 `contract_digest`、`plan_digest`、
`role_order`（永远重新编号为 `CONTROL_0001…`）与 `column_roles`。矩阵**不得**把顺序排
回去，也不得因为 series 同名或同值而合并列。

### 3.5 行顺序

行严格按 `preparation.complete_rows` 的既有顺序，即 `domain.expected_dates` 的字典序，
对 ISO `YYYY-MM-DD` 而言即时间序。矩阵层**不得**过滤、重排、去重或补齐行。行数必须等于
`len(preparation.complete_rows)`。

### 3.6 数值身份：规范十进制，不以 float 为边界

- 输入侧：现有适配器已用 `_dec` 强制规范形式（`Decimal` 有限、无多余零、无 `-0`、
  无 `0.0100`、无 `1E-2`）。矩阵层**不重新解析、不四舍五入、不格式化、不转换为 float**。
- 输出侧：每个单元格都是**规范十进制字符串**；`INTERCEPT` 为 `"1"`；条件指示列为
  `"0"`/`"1"`（由严格 `int` 格式化，`type(indicator) is int` 且 `isinstance(x, bool)` 为假
  才接受，`True`/`False` 是结构错误 `INVALID_INPUT_STRUCTURE`）。
- 因此 `matrix_digest`、`serialize_matrix` 与全部等价性判断都在十进制字符串上进行，
  float 只可能出现在未来执行器内部，且不得回流为本设计的身份。

### 3.7 矩阵准备与估计/执行硬隔离

矩阵准备成功**不**声明任何下列性质：满秩、可识别、可估计、条件数良好、系数可解释、
统计显著、经济显著、可交易、通过 evidence 规则、获得执行授权。矩阵层：

- 不计算秩、条件数、标准误、VIF、系数、p 值、置信区间；
- 不调用 `mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`；
- 不读取 holdout；`holdout_boundary.execution_authorized` 在计划中恒为 `False`，矩阵层
  再暴露一个恒为 `False` 的 `execution_authorized`，两者都不得被本设计升级；
- 不把"矩阵准备成功"（即 `quality.status == "READY_SYNTHETIC"` 且返回了矩阵对象）
  解释为统计有效性或执行授权。

## 4. 拟议数据结构

以下全部为**拟议 API**。字段名、顺序与类型在此冻结，实现者不得猜测、不得增删字段、
不得放宽运行时类型。

### 4.1 错误类型

```text
class MatrixError(ValueError):     # 拟议
    code: str                      # 稳定机器可读错误码
    message: str | None
```

说明（本轮冻结，不再留给实现者猜测）：

- 矩阵层**会**调用现有四参数 `validate_dataset`，因此上游 `AdapterError` 可能从矩阵入口
  抛出。上游错误**原样传播**：不包装、不改码、不吞掉、不替换成矩阵错误。来源层的
  `INPUT_DIGEST_MISMATCH`、`CONTRACT_PLAN_MISMATCH`、`EVIDENCE_DIGEST_MISMATCH`、
  `UNSUPPORTED_MODE`、`OUT_OF_DOMAIN`、`DUPLICATE_OBSERVATION`、`ROLE_BINDING_MISMATCH`、
  `INVALID_DATE`、`INVALID_VALUE`、上游 `IDENTITY_CONFLICT`/`INVALID_INPUT_STRUCTURE` 等
  全部保持 `AdapterError` 类型与 `.code` 不变。
- `MatrixError` 只承载**矩阵投影层**自身的失败：矩阵对象结构、列/行不变量、自摘要、
  与原始输入重投影后的逐字节不一致，以及质量门 `DATASET_NOT_READY`。
- 两个错误族存在同名码（`IDENTITY_CONFLICT`、`INVALID_INPUT_STRUCTURE`）。这是刻意的：
  同名同义、按**类型 + 阶段**可区分——`AdapterError` 表示"来源验证失败"，
  `MatrixError` 表示"矩阵内容失败"。调用方按 `.code` 分派时对同名码作同一处理即可，
  但验收必须断言类型，避免把"来源被篡改"和"矩阵被篡改"混为一谈。
- 是否改用独立错误类型属于实现评审项；无论选哪种，都不得在实现中静默改变上述语义。

### 4.2 嵌套类型

```text
@dataclass(frozen=True)
class MatrixColumnV1:              # 拟议
    position: int                  # 1-based，等于 term.position
    term_role: str                 # INTERCEPT / FACTOR_CONTINUOUS / CONTROL_00nn / CONDITION_INDICATOR
    coefficient_role: str          # 原样取自计划，例如 alpha / beta_factor / beta_control_0001 / gamma_condition
    source_role: str | None        # 审计/来源元数据（进入规范载荷与摘要，须与计划一致，不参与取值分派）：INTERCEPT 为 None，FACTOR_CONTINUOUS 为 "FACTOR"，其余为自身角色

@dataclass(frozen=True)
class MatrixRowV1:                 # 拟议
    trade_date: str                # 规范 YYYY-MM-DD
    cells: tuple[str, ...]         # 长度等于列数；全部规范十进制字符串

@dataclass(frozen=True)
class MatrixQualityV1:             # 拟议，继承而非重判
    status: str                    # 显式继承 preparation.status（DatasetPreparationV1 的顶层字段）
    coverage_numerator: int        # 以下七个字段逐字段复制 preparation.quality（QualityReportV1）
    coverage_denominator: int
    coverage_gate: str             # 规范十进制字符串
    missingness_policy: str
    failure_disposition: str
    reason_counts: tuple[tuple[str, int], ...]
    rejected_dates: tuple[str, ...]
```

`MatrixQualityV1` 是"继承而非重判"的显式结果：`status` **显式继承** `preparation.status`
（`DatasetPreparationV1` 的顶层字段），其余七个字段（`coverage_numerator`、
`coverage_denominator`、`coverage_gate`、`missingness_policy`、`failure_disposition`、
`reason_counts`、`rejected_dates`）逐字段复制 `preparation.quality`（`QualityReportV1`）的
同名字段，不重命名、不重算、不重新判定。严格地说，`QualityReportV1` **不含** `status`：
`status` 属于 `DatasetPreparationV1`。矩阵把 preparation 的顶层 `status` 纳入自己的
`quality` 块，理由是矩阵规范载荷不设独立的顶层 `status` 字段（第 6.5 节约束 3），而就绪/
拒绝状态必须与质量明细一起、在唯一且不可能与第二个状态字段矛盾的位置被下游读到：`status`
与 `preparation.quality` 的七个字段属于同一个质量结论，放在同一嵌套对象里才能让下游以单一
对象读取该结论。矩阵层不新增状态词表（仍只有 `READY_SYNTHETIC` / `REJECTED_QUALITY`），
也不把该字段当作重新判定。规范字典中 `reason_counts` 必须转成 JSON 对象（`{k: v}`，键序由
规范 JSON 排序键决定），因为 JSON 没有元组类型；这是唯一的表示差异。

`source_role` 是**审计/来源元数据**字段（记录该列绑定的来源序列名，`INTERCEPT` 为 `None`）：
它进入规范载荷、序列化字节与 `matrix_digest`，并且必须与计划的 `source_series_role` 一致，
因此属于被冻结的身份内容，不是纯展示字段。它**不参与单元格取值分派**；取值分派只按第 3.2 节
的 `term_role` 表。`source_series_role` 只表达输入来源，无法单独说明该列取常量 `1`、直接取
`values` 还是取 `condition_indicator`：`INTERCEPT` 的 `source_series_role` 为 `null`，指示列
指向不在 `role_order`/`values` 的 transform 输出角色，因此不得据其建表。

### 4.3 顶层输出

```text
@dataclass(frozen=True)
class MatrixPreparationV1:         # 拟议
    matrix_schema_version: str     # 固定 "M4_DESIGN_MATRIX_V1"
    builder_version: str           # 固定 "M4_DAILY_CONDITIONAL_DESIGN_MATRIX_V1"
    source_contract_digest: str    # 继承 preparation.source_contract_digest
    plan_digest: str               # 继承 preparation.plan_digest
    input_digest: str              # 继承 preparation.input_digest
    domain_digest: str             # 继承 preparation.domain_digest
    dataset_digest: str            # 继承 preparation.dataset_digest
    role_order: tuple[str, ...]    # 继承 preparation.role_order
    columns: tuple[MatrixColumnV1, ...]
    response_role: str             # 等于 plan.design_plan.response_role
    rows: tuple[MatrixRowV1, ...]
    quality: MatrixQualityV1
    execution_authorized: bool     # 恒为 False
    statistics_computed: bool      # 恒为 False
    matrix_digest: str             # 自身内容摘要，排除本字段
```

`statistics_computed` 是显式的否定声明字段，用于让下游无法把"矩阵准备成功"误读为"统计
已执行"。两个布尔字段都必须是严格 `bool` 且恒为 `False`；其他取值是结构错误。

### 4.4 不变量（构造即校验，非法即拒绝）

1. `matrix_schema_version`、`builder_version` 精确等于固定常量。
2. 五个摘要字段均为 64 位小写十六进制。
3. `columns` 非空，`position` 为从 1 起的连续整数。
4. `[c.term_role for c in columns]` 精确等于第 3.1 节断言序列；
   `[c.coefficient_role]` 与计划一致。
5. `response_role` 在 `role_order` 中；`row_order` 见第 3.5 节。
6. 每行 `cells` 长度等于 `len(columns)`；每个单元格是规范十进制字符串。
7. `quality.status` 与 `preparation.status` 一致（显式继承，不是重新判定）；
   `quality.coverage_denominator` 等于 `len(preparation.audit_rows)`。
8. `quality.status == "READY_SYNTHETIC"` 当且仅当 `len(rows) > 0`；
   `quality.status == "REJECTED_QUALITY"` 时 `rows` 必须为空元组。反向也成立：
   只要 `quality.status == "REJECTED_QUALITY"`，矩阵层已经在第 5.2 节共享投影管线第 5 步
   （质量边界）拒绝，因此**不存在**"有行但被拒绝"或"被拒绝但有行"的中间对象。
9. 两个 `bool` 字段恒为 `False`。
10. `matrix_digest` 等于 `canonical_digest(payload)`，其中 `payload` 是
    `matrix_to_canonical_dict(matrix)` 删除 `matrix_digest` 自身后的字典；
    即与 `dataset_digest` 完全同构的算法（第 6.3 节）。

## 5. 拟议公开接口与失败语义

### 5.1 签名（本轮重新冻结）

```text
# 拟议公开 API（只有这四个入口）
materialize_design_matrix(preparation, contract, plan, bound_inputs) -> MatrixPreparationV1
matrix_to_canonical_dict(matrix) -> dict                # 独立副本
serialize_matrix(matrix) -> bytes                       # 规范字节
validate_design_matrix(matrix, preparation, contract, plan, bound_inputs) -> None

# 拟议私有实现细节（非公开 API、非验收入口、不导出）
_project_validated_matrix(preparation, plan) -> MatrixPreparationV1
```

- **唯一的对外材料化入口**是四参数 `materialize_design_matrix(preparation, contract, plan,
  bound_inputs)`。它按固定顺序执行：① `validate_dataset(preparation, contract, plan,
  bound_inputs)` 来源验证（上游 `AdapterError` 原样传播）；② 质量门，`status !=
  "READY_SYNTHETIC"` 或 `complete_rows` 为空即 `MatrixError("DATASET_NOT_READY")`；
  ③ 投影（内部调用 `_project_validated_matrix`）。**没有**先于来源验证的公开材料化路径，
  也没有只吃 `preparation` 的公开重载。
- `_project_validated_matrix(preparation, plan)` 是**私有实现细节**：它假定调用方已经完成
  四参数来源验证，只做结构校验、质量门、列映射与逐格投影，不做来源验证、不接受
  `contract`/`bound_inputs`、不导出、不构成任何 API 或验收入口。它存在的唯一理由是让
  材料化入口与 `validate_design_matrix` 的重投影共享同一段确定性投影代码，避免两处实现
  漂移。把 `preparation` 直接交给它属于实现内部调用，调用方不得据此绕过门禁。
- `materialize_design_matrix` 与 `_project_validated_matrix` 都不做 IO、不访问路径、环境、
  时间、随机数、provider、数据库或统计库。
- `validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)` 必须重新执行
  完整来源验证并重投影，然后逐字节比较 `serialize_matrix(matrix)` 与由原始输入重新得到的
  字节；矩阵内容不一致即 `MatrixError("IDENTITY_CONFLICT")`。它因此**必须**拥有
  `preparation` 参数（`validate_dataset` 的第一个参数）；只比较 `matrix_digest` 字符串
  不足以通过。

只吃 `preparation` 的两参数重载**不存在**，也不再作为拟议 API 出现：它会让调用方在缺少
`contract`/`plan`/`bound_inputs` 的情况下拿到一个未经来源验证的矩阵对象，正是本设计要
封死的门禁旁路。

两个公开入口在 `REJECTED_QUALITY` 上的行为必须一致且平凡明确：

| 入口 | 输入 | `REJECTED_QUALITY` 时的行为 |
| --- | --- | --- |
| `materialize_design_matrix(preparation, contract, plan, bound_inputs)` | 原始输入齐备 | ①`validate_dataset` 先通过（合法的拒绝态 preparation 与原始输入逐字节一致），②质量门随即抛 `MatrixError("DATASET_NOT_READY")`；不投影、不返回对象 |
| `validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)` | 矩阵 + 其声称的原始输入 | 同一顺序：①矩阵结构不变量，②`validate_dataset`，③重投影在质量门抛 `MatrixError("DATASET_NOT_READY")`。拒绝态下**不存在**合法的矩阵对象，因此本入口在该状态下没有可构造的验收输入，也**不把任何伪造的"拒绝态矩阵"当作必需输入或可接受输入** |

即：**矩阵层没有任何 API 能在质量拒绝时返回一个对象**——既没有 0 行的"空矩阵"，也没有
2 行的"部分矩阵"。拒绝态只以异常存在，因而不可能被下游当作输入继续使用。验收层面，
`REJECTED_QUALITY` 只需断言 `materialize_design_matrix(...)` 抛 `DATASET_NOT_READY`
且无对象返回；`validate_design_matrix` 在此状态下不需要（也无法）被喂入矩阵对象。

### 5.2 验证顺序（同一入口内按确定顺序，首个错误可复现）

**共享投影管线 `_project_validated_matrix(preparation, plan)`（私有）**，顺序固定：

1. 运行时结构与类型（frozen dataclass、tuple、严格 `bool`/`int`）。
2. 计划结构：`ordered_terms` 存在、`position` 连续、`term_role` 白名单与第 3.1 节断言。
3. `preparation` 结构：`role_order` 非空、`complete_rows` 与 `audit_rows` 形状。
4. `response_role` 解析与 `FACTOR` 位序解析。
5. 质量边界：`preparation.status != "READY_SYNTHETIC"`（含 `REJECTED_QUALITY`）或
   `complete_rows` 为空 → `MatrixError("DATASET_NOT_READY")`，**在此终止，不进入投影**；
   本步骤之前的第 1–4 步已完成，因此拒绝原因不会被结构错误掩盖。
6. 逐行投影与逐格校验（按行序、列序）。
7. 自摘要计算与第 4.4 节不变量 10 的自洽校验（`MATRIX_DIGEST_MISMATCH`）。

**矩阵对象结构校验 M1**（仅 `validate_design_matrix` 有 `matrix` 输入）：检查 `matrix` 的
运行时结构与第 4.4 节全部 10 条不变量；结构不满足 → `MatrixError("INVALID_INPUT_STRUCTURE")`，
自摘要与自身载荷不符 → `MatrixError("MATRIX_DIGEST_MISMATCH")`。该步不依赖任何上游输入，
先于来源验证执行，因此格式错误的矩阵不会被送去序列化比较。

**`materialize_design_matrix(preparation, contract, plan, bound_inputs)` 的顺序**：

- A1. `validate_dataset(preparation, contract, plan, bound_inputs)`；上游 `AdapterError`
  原样抛出（含上游 `IDENTITY_CONFLICT`、`INPUT_DIGEST_MISMATCH`、`CONTRACT_PLAN_MISMATCH`
  等），**在此终止**。
- A2. 执行共享投影管线第 1–7 步；第 5 步质量门抛
  `MatrixError("DATASET_NOT_READY")` 时**在此终止，不进入投影**。

**`validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)` 的顺序**：

- V1. 矩阵结构校验 M1。
- V2. `validate_dataset(preparation, contract, plan, bound_inputs)`（同 A1）；上游失败原样
  抛出并终止。
- V3. `expected = _project_validated_matrix(preparation, plan)`（同 A2）。
- V4. `serialize_matrix(matrix) != serialize_matrix(expected)` →
  `MatrixError("IDENTITY_CONFLICT")`；相等即通过（返回 `None`）。

确定性与可复现性要求：同一输入必须命中同一首个错误；结构错误不得被来源错误或质量错误
掩盖，来源错误不得被矩阵内容错误掩盖（V1 → V2 → V3 → V4 固定顺序）。

### 5.3 失败语义

| 错误族 | 错误码 | 触发条件 | 是否可降级 |
| --- | --- | --- | --- |
| `MatrixError` | `INVALID_INPUT_STRUCTURE` | 矩阵对象类型/shape/布尔陷阱/字段长度不符/增删字段 | 否 |
| `MatrixError` | `DATASET_NOT_READY` | `preparation.status != "READY_SYNTHETIC"` 或 `complete_rows` 为空 | 否 |
| `MatrixError` | `PLAN_TERM_ROLE_MISMATCH` | 列序列不等第 3.1 节断言，或 `response_role` 缺失 | 否 |
| `MatrixError` | `UNSUPPORTED_TERM_ROLE` | `term_role` 不在白名单 | 否 |
| `MatrixError` | `UNSUPPORTED_PLAN_SCHEMA` | `plan.schema_version` 非 `M4_DETERMINISTIC_ANALYSIS_PLAN_V1` | 否 |
| `MatrixError` | `MATRIX_DIGEST_MISMATCH` | 矩阵自摘要与其自身载荷重算不符 | 否 |
| `MatrixError` | `IDENTITY_CONFLICT` | `validate_design_matrix` 中矩阵字节 ≠ 由原始输入重投影的字节 | 否 |
| `AdapterError`（上游） | `IDENTITY_CONFLICT` | `validate_dataset` 重 materialize 后逐字节不一致（来源层） | 否 |
| `AdapterError`（上游） | `INPUT_DIGEST_MISMATCH` | `bound_inputs.input_digest` 与重算不符 | 否 |
| `AdapterError`（上游） | `CONTRACT_PLAN_MISMATCH` | 计划与合同语义不一致 | 否 |
| `AdapterError`（上游） | `EVIDENCE_DIGEST_MISMATCH` | 观察证据与重算不符 | 否 |
| `AdapterError`（上游） | 其余上游码 | `UNSUPPORTED_MODE`、`OUT_OF_DOMAIN`、`DUPLICATE_OBSERVATION`、`ROLE_BINDING_MISMATCH`、`INVALID_DATE`、`INVALID_VALUE`、上游 `INVALID_INPUT_STRUCTURE` 等 | 否 |

硬性语义：**失败不产生部分矩阵**。任何错误都必须抛出，不得返回带空 `rows` 或截断 `rows`
的"部分成功"对象。`REJECTED_QUALITY` 不是"降级成功"，而是 `DATASET_NOT_READY` 的
明确拒绝：没有可绕过的部分执行矩阵。

### 5.4 错误码与既有码的同名说明

- 矩阵层**新增**的错误码（既有适配器中不存在，已对真实 `datasets/synthetic.py` 与
  `planning/compiler.py` 全量 `_fail(...)` 调用核对）：`DATASET_NOT_READY`、
  `PLAN_TERM_ROLE_MISMATCH`、`UNSUPPORTED_TERM_ROLE`、`UNSUPPORTED_PLAN_SCHEMA`、
  `MATRIX_DIGEST_MISMATCH`。
- 与既有适配器**同名**的码：`IDENTITY_CONFLICT`、`INVALID_INPUT_STRUCTURE`。二者语义一致
  （来源/内容不一致、结构非法），但分属两个错误族：上游命中时抛 `AdapterError`，矩阵层
  命中时抛 `MatrixError`。调用方按 `.code` 统一分派即可，验收按类型区分阶段。
- 上游其余码（`INPUT_DIGEST_MISMATCH`、`CONTRACT_PLAN_MISMATCH`、
  `EVIDENCE_DIGEST_MISMATCH`、`UNSUPPORTED_MODE`、`UNSUPPORTED_BINDING_POLICY`、
  `UNSUPPORTED_OUTCOME`、`DUPLICATE_OBSERVATION`、`OUT_OF_DOMAIN`、
  `EMPTY_EXPECTED_DOMAIN`、`ROLE_BINDING_MISMATCH`、`INVALID_DATE`、`INVALID_VALUE`）
  一律原样传播，矩阵层不得改写为上述任一矩阵码。

## 6. 不可变性、独立副本、确定性摘要与序列化

### 6.1 不可变与独立副本

- 全部类型为 `frozen=True` dataclass，嵌套容器为 `tuple`。
- `matrix_to_canonical_dict` 返回**全新** dict/list，不持有 `matrix` 内部引用；调用方修改
  返回值不得影响 `matrix`，也不得影响任何后续序列化结果。
- 构造器只规范化容器与键顺序（排序、`tuple` 化），**不修复**非法日期、数值或缺失证据。

### 6.2 序列化

```text
canonical JSON = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
serialize_matrix(matrix) = (canonical JSON + "\n").encode("utf-8")
```

即与现有 `serialize_dataset`、`serialize_analysis_plan` 相同的规范形：无 BOM、无缩进、
`\n` 结尾恰好一个、UTF-8。序列化前必须完成全部不变量校验。

### 6.3 摘要

`matrix_digest = canonical_digest(payload)`，其中 `payload` 是
`matrix_to_canonical_dict(matrix)` **删除 `matrix_digest` 自身**后的字典，使用现有
`mechanism.model_digest.canonical_digest`（排序键、紧凑 UTF-8、SHA256、无换行）。
`canonical_digest` 的真实实现为：

```python
json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
sha256(...).hexdigest()
```

因此 `sort_keys=True` 已在算法内，字典键顺序**不可能**影响身份。摘要覆盖面
（不含 `matrix_digest` 本身）为 6.5 节冻结的全部字段：

```text
matrix_schema_version, builder_version,
source_contract_digest, plan_digest, input_digest, domain_digest, dataset_digest,
role_order, columns[{position, term_role, coefficient_role, source_role}],
response_role, rows[{trade_date, cells[...]}],
quality{status（显式继承 preparation.status）,
        coverage_numerator, coverage_denominator, coverage_gate,
        missingness_policy, failure_disposition, reason_counts, rejected_dates
        （以上七项逐字段复制 preparation.quality，不重判）},
execution_authorized, statistics_computed
```

`matrix_digest` 的**计算口径必须与 `serialize_matrix` 的 payload 完全一致**：
serialize 用的是"payload + `matrix_digest`"，digest 用的是"payload − `matrix_digest`"。
两者不一致会使"逐字节比较"和"自摘要比较"互相矛盾，属于实现错误。

### 6.4 身份变化的必需方向

| 变化 | 是否必须改变 `matrix_digest` | 理由 |
| --- | --- | --- |
| observations 输入行排列 | 否 | 输入在 `input_digest` 前已按 (trade_date, 角色序位) 排序 |
| 字典键顺序 | 否 | 规范 JSON 排序键（`sort_keys=True`，已实测） |
| 工作目录、绝对路径、主机名、运行时 | 否 | 路径与环境不进入语义身份（已实测：换 cwd 后字节相等） |
| 任一 factor / control / target 值 | 是 | 进入 `rows[*].cells` 与 `dataset_digest` |
| 计划阈值、算子、合同、控制注册顺序 | 是 | 经 `plan_digest`、`dataset_digest`、`columns[*].coefficient_role` |
| 缺口日期或缺口原因（即使 n/N 不变） | 是 | 经 `quality.reason_counts` / `rejected_dates` / `dataset_digest` |
| 增加或删除控制项 | 是 | 列数、列名、`role_order` 全变 |
| 缺行导致 `rows` 变化 | 是 | `rows` 直接进摘要 |

### 6.5 冻结的规范字典（`matrix_to_canonical_dict` 的精确形状）

以下为**拟议 API**的精确输出结构。字段名、嵌套形状与类型在此冻结；实现者不得增删字段。
顺序仅用于阅读，实际身份由 `sort_keys=True` 决定。

```python
{
  "matrix_schema_version": "M4_DESIGN_MATRIX_V1",
  "builder_version": "M4_DAILY_CONDITIONAL_DESIGN_MATRIX_V1",
  "source_contract_digest": "<64 hex>",
  "plan_digest": "<64 hex>",
  "input_digest": "<64 hex>",
  "domain_digest": "<64 hex>",
  "dataset_digest": "<64 hex>",
  "role_order": ["TARGET_OUTCOME", "FACTOR", "CONTROL_0001", ...],
  "columns": [
    {"position": 1, "term_role": "INTERCEPT",
     "coefficient_role": "alpha", "source_role": None},
    {"position": 2, "term_role": "FACTOR_CONTINUOUS",
     "coefficient_role": "beta_factor", "source_role": "FACTOR"},
    ...
    {"position": n, "term_role": "CONDITION_INDICATOR",
     "coefficient_role": "gamma_condition", "source_role": "CONDITION_INDICATOR"}
  ],
  "response_role": "TARGET_OUTCOME",
  "rows": [
    {"trade_date": "2020-01-02", "cells": ["1", "-0.02", "0.01", "0.01", "1"]},
    ...
  ],
  "quality": {
    "status": "READY_SYNTHETIC",
    "coverage_numerator": 3,
    "coverage_denominator": 3,
    "coverage_gate": "0.99",
    "missingness_policy": "FAIL_CLOSED",
    "failure_disposition": "INCONCLUSIVE",
    "reason_counts": {},
    "rejected_dates": []
  },
  "execution_authorized": False,
  "statistics_computed": False
}
```

约束：

1. `payload` 中**没有** `row_count` / `column_count` 冗余字段：行数与列数分别由
   `len(rows)`、`len(columns)` 派生，避免出现"计数与内容不一致但仍能通过摘要"的对象。
2. `payload` 中**没有** `column_roles` 之类的扁平列名数组：列名只以
   `columns[*].term_role` 存在，避免同一信息出现两种可互相矛盾的表示。
3. `payload` 中**没有**独立的顶层 `status` 字段：就绪/拒绝状态只以 `quality.status` 存在
   （该字段显式继承 `preparation.status`，见第 4.2 节），避免同一载荷里出现两个可能互相
   矛盾的状态字段。这不等于"质量块没有 status"——`status` 在 `quality` 内，且它是继承值，
   不是矩阵层的重新判定。
4. `quality` 是**嵌套对象**（与 `dataset_to_canonical_dict` 的形状一致），不是扁平字段。
5. `matrix_digest` 只出现在 `serialize_matrix` 的输出中，不参与自身摘要计算。

### 6.6 与前一份草稿的差异说明（诚实记录）

本文件是同一路径的修订版。上一轮中断时留下的草稿在第 7 节给出的 `matrix_digest`
数值，是用一个**与 6.5 节不一致**的临时载荷（含 `column_roles`、`row_count`、
`column_count`、`cells` 等字段）算出的。本轮已把第 7 节全部 `matrix_digest`
改为按 6.5 节冻结形状实测重算的值：`plan_digest`、`input_digest`、`domain_digest`、
`dataset_digest`、`serialize_dataset` 字节哈希等上游值不变（它们来自既有实现），
只有矩阵自摘要及其字节哈希发生变化。这是一次设计自洽性修正，不是实现结果变化。

## 7. 精确数值示例（本轮在真实代码上复算）

以下全部数值为 2026-09-10 在本工作树、用既有真实实现实测得到，不是虚构摘要。
复算口径：`sys.path` 加入 `src` 与 `tests`，使用既有 fixture
`test_m4_stage4a1_typed_contract._document()` 与 `_compiled()`，合同/计划/输入/输出全部走
既有真实函数，矩阵投影按第 3 节规则独立重算。复算脚本为一次性只读探针，**未**纳入交付，
已在最终证据包前删除；本节所有数值均可由读者用同一 fixture 复现。

### 7.1 基础 fixture（真实合同与计划）

合同来源：既有 `_document()`。关键字段：`condition.operator = LTE`、
`condition.threshold = "-0.0100"`、`controls = ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"]`、
`development = 2020-01-01..2022-12-31`、`coverage_gate = "0.9900"`、
`missingness_policy = FAIL_CLOSED`、`evidence_rule.data_quality_failure_disposition =
INCONCLUSIVE`。

```text
contract_digest = ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457
plan_digest     = 45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981
input_digest    = c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602
domain_digest   = b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da
dataset_digest  = c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b
sha256(serialize_dataset(preparation)) = 32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060
validate_dataset(preparation, contract, plan, bound_inputs) = 通过（无异常）
status = READY_SYNTHETIC ; execution_authorized = False
source_contract_digest = ee450d1f...（等于 contract_digest）
role_order = ("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002")
quality: coverage_numerator = 3 ; coverage_denominator = 3 ; coverage_gate = 0.99
         missingness_policy = FAIL_CLOSED ; failure_disposition = INCONCLUSIVE
         reason_counts = {} ; rejected_dates = ()
```

计划的 `ordered_terms`（真实输出；第 2 项 `source_series_role` 为 `"FACTOR"`、第 5 项为
`"CONDITION_INDICATOR"`，二者**不同**，与第 3.2 节的来源绑定说明一致）：

```json
[{"coefficient_role":"alpha","position":1,"source_series_role":null,"term_role":"INTERCEPT"},
 {"coefficient_role":"beta_factor","position":2,"source_series_role":"FACTOR","term_role":"FACTOR_CONTINUOUS"},
 {"coefficient_role":"beta_control_0001","position":3,"source_series_role":"CONTROL_0001","term_role":"CONTROL_0001"},
 {"coefficient_role":"beta_control_0002","position":4,"source_series_role":"CONTROL_0002","term_role":"CONTROL_0002"},
 {"coefficient_role":"gamma_condition","position":5,"source_series_role":"CONDITION_INDICATOR","term_role":"CONDITION_INDICATOR"}]
```

计划条件节（真实输出）：`{"operator":"LTE","threshold":"-0.01","source_role":"FACTOR",
"output_role":"CONDITION_INDICATOR","true_value":1,"false_value":0}`。注意阈值在计划中已按
`canonical_decimal` 规范为 `"-0.01"`（合同里是 `"-0.0100"`）。

`preparation.complete_rows`（真实输出，`values` 按 `role_order =
("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002")`，第三元素为严格 `int` 指示值）：

```text
("2020-01-02", ("0.01", "-0.02", "0.01", "0.01"), 1)
("2020-01-03", ("0.02", "-0.01", "0.02", "0.02"), 1)
("2020-01-06", ("0.03", "0",     "0.03", "0.03"), 0)
```

### 7.2 基础 fixture 的矩阵（本设计预期输出）

```text
columns[*].term_role       = ["INTERCEPT","FACTOR_CONTINUOUS","CONTROL_0001","CONTROL_0002","CONDITION_INDICATOR"]
columns[*].coefficient_role= ["alpha","beta_factor","beta_control_0001","beta_control_0002","gamma_condition"]
columns[*].source_role     = [null,"FACTOR","CONTROL_0001","CONTROL_0002","CONDITION_INDICATOR"]
response_role              = "TARGET_OUTCOME"
role_order                 = ["TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002"]
```

| trade_date | INTERCEPT | FACTOR_CONTINUOUS | CONTROL_0001 | CONTROL_0002 | CONDITION_INDICATOR |
| --- | --- | --- | --- | --- | --- |
| 2020-01-02 | `1` | `-0.02` | `0.01` | `0.01` | `1` |
| 2020-01-03 | `1` | `-0.01` | `0.02` | `0.02` | `1` |
| 2020-01-06 | `1` | `0` | `0.03` | `0.03` | `0` |

目标向量（行序，**不进入矩阵列**）：`["0.01","0.02","0.03"]`。

按第 6.2/6.3/6.5 节冻结口径实测：

```text
matrix_digest = a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
sha256(serialize_matrix(matrix)) = 70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa
len(rows) = 3 ; len(columns) = 5 ; execution_authorized = false ; statistics_computed = false
```

对应的规范字典（第 6.5 节形状，`sort_keys=True` 后的真实字节；这就是
`sha256(serialize_matrix(matrix))` 的输入去掉尾部换行）：

```json
{"builder_version":"M4_DAILY_CONDITIONAL_DESIGN_MATRIX_V1","columns":[{"coefficient_role":"alpha","position":1,"source_role":null,"term_role":"INTERCEPT"},{"coefficient_role":"beta_factor","position":2,"source_role":"FACTOR","term_role":"FACTOR_CONTINUOUS"},{"coefficient_role":"beta_control_0001","position":3,"source_role":"CONTROL_0001","term_role":"CONTROL_0001"},{"coefficient_role":"beta_control_0002","position":4,"source_role":"CONTROL_0002","term_role":"CONTROL_0002"},{"coefficient_role":"gamma_condition","position":5,"source_role":"CONDITION_INDICATOR","term_role":"CONDITION_INDICATOR"}],"dataset_digest":"c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b","domain_digest":"b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da","execution_authorized":false,"input_digest":"c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602","matrix_digest":"a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a","matrix_schema_version":"M4_DESIGN_MATRIX_V1","plan_digest":"45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981","quality":{"coverage_denominator":3,"coverage_gate":"0.99","coverage_numerator":3,"failure_disposition":"INCONCLUSIVE","missingness_policy":"FAIL_CLOSED","reason_counts":{},"rejected_dates":[],"status":"READY_SYNTHETIC"},"response_role":"TARGET_OUTCOME","role_order":["TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002"],"rows":[{"cells":["1","-0.02","0.01","0.01","1"],"trade_date":"2020-01-02"},{"cells":["1","-0.01","0.02","0.02","1"],"trade_date":"2020-01-03"},{"cells":["1","0","0.03","0.03","0"],"trade_date":"2020-01-06"}],"source_contract_digest":"ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457","statistics_computed":false}
```

自洽性实测：把该 JSON 解析回字典、删掉 `matrix_digest` 后重算 `canonical_digest`，
结果等于 `a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a`；把它按第 6.2 节
序列化（末尾加一个 `\n`）后的 SHA256 等于 `70d9926e...b187fa`。两者均已在真实代码上核对。

### 7.3 精确条件边界（只有算子变化，阈值固定 0）

同一 factor 序列 `(-0.02, -0.01, 0)`、阈值规范化为 `"0"`，只替换合同算子并重新冻结与编译。
四行算子得到**完全不同**的指示列，且在阈值相等处严格区分（不做浮点容差）：

| 算子 | 合同 threshold | 计划规范化 threshold | 2020-01-02 | 2020-01-03 | 2020-01-06 |
| --- | --- | --- | --- | --- | --- |
| `LT` | `"0"` | `0` | `1` | `1` | `0` |
| `LTE` | `"0"` | `0` | `1` | `1` | `1` |
| `GT` | `"0"` | `0` | `0` | `0` | `0` |
| `GTE` | `"0"` | `0` | `0` | `0` | `1` |

（另有基础 fixture 的阈值 `-0.01` 与 factor 值 `(-0.02, -0.01, 0)` 的边界对比，用于确认
合同 `"-0.0100"` 在计划中规范化为 `"-0.01"`：`LT`/`LTE`/`GT`/`GTE` 的指示列分别为
`(1,0,0)`/`(1,1,0)`/`(0,0,1)`/`(0,1,1)`，即 `-0.01` 在 `LTE` 下为 1、在 `GT` 下为 0。）

对应实测矩阵（同列序，仅列 `CONDITION_INDICATOR` 不同；`plan_digest` 与
`dataset_digest`、`matrix_digest` 全部随之改变）：

```text
LT  : [("2020-01-02", ("1","-0.02","0.01","0.01","1")),
       ("2020-01-03", ("1","-0.01","0.02","0.02","1")),
       ("2020-01-06", ("1","0",    "0.03","0.03","0"))]
LTE : [("2020-01-02", ("1","-0.02","0.01","0.01","1")),
       ("2020-01-03", ("1","-0.01","0.02","0.02","1")),
       ("2020-01-06", ("1","0",    "0.03","0.03","1"))]
GT  : [("2020-01-02", ("1","-0.02","0.01","0.01","0")),
       ("2020-01-03", ("1","-0.01","0.02","0.02","0")),
       ("2020-01-06", ("1","0",    "0.03","0.03","0"))]
GTE : [("2020-01-02", ("1","-0.02","0.01","0.01","0")),
       ("2020-01-03", ("1","-0.01","0.02","0.02","0")),
       ("2020-01-06", ("1","0",    "0.03","0.03","1"))]
```

四行算子的计划身份（真实输出），说明算子确实进入身份：

```text
LT : plan_digest=44207cc23c608a0e33634a79db5810175a665409d3703296812e84ee3a8bab79 dataset_digest=0246d5fba959ce69efe9e93246bc19ca47656842b0ec950572d52aa2596319d5 matrix_digest=6b7687e32235393081554702b010b93958aa8fb92a27352ff0237e7f417cbff7
LTE: plan_digest=798955e8c4987cdfe8b067f19d59454039f728aad67ebeaa44bb41e38481bedf dataset_digest=4302b6f943f50b8939ec09c6ad9069079a2bdd01f97b67cb410a4ed6bb8a9c52 matrix_digest=a862e23b64ea7f928d81f2442d83c7439853bc714c601d70a5a8ca6374a170ee
GT : plan_digest=f4030af6d69f6009970c12ee895822837cab590c4ac5da256595da5aa88006f4 dataset_digest=5a76f115c5023044aebf0c0716e10ea7bc4137926599fa02475213a1421d088d matrix_digest=7b1703457786f09c1caaab0b801c55bdb6cb94b709d20dfee8759416f5775183
GTE: plan_digest=f32b071c6c69afac21a6d6d1f95e7d9aaa3453b2d6d314802503374d8f544b41 dataset_digest=79e5fdd0b0bef3706adf5d7fc2e259bf8e3b8eaf5bd975a37162541899f90f24 matrix_digest=7fbfcf8f3c5f196a0e06ab8e8ce514a371f4757aaa0dc6c3810d87b5c608d610
```

阈值 `-0.01` 的同一组对比（用于确认 `"-0.0100"` 在计划中被规范为 `"-0.01"`，且
`-0.01` 这个点严格落在 `LTE` 与 `GTE` 内、`LT` 与 `GT` 外）：

```text
LT : indicator=(1,0,0) dataset_digest=496145810434a8c77cefe88b279f832c597e3b258b7166d8ab714688b64c2067 matrix_digest=9d0c1f0986f4b7d78a5212bf25e11e6883d2ed58c1ef54b3fe1e88333fb7a49a
LTE: indicator=(1,1,0) dataset_digest=c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b matrix_digest=a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
GT : indicator=(0,0,1) dataset_digest=fe8f2a9acf513fe6562f9a8c937960a86183c03c9913cd3519fd5cad1b756d68 matrix_digest=e228c48e4b4c4b1b4bf3e50adb1fa719cade7a88f5db0a755169e9710ec77374
GTE: indicator=(0,1,1) dataset_digest=0612e95c83ad404dc957ad5ea8560e1a07faef203b3e0f488ea1816e9024d2d0 matrix_digest=7a093d21de861de1e073eab51a66b9e82072f9021545361dacfa0ccbe271d1e0
```

注意 `LTE` 一行与 7.1/7.2 的基础 fixture 完全同一身份（`dataset_digest`、
`matrix_digest` 相同），因为它就是同一个合同——这本身是对"口径一致"的交叉验证。

### 7.4 无 controls（重新冻结的合同）

`controls = []`：`role_order = ("TARGET_OUTCOME","FACTOR")`，计划 3 列，矩阵 3 列。

```text
contract_digest = 224d1dda42298ac8c1055fa8093ffbacfd43592364568777f365552df2e26f73
plan_digest     = 25d45eccedca0854f2ec5a6ccc08701f54822cf20d57a8764484a2016347f0d7
input_digest    = d002f398f45b820f9b1d14e43c9866a7a3a53e52f0c3b7b65245408772124952
domain_digest   = （与基础 fixture 相同：b78882e4...，domain 未变）
dataset_digest  = e0e52d46f078be3993e759b27c8bb84e71c3a590001282ef63eb1d02aff6728f
matrix_digest   = f6df25c471bc1a60f6f48c4863f30791388d26461b3210228a118975e5505db8
column_roles    = ["INTERCEPT","FACTOR_CONTINUOUS","CONDITION_INDICATOR"]
coefficient_roles = ["alpha","beta_factor","gamma_condition"]
role_order      = ("TARGET_OUTCOME","FACTOR")
status          = READY_SYNTHETIC ; n/N = 3/3
rows            = [("2020-01-02", ("1","-0.02","1")),
                   ("2020-01-03", ("1","-0.01","1")),
                   ("2020-01-06", ("1","0",    "0"))]
```

与基础 fixture 对比：列数由 5 变 3，`matrix_digest` 改变；因为 `controls` 参与合同与
计划内容，`contract_digest`/`plan_digest`/`dataset_digest` 也全部改变。

### 7.5 控制注册顺序变化（重新冻结的合同）

`controls = ["SYNTH_CONTROL_2", "SYNTH_CONTROL_1"]`（与基础 fixture 相反）：

```text
contract_digest = 91468509f54724eb61877baad116f1e67fa992eb22f6a5d4a2aea7b622145f1e
plan_digest     = 803eae6bdef67300792757170b238238786b77f314858cd34443c862f81c8143
input_digest    = 4a863864e3760a094a7d634c133aa3abe5badaf21f98d266372f08df992ae822
role_order      = ("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002")
column_roles    = ["INTERCEPT","FACTOR_CONTINUOUS","CONTROL_0001","CONTROL_0002","CONDITION_INDICATOR"]
coefficient_roles = ["alpha","beta_factor","beta_control_0001","beta_control_0002","gamma_condition"]
dataset_digest  = d4cddef0269825e3d040d3170aeab323c6c42c6c0e2e61c21c02f57bea8b1e94
matrix_digest   = 48f8a5b3930ecfad3abd29830d744ad8ec7cf368a130408d65f3fd90eab37f4f
rows            = [("2020-01-02", ("1","-0.02","0.01","0.01","1")),
                   ("2020-01-03", ("1","-0.01","0.02","0.02","1")),
                   ("2020-01-06", ("1","0",    "0.03","0.03","0"))]
```

关键点：`role_order`、`column_roles` 与 `coefficient_roles` 的**名字**都还是
`CONTROL_0001…`，与基础 fixture 字面相同；但 `contract_digest`、`plan_digest`、
`input_digest`、`dataset_digest`、`matrix_digest` 全部改变。角色名永远按注册顺序重新编号
为 `CONTROL_0001…`，**不**按 series 名或字母序排回，也不合并同名列。列名相同**不代表**
身份相同——身份由摘要承载。

注意：在本例中两个控制 series 的取值恰好相同（`0.01/0.02/0.03`），所以 `rows` 的字面值
与基础 fixture 相同；**只有摘要能区分"控制顺序不同"**。这正是"列名不可作为身份、
`matrix_digest` 必须覆盖 `dataset_digest`"的实测理由。

### 7.6 质量拒绝与部分矩阵封锁

全部实测，`_document()` 基础上只改 `data_quality_gates` 并重新冻结、重编译：

| 场景 | gate | missingness | 缺口 | status | n/N | complete_rows | dataset_digest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 基础 | 0.99 | FAIL_CLOSED | 无 | `READY_SYNTHETIC` | 3/3 | 3 | `c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b` |
| 缺 CONTROL_0002 于 2020-01-03 | 0.99 | FAIL_CLOSED | 1 | `REJECTED_QUALITY` | 2/3 | 0 | `d5e6511d420330e316c5b9ba26925294b7ecf2fcd77ec080f734e90bb32653cd` |
| 缺 CONTROL_0002 于 2020-01-03 | 0.66 | FAIL_CLOSED | 1 | `REJECTED_QUALITY` | 2/3 | 0 | `62352525a7724369ef7664233632f6a2a99571f64e7916e9a3cc3c0dd59984dd` |
| 缺 CONTROL_0002 于 2020-01-03 | 0.66 | RETAIN_IN_DENOMINATOR | 1 | `READY_SYNTHETIC` | 2/3 | 2 | `aff29dfda78a5db0a0a3fe4095eff7edb6211e0f084c774c1c14fcc40ae8d198` |
| 缺 CONTROL_0002 于 2020-01-03 | 0.67 | RETAIN_IN_DENOMINATOR | 1 | `REJECTED_QUALITY` | 2/3 | 0 | `d1d287f7f0d657d8a36866e5392224c875cbcc5b647d43a8b31e38d48515487c` |

对应的矩阵层结果（**拒绝态没有矩阵对象**，故只有错误码与"存在时的"摘要）：

| 场景 | 矩阵层行为 | 拒绝态是否有 rows | 若 READY 的 `matrix_digest` |
| --- | --- | --- | --- |
| 基础 | 返回对象 | — | `a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a` |
| 0.99 / FAIL_CLOSED / 缺口 | `DATASET_NOT_READY` | 无对象 | — |
| 0.66 / FAIL_CLOSED / 缺口 | `DATASET_NOT_READY` | 无对象 | — |
| 0.66 / RETAIN / 缺口 | 返回对象（2 行） | — | `09a1af5f1dd323522e5b628f57245fb0287e551d19ff6d96f5a9214f1065812e` |
| 0.67 / RETAIN / 缺口 | `DATASET_NOT_READY` | 无对象 | — |

结论（对实现者必须明确）：

- 缺口**不**缩小分母：`coverage_denominator` 仍是 3。
- `FAIL_CLOSED` 下任何缺口都直接 `REJECTED_QUALITY`，与 gate 无关；
  `RETAIN_IN_DENOMINATOR` 下才可能出现"有缺口但 READY"。
- 三日期 fixture 上的精确门槛比较（`Decimal("0.66").as_integer_ratio() == (33, 50)`，
  `Decimal("0.67").as_integer_ratio() == (67, 100)`）：
  `2*50 >= 3*33` 为真（gate 0.66 通过），`2*100 >= 3*67` 为假（gate 0.67 拒绝）。
  即"2/3 ≈ 0.6667"在 0.66 下通过、在 0.67 下拒绝——`0.66` 与 `0.67` 的区别正是
  "精确有理数比较"而非"显示百分比四舍五入"的结果。
- `REJECTED_QUALITY` 时 `complete_rows == ()`，矩阵层必须 `DATASET_NOT_READY`，
  **不得**输出 0 行或 2 行的部分矩阵。
- `FAIL_CLOSED` 的拒绝与 gate 无关，因此"把 gate 调低"**不是**绕过质量门的手段；
  这正是 `FAIL_CLOSED` 语义的实测确认。

### 7.7 缺口原因不改变 n/N 但改变身份

gate 0.66 / RETAIN_IN_DENOMINATOR，以下全部缺口都得到 2/3（`rejected_dates` 均为
`("2020-01-03",)`，除注明外），但**原因与身份不同**：

```text
删除 CONTROL_0002 于 2020-01-03 : reason_counts = {"MISSING_OBSERVATION": 1}
                                dataset_digest = aff29dfda78a5db0a0a3fe4095eff7edb6211e0f084c774c1c14fcc40ae8d198
                                matrix_digest  = 09a1af5f1dd323522e5b628f57245fb0287e551d19ff6d96f5a9214f1065812e
CONTROL_0002 该日 value=null    : reason_counts = {"MISSING_VALUE": 1}
                                dataset_digest = 5c95431cec44ff8633ddd6e27d6138ef9ede718ec29cce209d4a19eb7136849d
                                matrix_digest  = 8967d4fe69548bc8c3ff9924564a0e9e60af130f80104517441dcf5770fad50d
CONTROL_0002 该日 available_on=null（PIT_UNPROVEN）:
                                reason_counts = {"PIT_UNPROVEN": 1}
                                dataset_digest = 5cc29781d464871d217dc7d9317a5c9443549c8c2a99c02557fba0f80847c559
                                matrix_digest  = 52298a8c57c01fc152497bd547e1e70c882b0a3b12c98fd8ab78c2fcb6a0b7ef
CONTROL_0002 该日 available_on=2020-01-06（PIT_NOT_AVAILABLE）:
                                reason_counts = {"PIT_NOT_AVAILABLE": 1}
                                dataset_digest = 09dea69c1998be598d8d266f4277dca35b39c37976d80132affc62da35120337
                                matrix_digest  = fce3d11e2bda79fdcfc8a099f953d406e2fea7317b1546a5b05782797ddcdc5b
```

其他实测缺口同样改变身份且不缩小分母：

```text
缺 CONTROL_0002 于 2020-01-02 (rejected=2020-01-02) : 2/3
    dataset_digest=f85b4a3701ee92be4ad86b9f31f9a123d2d06b1639ad07983efc421ee245dec8
    matrix_digest =6e46e2a0bd3ba74bb2701dc465c889ca489c1d8cc3cab153accfcd1d601addac
缺 CONTROL_0001 于 2020-01-03 : 2/3
    dataset_digest=e684cab7263b5d1491ec586ecb3241b2a9f88e293dd8ce8d84b5297613701557
    matrix_digest =d995c832df5798f4fcd08b68f592f102a29b16342b148a57463378e627821d9d
缺 TARGET_OUTCOME 于 2020-01-03 : 2/3
    dataset_digest=38b5d6ccb8008e9d1aa976949c735aa0a92c2115dc2f67de188746969c2f6910
    matrix_digest =3c3b4158c7845e855b57c25e56509f104f3e4e14f58c065fe9a2d06510e05272
缺 FACTOR 于 2020-01-03 : 2/3
    dataset_digest=8303d7e0fa0dc2d4c8ace978f85633ce6e63eb6c07e67abd714bfeb75932e27f
    matrix_digest =5734473dd3f051351bbeae6647faf85f28f17ef5d79d9c62f7c64e7474a5a245
```

**九种不同的缺口原因/位置组合得到九种不同的身份**，其中若干组合的 `n/N` 与 `rows`
字面值完全相同（例如两种原因都 2/3、都缺 2020-01-03）。因此矩阵身份必须覆盖
`quality.reason_counts`、`quality.rejected_dates` 与 `dataset_digest`；只覆盖数值单元
**不足以**区分这些情况。

### 7.8 等价性与篡改实测

```text
observations 逆序后重算 input_digest : 与原始相等（True）
逆序后 dataset_digest                : 相等（True）
逆序后 serialize_dataset 字节         : 相等（True）
逆序后 matrix_digest                 : 相等（True）

篡改 complete_rows 的 indicator（三行全部取反）并重算 preparation.dataset_digest:
    tampered.dataset_digest = 721584843f0f10448b0e1aecc28cc30a52018844be4c5852923c0acdab57b79f  （≠ 原始 c3410933...）
    serialize_dataset(tampered)            -> ACCEPTED（内部自洽，无异常）
    validate_dataset(tampered, contract, plan, bound_inputs) -> IDENTITY_CONFLICT
    该篡改体若被投影，会得到 matrix_digest = fdf644360661742ef18df1520cff830eba8dc629f97510b4bc84b9e951374d6a
    （≠ 合法基础矩阵 a3c40269...），且指示列会从 (1,1,0) 变成 (0,0,1)。
    公开入口 materialize_design_matrix(tampered, contract, plan, bound_inputs) 在 A1 步
    即抛上游 IDENTITY_CONFLICT，永远不会走到投影；上面的 matrix_digest 只用于说明
    "投影层自身不做来源验证"，不构成任何可调用的旁路。

重哈希过的**原始输入**篡改（把 FACTOR 在 2020-01-03 的值改为 "-0.05" 并重算 input_digest 与证据摘要）:
    rehashed.input_digest  = e877c147b58b53ee3283e87bcce49592470643c161e7a675af1e06a51943b464 （≠ 原始 c1f6c3d7...）
    rehashed.dataset_digest = 2788e8ec06d370a3020b99fecbdcb4d7cb30d7568dbea33d0f22a63a063a7aea
    rehashed.matrix_digest  = 95a7d95835ebd92f7f7cccfb890ba3bd2ad7cadab00c1e36f608a11a48b6fdf3
    rehashed.rows           = [("2020-01-02",("1","-0.02","0.01","0.01","1")),
                               ("2020-01-03",("1","-0.05","0.02","0.02","1")),
                               ("2020-01-06",("1","0",    "0.03","0.03","0"))]
    validate_dataset(rehashed_preparation, contract, plan, 原始 bound_inputs) -> IDENTITY_CONFLICT
```

因此矩阵的两个公开入口（`materialize_design_matrix` 与 `validate_design_matrix`）都必须各自
完成来源验证：只信 `preparation.dataset_digest` 或只跑 serializer 都会接受被篡改的指示列；
只信 `bound_inputs.input_digest` 也会接受重哈希过的输入。**只有四参数 `validate_dataset`
能同时封住这两条路径**，因为它重新 materialize 并与原始输入逐字节比对。

### 7.9 嵌套修改与计划绑定实测

在 `_document()` 内层 `robustness_registry[0].parameters.trim` 由 `"0.0100"` 改为 `"0.0200"`：

```text
nested.contract_digest = f4c193cbbc9a32e9bc7d17bf9ba494c7702fc46acd3c723102d025e8084eed9f  （≠ 基础）
nested.plan_digest     = 8833ed844a7f50d9665945b7d18c07d2e1d72bde97b13cf8aeefcad24e2cc677  （≠ 基础）
nested.dataset_digest  = dfa395bb1dff0c694cad4d8cc3438d07c2896f92bdb72d20fdbcfe663eaf5c6d  （≠ 基础）
nested.matrix_digest   = b75877ee489f1a08bdcbbcc6fa0f0c57a9a1e1fcc940844ca04ea5ea7c2ddd5e  （≠ 基础）
plan.robustness_plan.entries[0].parameters.trim: 基础 "0.0100" → 修改后 "0.0200"
materialize_analysis_dataset(nested_contract, base_plan, base_inputs) -> CONTRACT_PLAN_MISMATCH
```

说明：即使该内层字段不影响矩阵数值，身份仍然必须改变——身份绑定的是内容，不是"看起来
相关的字段"。这正是"用 plan 重编译 + 逐字节比较"而不是"比较若干看起来相关的字段"的
理由。

### 7.10 规范十进制与非法值实测

```text
ObservationV1 value="-0"     -> INVALID_VALUE
ObservationV1 value="0.0100" -> INVALID_VALUE
ObservationV1 value="1E-2"   -> INVALID_VALUE
ObservationV1 value="0.0"    -> INVALID_VALUE
ObservationV1 value="0"      -> ACCEPTED（唯一的零表示）
ObservationV1 value="0.01"   -> ACCEPTED
ObservationV1 value="1"      -> ACCEPTED
ObservationV1 value="-0.01"  -> ACCEPTED
plan threshold "-0.0100"（合同）规范化为 "-0.01"
plan threshold "0"（合同）规范化为 "0"
```

规范零的唯一形式是 `"0"`：`"-0"`、`"0.0"`、`"0.00"` 全部拒绝。规范整数不带小数点：
`"1"` 合法，`"1.0"` 非法。这与 `_dec` 的真实实现一致：

```python
canonical = "0" if d == 0 else format(d, "f")
if "." in canonical:
    canonical = canonical.rstrip("0").rstrip(".")
if canonical != value:
    _fail("INVALID_VALUE")
```

因此矩阵层**不重新解析、不四舍五入、不格式化**：它只搬运上游已经规范化的字符串。
矩阵层不得"顺手修好"这些值：一旦上游放行非法字符串，矩阵层必须抛错而非就地规范化。

### 7.11 键序与工作目录不变性实测

```text
把规范字典的键顺序按 sha256(键名) 重排后重算 matrix_digest : 与原始相等（True）
把 preparation 规范载荷的键顺序完全逆序后重算 input_digest  : 与原始相等（True）
换工作目录到 src/ashare_research 后重新 materialize：
    dataset_digest 相等（True）
    serialize_dataset 字节相等（True）
    matrix_digest 相等（True）
serialize_dataset(preparation) 字节中不包含工作树绝对路径（False）
字节中不出现 worktree / hostname / cwd 之类的键（False）
```

即"字典键次序不改变身份、工作目录与绝对路径不进入身份"两条要求在真实实现上成立，
而不是设计假设。原因是 `canonical_digest` 内部固定 `sort_keys=True`（第 6.3 节），
且身份链只由内容摘要构成，不含任何路径。

### 7.12 多 controls（三个控制项）

`controls = ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2", "SYNTH_CONTROL_3"]`，并额外提供
`CONTROL_0003` 序列（`0.04/0.05/0.06`）：

```text
contract_digest = 284295d316f2af1dad947a126d51ef077f5582f0d34841614eec644592d5a284
plan_digest     = 1be6c91f6e14f31f8402d48efad3e8fdf76ee2149049d889334d66d7058e3e04
input_digest    = daad9c937c22a8883c1b0bb54ff6ed4f9780f7baaeccb49e06e399e929bbae88
role_order      = ("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002","CONTROL_0003")
column_roles    = ["INTERCEPT","FACTOR_CONTINUOUS","CONTROL_0001","CONTROL_0002","CONTROL_0003","CONDITION_INDICATOR"]
dataset_digest  = 4c0603288b168b067b9a117744ffba38c3e6a81a0be9668511702140f31bec0f
matrix_digest   = 13c1830672434e1d6a56ae8a3548ab106b6baab86295b792a242e2f4b43f115e
len(columns)    = 6 ; status = READY_SYNTHETIC ; n/N = 3/3
rows            = [("2020-01-02", ("1","-0.02","0.01","0.01","0.04","1")),
                   ("2020-01-03", ("1","-0.01","0.02","0.02","0.05","1")),
                   ("2020-01-06", ("1","0",    "0.03","0.03","0.06","0"))]
```

控制列数量必须随注册控制数增长（本例 3 个控制 → 6 列），不得固定为 5 列，也不得因为
`CONTROL_0003` 是新角色而忽略它。这与第 7.4 节（0 个控制 → 3 列）共同确认列数完全由计划
的 `ordered_terms` 决定。

## 8. 实现落点、复用与不得触碰项

### 8.1 拟议落点

拟议新增一个纯模块（例如 `mechanism/planning/matrix.py`）承载上述类型与函数。选择
`planning` 包的理由：矩阵是"计划的投影视图"，与 A.2I 冻结的 `compiler.py` 同域但**不得**
修改后者；`datasets` 包已被现有适配器占用，复用它需要改 `datasets/__init__.py` 的
`__all__`，会与"不得改既有导出"的约束冲突。最终落点属实现评审项。

该模块的导出面**只有**第 5.1 节的四个公开 API；`_project_validated_matrix` 必须保持私有
（下划线前缀、不进入 `__all__`、不被文档或验收当作入口）。任何把纯投影提升为公开 API 的
实现都属于违反本设计。

### 8.2 复用（只调用，不修改）

- `mechanism.model_digest.canonical_digest`
- `mechanism.planning.plan_to_canonical_dict` / `validate_analysis_plan`
- `mechanism.datasets.validate_dataset`（四参数）
- 现有 `DatasetPreparationV1`、`RoleBindingV1`、`ObservationV1`、`ExpectedDomainV1` 只读消费

### 8.3 明确不得触碰

`analysis_dataset.ANALYSIS_COLUMNS`、`analysis_contracts` 的固定 M3 日期与 holdout 门、
`regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、`crash.py`，
以及全部 M3 冻结产物与哈希。矩阵层不得引入 pandas 或任何统计库作为规范序列化边界。

### 8.4 schema 变更

本设计**不需要**任何 A.1 / A.2 / dataset schema 变更。实现过程中如发现确有必要变更任何
已冻结 schema，必须**停止并报告**，不得把变更藏进设计或实现。

## 9. 实现前置条件与验收边界

实现（另立 Goal、另获授权）前必须满足：

1. 四份设计文档通过独立审查，接口与失败语义无关键待定项；
2. 全部验收案例按 [合成矩阵验收场景 v1](m4_analysis_matrix_acceptance_cases_v1.md) 先复现
   负例再实现正例；
3. 已有 adapter / compiler / 保护门回归保持通过；
4. 不新增镜像式产品测试来替代真实最小实现验证。

本设计的验收**不是**实现授权。矩阵实现、PR #11 合并、任何 M4-B 或统计执行阶段都需要用户
分别明确授权。

## 10. 未决与风险

| 项 | 状态 | 说明 |
| --- | --- | --- |
| 错误类型归属 | 待实现评审 | 独立 `MatrixError` vs 复用 `AdapterError`；本设计给出可区分性要求，且不把 `AdapterError` 包成矩阵错误 |
| 模块落点 | 待实现评审 | `planning/matrix.py` 为拟议；不得为落点修改既有 `__init__` 导出 |
| `source_role` 审计/来源元数据 | 已冻结语义 | 进入规范载荷、序列化与 `matrix_digest`，必须与计划一致；**不参与**单元格取值分派。列语义与投影规则由 `term_role` 承载：`source_series_role` 只表达输入来源，无法单独说明该列取常量 `1`、取 `values` 还是取 `condition_indicator`；`INTERCEPT` 为 `null`，指示列指向不在 `role_order`/`values` 的 transform 输出，实现不得据其建表。当前 `ordered_terms` 上 `term_role → source_series_role` 恰好一一对应，但实现不得依赖该巧合 |
| 对外材料化入口 | 已冻结（第 5.1 节） | 只有四参数 `materialize_design_matrix(preparation, contract, plan, bound_inputs)`；纯投影 `_project_validated_matrix` 为私有实现细节，不是 API/验收入口 |
| 摘要载荷形状 | 已冻结（第 6.5 节） | 上一轮草稿曾用不一致的临时载荷；本轮已按冻结形状重算第 7 节全部自摘要 |
| 未来真实数据 | 不在本设计 | 合成来源证据不可升级为真实研究证据 |
| M3 固定列与固定开发期 | 明确禁止 | 复用即回归 M3，属禁止范围 |
| `quality.status` 命名与来源 | 已冻结 | 沿用既有 `READY_SYNTHETIC` / `REJECTED_QUALITY`，且 `status` 显式继承 `preparation.status`（顶层字段），其余七个质量字段逐字段复制 `preparation.quality`；本设计**不新增** `READY_MATRIX` 状态 |
| 执行授权 | 恒为 false | 任何 readiness 声明都不得越过执行授权边界 |
| 统计有效性 | 未声明 | 矩阵准备成功不代表满秩、可估计、显著或可交易；本设计不计算任何统计量 |
| 实现与测试 | 未开始 | 本文件是设计，不是实现；不存在可通过的实现测试 |

### 10.1 明确不在本设计内的事情

- 本设计**没有**实现 `materialize_design_matrix` 等任何函数；第 4、5、6 节全部标记为拟议 API。
- 本设计**没有**新增或修改任何产品测试；第 7 节数值全部由一次性只读探针在既有真实实现上
  实测得到，探针未纳入交付。
- 本设计**没有**执行任何回归、bootstrap、稳健性或 evidence 计算。
- 本设计**没有**访问数据库、provider、真实行情或 holdout。
- 本设计**不构成**执行授权、统计有效性声明或 PR #11 合并依据。
