# M4 合成端到端流水线设计 v1

状态：DESIGN_ONLY / READY_FOR_IMPLEMENTATION_REVIEW。**2026-09-12 设计更正**：第 4.4 节 `J4`、
第 5.5 节 `D6`、第 6.1 节 `S0` 行与第 6.2 节 `P3`、第 7.1 节 `G14` 与 S0 扫描面、
第 8.3/8.4/8.5 节（复制上界行、透传面说明、可达性分类）、第 9.5 节 `V3`/`V4`/`V5` 失败码、
第 10.3 节绑定失败码、第 11.3 节调用次数上界与 `§11.3.1 R17.2` 求值条件、
第 14 节 `R2`/`R11`/`R17`/`R19` 已按实现评审的
**实测证据**更正（依据：实现保全提交 `8a71fb9` 的源码、测试与记录；契约见
`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`；逐项变更清单见
`acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`）。本次更正**只**修正
与实测不符或自相矛盾的事实陈述：公开 20 符号面、14 码封闭表、常量值、字段、签名、`L1`–`L14`、
`S0`–`S8`、`V1`–`V6`、授权边界与全部上游契约**均未改变**。本文是 M4-A 阶段
`Typed Contract -> Plan -> Synthetic Dataset -> Immutable Matrix -> Bounded Execution`
五个**已实现且已冻结**阶段的单一编排入口设计规范与**拟议接口契约**，尚未实现。
文中全部类名、函数名、字段名、常量名与错误码都标记为**拟议（proposed）**，不冒充现有实现，
也不表示本阶段获得任何实现、统计执行、真实数据、真实候选数据集、文献获取、provider、
数据库内容或 holdout 授权。

**2026-09-13 AC-05 澄清**：最小可物化域只保证适配器与矩阵能够生成对象，不保证 S6 设计矩阵
满秩。S6 的既有 `ExecutionError("SINGULAR_DESIGN")` 是合法的组合入口首错，按第 8.4/8.5.1 节
原样透传；对应验收场景见 [AC-05](m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md#ac-05-边界最小可物化域)。
此澄清不改变估计器、门禁、公开错误码或授权范围。

基线：工作树 `D:/量化分析-m4-synthetic-pipeline-design`，分支
`codex/m4-synthetic-pipeline-design`，任务起始 HEAD
`f6ec598ac819c2d8db14f7a2e8c910a6ed85b301`（仅含 Goal 文件），基线 `origin/main`
`fd1cc35ee824aa9449f7e7800c12d0d80c845e05`（PR #15 合并点）。

依赖并保持冻结的既有设计与实现：

- [Goal：M4 synthetic end-to-end pipeline design](../agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md)
- [M4-A.1 类型化合同与冻结合同编译器](../acceptance/m4_stage4a1_typed_hypothesis_config_and_frozen_contract_compiler.md)（`mechanism/contract_compiler.py`）
- [M4-A.2I 确定性分析计划编译器](../acceptance/2026-09-07_m4a2i_analysis_plan_compiler.md)（`mechanism/planning/compiler.py`）
- [M4 合成数据适配器设计 v1](m4_dataset_adapter_design_v1.md)（`mechanism/datasets/synthetic.py`）
- [M4 合成分析矩阵设计 v1](m4_analysis_matrix_design_v1.md)（`mechanism/planning/matrix.py`）
- [M4 有界执行与证据处置设计 v1](m4_bounded_execution_and_evidence_design_v1.md)（`mechanism/execution/bounded.py`）
- [M4-B 理论/假设注册表设计 v1](m4b_hypothesis_registry_design_v1.md)（`mechanism/registry/`）

编号约定：本文的条款编号（`S0`–`S8`、`D1`–`D7`、`P1`–`P7`、`E7`–`E9`、`I1`–`I6`）是稳定标识，
一经发布不得重用或改义；删除条款必须留空号，不得重排。跨文档条款编号见第 13 节。

---

## 1. 目标、范围与非目标

### 1.1 目标

本设计冻结一个**单一、确定性、内存内**的编排入口，把五个已冻结的合成阶段串成一条可复现链，
并冻结以下九件事：

1. 一个最小公共编排入口与不可变结果信封的**精确**名称、输入、输出、版本常量、规范序列化、
   身份/摘要规则与公开导出面（第 4、5 节）。
2. 五个阶段的**精确组合顺序**，以及每阶段之前与之后的验证；不得复制任何统计实现、
   不得绕过任何既有验证器（第 6 节）。
3. 合成来源与授权门禁：在任何计算之前拒绝真实/未知输入，并让注册表元数据与执行证据
   在**结构上**分离（第 5.4、7、10 节）。
4. 确定性首错顺序、稳定错误码、异常映射，以及失败时**不产生部分结果**（第 8 节）。
5. 源配置、冻结合同、计划、准备数据、矩阵与执行产物之间的跨产物绑定，含精确摘要链与
   篡改检测责任划分（第 9 节）。
6. 不可变性、规范字节相等、重复运行确定性、有界资源行为，以及不存在文件系统/网络/
   provider/数据库/holdout 副作用（第 6.4、11 节）。
7. 可选合成/schema-only M4-B 记录如何作为**元数据**绑定而不改变其状态、不作为证据、
   不触发执行；省略时具有显式语义（第 10 节）。
8. 完整验收矩阵与后续 Goal 的实现白名单（第 12 节与配套验收场景文档）。
9. 显式非目标与残余风险，包含"为什么这不是通用真实数据研究执行器"（第 1.2、14 节）。

### 1.2 非目标（本设计不授权）

本设计**不做**、也**不授权**以下任何一项：

1. 不实现本设计的任何符号；第 4、5、10 节全部为拟议 API 与拟议常量。编排器**尚不存在**。
2. 不改动任何既有冻结组件：不改 `src/**`、不改既有 `__all__`、不改任何既有 schema 版本、
   不改正则/常量值/摘要算法、不改错误码、不改既有测试、报告、fixture、workflow 或依赖。
3. 不做真实数据适配、不访问 provider、不打开数据库、不读取真实行情、不采集文献、
   不创建或加载真实候选注册数据集、不进入真实 M4-B 研究。
4. 不接触 holdout；任何 holdout 请求 fail-closed。本设计不存在可传 holdout 的入口。
5. 不做回测、排序、提升、选择、调优、推荐或任何交易结论；不声称可估计性、统计显著、
   经济有效、可交易或任何 A 股机制结论。
6. 不把"合成流水线就绪"表述为"A 股机制已建立"或"研究已授权"。
7. 不推送 `main`、不强制推送、不做破坏性清理、不改动 stash 或原始工作树。
8. 不把注册表元数据当作证据，也不让注册表状态影响任何统计量或执行授权。

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| 编排器 / orchestrator | 拟议的单一公共入口 `run_synthetic_pipeline`，只做门禁、转发与组合 |
| 结果信封 / result envelope | 拟议不可变类型 `SyntheticPipelineResultV1`，编排器唯一返回值 |
| 合成策略输入 / synthetic policy input | 调用者必须提供、且**无法**由上游阶段推导的合成声明（第 5.3 节） |
| 上游产出对象 / upstream-produced object | 必须由前一阶段函数产出、调用者不得手工伪造的对象 |
| 首错 / first error | 按第 6 节冻结顺序第一个失败的步骤所抛出的、唯一的错误 |
| 链式重算 / chain recomputation | 既有下游验证器"重新验证上游 + 重算 + 逐字节比对"的既有模式 |
| 摘要链 / digest chain | 从源配置到执行产物的十四个身份链接 `L1`–`L14`，其中六个字段构成执行层 `SourceChainV1`（第 9 节） |
| 注册表元数据绑定 / registry metadata binding | 第 10 节的只读、可选、非证据字段块 |

---

## 2. 已验证基线与来源绑定

### 2.1 现有能力链（本设计只消费，不重定义）

本设计只调用以下已存在于当前 HEAD 的公共入口，**不**重定义其语义：

| # | 阶段 | 既有公共入口（实测签名） | 返回 |
| --- | --- | --- | --- |
| S2 | 合同编译 | `compile_hypothesis_config(config: HypothesisConfig) -> FrozenMechanismContract` | 不可变合同 |
| S3 | 计划编译 | `build_analysis_plan(contract: FrozenMechanismContract) -> DeterministicAnalysisPlan` | 不可变计划 |
| S4 | 合成数据适配 | `materialize_analysis_dataset(contract, plan, bound_inputs) -> DatasetPreparationV1` | 不可变准备数据 |
| S5 | 矩阵物化 | `materialize_design_matrix(preparation, contract, plan, bound_inputs) -> MatrixPreparationV1` | 不可变矩阵 |
| S6 | 有界执行 | `execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs) -> ExecutionArtifactV1` | 不可变执行产物 |

配套验证器（本设计只调用，不修改）：
`validate_contract`、`validate_analysis_plan`、
`validate_dataset(preparation, contract, plan, bound_inputs)`、
`validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)`、
`validate_execution_artifact(artifact, matrix, preparation, contract, plan, bound_inputs)`。

配套规范序列化器：`serialize_frozen_contract`、`serialize_analysis_plan`、
`serialize_dataset`、`serialize_matrix`、`serialize_execution_artifact`。

### 2.2 复合键不可拆：五元组是既有事实

`materialize_design_matrix` 与 `execute_bounded_analysis` 都要求完整五元组
`(matrix, preparation, contract, plan, bound_inputs)`；既有执行层文档明确"没有只吃 `matrix`
的路径，也没有 `**kwargs`"。因此本设计的编排器**不得**发明"矩阵单参"路径，也不得省略
`bound_inputs`。README 第 107–146 行与 `execution/__init__.py` 的模块 docstring 已把这一点
写成冻结事实。

### 2.3 链式重算是既有的篡改检测机制（实测）

既有验证器不是"只查结构"，而是**重算并逐字节比对**：

- `validate_dataset` 重新调用 `materialize_analysis_dataset` 并比较
  `serialize_dataset(preparation)` 与重算结果的字节（`datasets/synthetic.py:791-799`）。
- `validate_design_matrix` 先做 `_validated_matrix_payload`（其中在
  `planning/matrix.py:323-324` 重算并比对 `matrix_digest`），再
  `validate_dataset`，再重投影并逐字节比对（`planning/matrix.py` `validate_design_matrix`）。
- `serialize_dataset` 自身在 `datasets/synthetic.py:784-785` 重算 `dataset_digest` 并比对；
  `serialize_matrix` 经 `_validated_matrix_payload` 重算 `matrix_digest` 并比对。
- `validate_execution_artifact` 走 V1–V4 四步：V1 结构与自摘要、V2 `validate_design_matrix`、
  V3 **重新执行**、V4 逐字节比对（`execution/bounded.py` `validate_execution_artifact`）。
- `_check_plan_source` 的 X1–X2 先做五对象 `_shape`，再调用 `validate_design_matrix`
  （`execution/bounded.py` `_check_plan_source`）。

结论：本设计**不需要**发明新的篡改检测机制，只需保证编排器把每个下游验证器都接进链路，
并把这条链的检测能力与检测**盲区**在验收场景里逐条断言（第 9.4 节）。

### 2.4 副作用面实测为零

对五个阶段模块的 import 段与副作用模式做机械扫描（`open(`、`.write`、`requests`、`urllib`、
`duckdb`、`socket`、`subprocess`、`tempfile`、`os.environ`、`os.getcwd`、`datetime.now`、
`time.time`、`import random`）：**零命中**。五个模块的 import 仅有
`json`、`re`、`math`、`dataclasses`、`datetime.date`、`decimal`、`types`、`typing`、`numpy`
与同包内部模块。因此"S"链本身天然无文件系统、网络、provider、数据库或 holdout 副作用；
本设计的责任是**不引入**这类调用（第 11 节）。

### 2.5 RNG 由计划声明驱动

`execution/bounded.py:965` 使用 `numpy.random.Generator(numpy.random.PCG64(seed))`，其中 `seed`
来自计划中已冻结的 bootstrap 声明（`_bootstrap_declaration` 从计划 payload 读取 `seed`，
`execution/bounded.py:654-668`）。编排器**不得**提供、覆盖或派生 seed；seed 只来自
`HypothesisConfig.bootstrap_policy` 经合同与计划固化后的值。这是重复运行确定性的前提（第 11.2 节）。

---

## 3. 冻结的常量（拟议）

以下全部为**拟议**常量；实现不得改名、改值或新增同类常量。

```text
ORCHESTRATOR_VERSION              = "M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V1"
PIPELINE_SCHEMA_VERSION           = "M4_SYNTHETIC_PIPELINE_RESULT_V1"
PIPELINE_STATE                    = "SYNTHETIC_PIPELINE_COMPLETED"
PIPELINE_DIGEST_ALGORITHM         = "M4_CANONICAL_PIPELINE_RESULT_DIGEST_V1"
PIPELINE_STAGE_SEQUENCE           = ("INTAKE","CONTRACT","PLAN","SYNTHETIC_INPUT","DATASET",
                                     "MATRIX","EXECUTION","ENVELOPE")
REQUIRED_STAGES_COMPLETED         = ("CONTRACT","PLAN","SYNTHETIC_INPUT","DATASET","MATRIX","EXECUTION")
REGISTRY_BINDING_ABSENT           = "NO_M4B_REGISTRY_METADATA_BOUND"
REGISTRY_BINDING_PRESENT          = "M4B_REGISTRY_METADATA_BOUND_READ_ONLY"
REGISTRY_BINDING_DIGEST_ALGORITHM = "M4_CANONICAL_REGISTRY_BINDING_DIGEST_V1"
SYNTHETIC_PIPELINE_MODE           = "SYNTHETIC"
```

**实现细节常量（不进入公开 `__all__`；见第 C6、J4、R17.5、BS6 条）**：

```text
DECIMAL_CONTEXT_PRECISION         = 28
MAX_BOOTSTRAP_REPLICATIONS        = 100000
BINDABLE_REGISTRY_STATUSES        = ("DISCOVERED", "LITERATURE_REVIEWED",
                                     "A_SHARE_FEASIBILITY_REVIEWED", "NOT_TESTED",
                                     "PRE_REGISTERED", "DEFERRED")
```

**`metadata.interpretation_boundary` 的字面量（冻结，逐字符）**：编排器**必须**原样使用既有
执行层常量 `ashare_research.mechanism.execution.INTERPRETATION_BOUNDARY` 的值，不得改写、缩写、
翻译或重新断行：

```text
SYNTHETIC_TEST_ONLY: output of the frozen bounded executor on validated synthetic inputs. Not a research finding; not evidence of estimability, significance, economic validity or tradability; not an A-share mechanism result; not an authorization to execute on real data, on holdout data, or to enter M4-B.
```

注意其字段落点是既有 `ExecutionArtifactV1.evidence.interpretation_boundary`
（`execution/bounded.py` 的 `EvidenceBlockV1.interpretation_boundary`），**不是**
`method_configuration`。同名常量在 `registry/snapshot.py` 有**不同值**（`REGISTRY_METADATA_ONLY: …`），
导入时必须避免遮蔽（第 4.1 节 I6）。

形态约束（结构性，而非约定）：

| 常量 | 类型 | 取值约束 |
| --- | --- | --- |
| `ORCHESTRATOR_VERSION` | `str` | 严格等于上值；出现在信封与每个稳定错误中 |
| `PIPELINE_SCHEMA_VERSION` | `str` | 严格等于上值 |
| `PIPELINE_STATE` | `str` | 严格等于上值；只在成功信封中出现 |
| `PIPELINE_DIGEST_ALGORITHM` | `str` | 严格等于上值 |
| `PIPELINE_STAGE_SEQUENCE` | `tuple[str, ...]` | 恰为 8 元素、升序位置即执行顺序；顺序进入摘要 |
| `REQUIRED_STAGES_COMPLETED` | `tuple[str, ...]` | 恰为 `PIPELINE_STAGE_SEQUENCE[1:7]`；成功信封必须逐项等于它 |
| `REGISTRY_BINDING_ABSENT` | `str` | 省略注册表元数据时 `binding_state` 的唯一取值 |
| `REGISTRY_BINDING_PRESENT` | `str` | 提供注册表元数据时 `binding_state` 的唯一取值 |
| `REGISTRY_BINDING_DIGEST_ALGORITHM` | `str` | 严格等于上值 |
| `SYNTHETIC_PIPELINE_MODE` | `str` | 严格等于 `"SYNTHETIC"`；与既有适配器 `SCHEMA` 门禁兼容 |

---

## 4. 拟议公开接口

### 4.1 落点与导出面

拟议新模块：

```text
src/ashare_research/mechanism/pipeline/__init__.py
src/ashare_research/mechanism/pipeline/orchestrator.py
```

落点属实现评审项，但**必须**满足：

- I1：新模块**不得**改变 `mechanism/__init__.py`、`mechanism/planning/__init__.py`、
  `mechanism/datasets/__init__.py`、`mechanism/execution/__init__.py`、
  `mechanism/registry/__init__.py` 的既有 `__all__`（实测：`execution/__init__.py` 的
  docstring 写明 "exports exactly the eight frozen public entries"）。
- I2：新模块的 `__all__` 恰为第 4.4 节的冻结清单，不得多、不得少。
- I3：新模块不得从 `mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、
  `crash.py`、`analysis_dataset.py`、`analysis_contracts.py` 直接导入任何符号。
- I4：新模块不得**直接**导入 `pandas`、`statsmodels`，也不得导入 `os`、`pathlib`、`io`、`socket`、
  `subprocess`、`tempfile`、`datetime`（除类型注解不需要者外一律不导入）、`duckdb`、
  `requests`、`urllib`。可导入：`json`、`re`、`hashlib`、`decimal`、`dataclasses`、`typing`、
  既有同包五个阶段模块的公共入口与 `mechanism.model_digest.canonical_digest`。
  **重要澄清（实测）**：`mechanism.model_digest` → `mechanism.analysis_contracts` → `import pandas`，
  因此一旦编排器导入 `canonical_digest`，**进程内**必然已加载 `pandas`（实测：导入
  `contract_compiler` 后 `"pandas" in sys.modules` 为 `True`；同一依赖链还带入 `pyarrow`、
  `socket`、`pathlib`、`yaml`）。I4 因此只能约束编排器**不直接导入** pandas、
  **不把 pandas 用作序列化或计算边界**；"进程内无 pandas/socket/pathlib"**不是**可实现的目标，
  也**不得**被写成验收断言（见第 11.4 节 N4）。
- I6：新模块**不得**同时从 `mechanism.execution` 与 `mechanism.registry` 顶层导入
  `INTERPRETATION_BOUNDARY`。实测两者是**同名不同值**的两个常量：执行层为
  `"SYNTHETIC_TEST_ONLY: …"`，注册表快照层为 `"REGISTRY_METADATA_ONLY: …"`；同时导入会静默遮蔽其一。
  本设计要求：信封的 `metadata.interpretation_boundary` 必须取**执行层**（`SYNTHETIC_TEST_ONLY`）
  字面量；注册表限制语句若需要，必须以 `registry_snapshot.INTERPRETATION_BOUNDARY` 形式的
  显式别名引用，或直接不引用。
- I5：新模块不得定义任何统计、数值、质量判定或摘要算法；所有统计量必须来自
  `execute_bounded_analysis`，所有摘要必须来自既有 `canonical_digest` 或既有
  `compute_*_digest`。

### 4.2 唯一的编排入口

```python
def run_synthetic_pipeline(
    *,
    request: SyntheticPipelineRequestV1,
) -> SyntheticPipelineResultV1: ...
```

签名冻结约束：

- 仅一个参数 `request`，**关键字专用**（前置 `*`）。没有 `**kwargs`，没有可选位置参数。
- 因此 `run_synthetic_pipeline(config=...)`、`run_synthetic_pipeline(cfg, bound)`、
  任何含 `holdout=`、`window=`、`split=`、`real_data=`、`provider=`、`db=`、`path=`、`seed=`
  的调用都是 `TypeError`。**这是 holdout、真实数据、路径与 seed 的第一道拒绝：签名本身**。
- `request` 必须是 `SyntheticPipelineRequestV1` 实例；其他类型抛
  `PipelineError("PIPELINE_REQUEST_TYPE_INVALID")`（第 8.3 节错误表首行）。
- 编排器是**纯函数**：相同 `request` 必定返回字节相等的信封；不写文件、不读文件、
  不读环境变量、不读时钟、不使用全局可变状态、不使用随机数。

### 4.3 请求类型（拟议，不可变）

```python
@dataclass(frozen=True)
class SyntheticPipelineRequestV1:
    schema_version: str              # == PIPELINE_SCHEMA_VERSION
    orchestrator_version: str        # == ORCHESTRATOR_VERSION
    config: HypothesisConfig         # 既有类型；调用者提供
    bound_inputs: BoundDatasetInputsV1  # 既有类型；调用者提供的合成策略输入（第 5.3 节）
    registry_record: HypothesisRecordV1 | None  # 第 10 节；必填但可显式为 None，只读、非证据
```

约束：

- 五个字段全部必填（`registry_record` 显式可为 `None`；**不得**用"缺省键"代替显式 `None`，
  因为缺省键无法与"显式省略"区分，会破坏省略语义的可判定性）。
- `config` 与 `bound_inputs` 由调用者提供，但**不得**是伪造的上游产物：`bound_inputs` 中的
  `source_contract_digest` 与 `plan_digest` 必须等于编排器自己编译出的合同/计划摘要
  （第 6 节 S3）。
- `registry_record` 若提供，必须是 `HypothesisRecordV1` 实例且已通过
  `validate_hypothesis_record`；编排器**不**对其做任何状态转换。

### 4.4 结果信封与公开导出面（拟议，不可变）

```python
@dataclass(frozen=True)
class PipelineMetadataV1:
    orchestrator_version: str
    pipeline_schema_version: str
    pipeline_state: str
    stages_completed: tuple[str, ...]
    registry_binding: RegistryMetadataBindingV1 | None
    registry_binding_digest: str
    interpretation_boundary: str
    pipeline_digest: str

@dataclass(frozen=True)
class SyntheticPipelineResultV1:
    metadata: PipelineMetadataV1
    contract: FrozenMechanismContract
    plan: DeterministicAnalysisPlan
    preparation: DatasetPreparationV1
    matrix: MatrixPreparationV1
    execution: ExecutionArtifactV1

@dataclass(frozen=True)
class RegistryMetadataBindingV1:
    binding_state: str            # REGISTRY_BINDING_PRESENT
    hypothesis_id: str
    hypothesis_version: int
    record_identity_digest: str   # 既有 hypothesis_record_identity_digest 的值
    record_digest: str            # 既有 hypothesis_record_digest 的值
    record_status: str            # 绑定时记录的状态；只读快照，不是执行状态（第 10.4 节）
    record_bytes_hex: str         # 既有 serialize_hypothesis_record 规范字节的十六进制编码
```

**`record_bytes_hex` 的编码冻结（修正一处不可实现的早期草案）**：
`json.dumps` **不能**序列化 `bytes`（实测 `json.dumps({"k": b"x"})` → `TypeError`），
因此绑定字段**不得**声明为 `bytes`。冻结为：

- **J1**：`record_bytes_hex = serialize_hypothesis_record(record).hex()`，
  即既有规范字节的小写十六进制字符串；长度为 `2 × len(bytes)`，字符集 `[0-9a-f]`。
- **J2**：它是 `str`，因此可以进入规范 JSON；它**不含** `/`、不含禁止键、不匹配绝对路径模式，
  因此不会触发既有禁止内容检查。
- **J3**：它是**编码**而非重新序列化：`bytes.fromhex(record_bytes_hex)` 必须逐字节等于
  `serialize_hypothesis_record(record)`；实现**不得**美化解码或重新序列化。
- **J4**：任何**具体的**合法记录都必然序列化为**有限**字节，因此 `record_bytes_hex` 对每条实际
  绑定的记录都有限，长度恰为 `2 × len(serialize_hypothesis_record(record))`。但**上游 schema
  不对全体合法记录施加一致的有限上界**（修正一处不可成立的早期表述）：既有 M4-B 记录的
  `known_controls`、`known_alternative_explanations`、`known_replications`、`known_failures_or_decay`
  等**元组基数无上界**，`state_history` 长度无上界，`authorization_ref` 与 `schema_version` 也**没有**
  长度上限——逐字段文本上限（如 `NOTES_MAX_LEN = 4000`）只约束单个字段，不足以给出总上界。
  因此本设计**不冻结**任何"总字节上限"，也**不新增**任何编排器层尺寸门；实现评审只能把
  "有界文本骨架"的实测值记录为证据，**不得**把它表述为 schema 保证（第 14 节 R11）。

`pipeline/__init__.py` 拟议 `__all__`（**恰为**下列 20 个符号；本清单是唯一权威来源，
其计数与逐项枚举见下）：

```text
"ORCHESTRATOR_VERSION", "PIPELINE_DIGEST_ALGORITHM", "PIPELINE_SCHEMA_VERSION",
"PIPELINE_STAGE_SEQUENCE", "PIPELINE_STATE", "REGISTRY_BINDING_ABSENT",
"REGISTRY_BINDING_DIGEST_ALGORITHM", "REGISTRY_BINDING_PRESENT",
"REQUIRED_STAGES_COMPLETED", "SYNTHETIC_PIPELINE_MODE",
"PipelineError", "PipelineMetadataV1", "RegistryMetadataBindingV1",
"SyntheticPipelineRequestV1", "SyntheticPipelineResultV1",
"bound_inputs_identity_payload", "pipeline_result_to_canonical_dict",
"run_synthetic_pipeline", "serialize_pipeline_result", "validate_pipeline_result",
```

> 计数说明（唯一权威）：上列**恰为 20 个符号**。逐项枚举（10 个常量 + 10 个类/函数）：
> 4 个 `PIPELINE_*` 常量（`PIPELINE_DIGEST_ALGORITHM`、`PIPELINE_SCHEMA_VERSION`、
> `PIPELINE_STAGE_SEQUENCE`、`PIPELINE_STATE`）、`ORCHESTRATOR_VERSION`、
> `REGISTRY_BINDING_ABSENT`、`REGISTRY_BINDING_PRESENT`、`REGISTRY_BINDING_DIGEST_ALGORITHM`、
> `REQUIRED_STAGES_COMPLETED`、`SYNTHETIC_PIPELINE_MODE`（合计 10 个常量）；
> `PipelineError`、`PipelineMetadataV1`、`RegistryMetadataBindingV1`、
> `SyntheticPipelineRequestV1`、`SyntheticPipelineResultV1`、
> `bound_inputs_identity_payload`、`pipeline_result_to_canonical_dict`、
> `run_synthetic_pipeline`、`serialize_pipeline_result`、`validate_pipeline_result`（合计 10 个类/函数）。
> 注意：`SYNTHETIC_PIPELINE_MODE` 虽然以 `SYNTHETIC_PIPELINE_` 开头，但**不以** `PIPELINE_`
> 开头，因此 `PIPELINE_*` 前缀常量恰为 4 个。第 4.4 节冻结的是**集合**，实现不得增删任何一项。
>
> 实现验收与 AC-02 必须用**机器计数**断言该集合恰为 20 项，且逐项相等——不得只数前缀。

### 4.5 信封接口的精确签名

```python
def bound_inputs_identity_payload(
    contract: FrozenMechanismContract,
    plan: DeterministicAnalysisPlan,
    domain: ExpectedDomainV1,
    bindings: tuple[RoleBindingV1, ...],
    observations: tuple[ObservationV1, ...],
) -> dict: ...

def pipeline_result_to_canonical_dict(result: SyntheticPipelineResultV1) -> dict: ...
def serialize_pipeline_result(result: SyntheticPipelineResultV1) -> bytes: ...
def validate_pipeline_result(
    result: SyntheticPipelineResultV1,
    request: SyntheticPipelineRequestV1,
) -> None: ...
```

#### 4.5.1 `bound_inputs_identity_payload`：消除 `input_digest` 的无公开产出者问题

**问题（已实测确认）**：`BoundDatasetInputsV1.input_digest` 的**唯一**产出者是
`datasets/synthetic.py:417` 的**私有** `_input_payload`；`datasets/__init__.py` 的 `__all__`
不暴露任何构造器或摘要助手。三个既有测试模块直接导入该私有符号来构造合法 fixture
（`tests/test_m4_synthetic_dataset_adapter.py`、`tests/test_m4_analysis_matrix.py`、
`tests/test_m4_dataset_adapter_review.py`）。没有公开调用能返回正确值；`input_digest=""` 会以
`INPUT_DIGEST_MISMATCH` 失败。

**本设计的解决方式**：在新模块中提供一个**公开**的纯函数
`bound_inputs_identity_payload`，它返回**完全等于**既有 `_input_payload` 所返回的
规范化字典。这是本设计对 `input_digest` 归属的最终冻结：

- **A1**：它是**纯函数**，不接收也不返回 `BoundDatasetInputsV1`，不做 IO，不校验任何摘要。
- **A2**：返回字典必须与既有 `_input_payload(x)` 的结果**深度相等**，其中
  `x = BoundDatasetInputsV1(SCHEMA, "SYNTHETIC", contract.contract_digest, plan.plan_digest,
  domain, bindings, observations, <任意占位 input_digest>)`。
  实现评审必须用等价性测试逐键断言这一点。
- **A3**：调用者据此计算
  `input_digest = canonical_digest(bound_inputs_identity_payload(...))`，
  再构造 `BoundDatasetInputsV1`。这是调用者的责任，编排器**不代算**（否则"输入是否被改动"
  不可判定）。
- **A4**：本函数**只**是既有私有负载的公开再导出，**不得**引入任何新的规范化规则、
  排序规则或键名。既有 `_input_payload` 的观测排序键是
  `(trade_date, bindings 中的角色序)`；实现必须原样复制该语义。
- **A5**：本函数**不**构成对 `datasets/synthetic.py` 的修改：既有模块与其 `__all__` 一字不动；
  新增面只在新模块内。这满足第 4.1 节 I1。

**两遍调用协议（冻结）**：调用者**必须**按下列顺序构造请求，否则请求无法被构造出来：

```text
第一遍：contract = compile_hypothesis_config(config)      # 学到 contract.contract_digest
        plan     = build_analysis_plan(contract)          # 学到 plan.plan_digest
第二遍：input_digest = canonical_digest(
            bound_inputs_identity_payload(contract, plan, domain, bindings, observations))
        bound_inputs = BoundDatasetInputsV1(
            SCHEMA, "SYNTHETIC", contract.contract_digest, plan.plan_digest,
            domain, bindings, observations, input_digest)
        result = run_synthetic_pipeline(request=SyntheticPipelineRequestV1(...))
```

这是一处**有意接受**的重复编译：`contract`/`plan` 会被编译两次。理由是
`BoundDatasetInputsV1` 必须内嵌这两个摘要，而摘要只有在编译之后才存在。编排器**不得**
通过接受"未绑定输入"来消除这次重复（那会让编排器成为输入身份的权威，产生第二套
规范化权威，违反第 6.3 节与 I5）。调用者**可以**缓存第一遍的 contract/plan，
但即便复用它们，编排器仍会在 S1/S2 重新编译一次（第 6.2 节 P3 的既有链式重算）。

- `pipeline_result_to_canonical_dict` 返回**不含** `pipeline_digest` 的独立字典（自摘要不是
  自身摘要的输入）；返回的每个容器都是新建的，改动它不影响信封或任何后续序列化。
- `serialize_pipeline_result` 先验证再输出 UTF-8 规范 JSON：`ensure_ascii=False`、
  `sort_keys=True`、`separators=(",", ":")`，末尾**恰好一个** `\n`，与既有五个序列化器一致。
- `validate_pipeline_result` 是 I1–I6 的机械检查（第 9.5 节），必须重算信封摘要并比对。

---

## 5. 结果信封 schema 与规范序列化

### 5.1 规范字典的精确键序无关形态

`pipeline_result_to_canonical_dict` 返回下列键（键序由 `sort_keys=True` 决定，实现不得自定义）：

```text
metadata: {
  interpretation_boundary, orchestrator_version, pipeline_schema_version,
  pipeline_state, registry_binding, registry_binding_digest, stages_completed
}
contract:   <既有权威字典：contract_to_canonical_dict 的结果>
plan:       <既有权威字典：plan_to_canonical_dict 的结果>
preparation:<既有权威字典：dataset_to_canonical_dict 的结果>
matrix:     <既有权威字典：matrix_to_canonical_dict 的结果>
execution:  <既有权威字典：execution_artifact_to_canonical_dict 的结果>
```

结构性约束：

- **D1**：五个阶段对象的规范字典一律通过**既有**函数取得，编排器不得手写、不得重排、
  不得增删任何键。
- **D2**：`metadata.registry_binding` 为 `None`（省略）或第 10.2 节的绑定字典；
  没有第三种形态。
- **D3**：`metadata.pipeline_digest` **不**参与 `pipeline_digest` 的计算（自摘要排除规则）；
  其余全部字段（含 `metadata.registry_binding` 与 `registry_binding_digest`）都参与。
- **D4**：信封**不得**包含宿主信息、路径、会话、环境或选择/排序字段；被禁键集合是
  既有 `FORBIDDEN_KEYS` 的超集（第 5.5 节）。
- **D5**：`metadata.stages_completed` 成功时必须逐项等于 `REQUIRED_STAGES_COMPLETED`；
  不得出现部分完成的中间态取值。

### 5.2 规范序列化

```text
serialize_pipeline_result(result) ==
    json.dumps(pipeline_result_to_canonical_dict(result) | {"metadata.pipeline_digest": result.metadata.pipeline_digest},
               ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
```

> 上式为**语义等价写法**；实现必须先把 `pipeline_digest` 写回嵌套的 `metadata` 字典，
> 再整体 `json.dumps`。字节相等是验收项（AC-13），不是"看起来一样"。

### 5.3 谁是"合成策略输入"，谁是"上游产出对象"（冻结归属）

这是本设计消除编排歧义的核心划分。

| 对象 | 归属 | 理由与约束 |
| --- | --- | --- |
| `HypothesisConfig` | **调用者提供** | 假设的参数化声明；无法从空无中推导 |
| `BoundDatasetInputsV1` | **调用者提供** | 合成观测与域声明；适配器的签名要求它 |
| `FrozenMechanismContract` | 上游产出（S2） | 调用者不得手工构造后传入 |
| `DeterministicAnalysisPlan` | 上游产出（S3） | 同上 |
| `DatasetPreparationV1` | 上游产出（S4） | 同上 |
| `MatrixPreparationV1` | 上游产出（S5） | 同上 |
| `ExecutionArtifactV1` | 上游产出（S6） | 同上 |

`BoundDatasetInputsV1` 的字段与调用者责任（实测字段，实现不得增删）：

```text
BoundDatasetInputsV1(
  schema_version, mode, source_contract_digest, plan_digest,
  domain: ExpectedDomainV1, bindings: tuple[RoleBindingV1, ...],
  observations: tuple[ObservationV1, ...], input_digest)
```

调用者必须自行计算并被既有验证器校验的**四个**摘要负载（编排器**不代算**，因为代算会让
"输入是否被改动"不可判定；其中第 4 个由第 4.5.1 节的公开函数提供负载）：

| # | 摘要 | 精确计算式（实测） | 校验点 |
| --- | --- | --- | --- |
| 1 | `domain` 内 `calendar_evidence.evidence_digest` | `canonical_digest({"evidence_kind":"SYNTHETIC_CALENDAR_V1","domain_id","development_start","development_end","expected_dates":[list]})` | `synthetic.py` `ExpectedDomainV1.validate` |
| 2 | `domain` 内 `membership_evidence.evidence_digest` | `canonical_digest({"evidence_kind":"SYNTHETIC_FIXED_MEMBERSHIP_V1","universe_id","target_series_id","expected_dates":[list]})` | 同上 |
| 3 | 每个 `ObservationV1.evidence_digest` | `canonical_digest({"role","trade_date","value","available_on","source_record_id","binding":<RoleBindingV1 全字段字典>})` | `synthetic.py:_validate_inputs` |
| 4 | `input_digest` | `canonical_digest(bound_inputs_identity_payload(contract, plan, domain, bindings, observations))`（第 4.5.1 节公开函数；其返回字典含 7 键 `{schema_version, mode, source_contract_digest, plan_digest, domain, bindings, observations}`，观测按 `(trade_date, bindings 角色序)` 排序） | `synthetic.py:_validate_inputs` |

第 1–3 个摘要是**直接对 `canonical_digest` 的调用**，键集合如上（三个负载的键必须**精确**
等于所列键，多键或少键都会以 `EVIDENCE_DIGEST_MISMATCH` 失败）；第 4 个必须经由第 4.5.1 节的
公开函数，**不得**由调用者自行拼装（拼接错误会静默产生 `INPUT_DIGEST_MISMATCH`，而错误来源不可定位）。

三个嵌套类型的最小合法取值（实测，用于构造 fixture）：

```text
RoleBindingV1(role, series_id,
              value_semantics="DAILY_RETURN", unit="DECIMAL_RETURN",
              adjustment_policy="SYNTHETIC_DECLARED_RETURN",
              outcome_id=<TARGET_OUTCOME: contract.outcome.outcome_id；其余角色 None>,
              horizon="1D", observation_timing="CLOSE_TO_CLOSE")
ObservationV1(role, trade_date=<ISO，须在 domain.expected_dates 内>,
              value=<规范十进制字符串或 None>, available_on=<ISO 或 None>,
              source_record_id=<[A-Za-z0-9][A-Za-z0-9_.-]*>, evidence_digest=<负载 3>)
ExpectedDomainV1(domain_id, universe_id=contract.universe.universe_id,
                 membership_policy="SYNTHETIC_FIXED_UNIVERSE", pit_policy="EXPLICIT_PIT",
                 target_series_id=contract.target.series_id,
                 identity_policy="SYNTHETIC_FIXED_IDENTITY",
                 development_start=contract.development.start,
                 development_end=contract.development.end,
                 expected_dates=<非空、升序、去重 ISO 元组>,
                 calendar_evidence=<负载 1>, membership_evidence=<负载 2>)
```

注意：`expected_dates`（合成交易日历）**不能**从 `contract.development` 推导——合同只有起止
日期，没有日历。它是调用者声明的合成日历。`value` 必须是**规范**十进制字符串
（`-0.000` 会被判为 `INVALID_VALUE`，既有适配器不接受也不修复非规范值）。

编排器对 `bound_inputs` 的**唯一**责任是机械门禁（第 6 节 S3）：`schema_version` 必须等于
既有 `mechanism.datasets.synthetic.SCHEMA`；`mode` 必须等于 `SYNTHETIC_PIPELINE_MODE`；
`source_contract_digest` 必须等于自己编译的 `contract.contract_digest`；
`plan_digest` 必须等于自己编译的 `plan.plan_digest`。任一不等 => 稳定错误（第 8.3 节）。

补充冻结项：

- 编排器**不得**把 `bound_inputs` 以 `dict` 形式转发给适配器。既有
  `materialize_analysis_dataset` 接受 `BoundDatasetInputsV1 | dict`，但 `from_dict` 走的是
  `_keys(value, set(cls.__dataclass_fields__))` 的**精确键集**要求，多键少键都会以
  `INVALID_INPUT_STRUCTURE` 失败。为消除"同一请求两种转发形态可能给出不同首错"的歧义，
  请求类型字段声明为 `BoundDatasetInputsV1`，S0 门禁要求 `type(...) is BoundDatasetInputsV1`
  （G4）；未通过即 `PIPELINE_INPUT_TYPE_INVALID`。
- `request.config` 必须是**已解析的** `HypothesisConfig` 对象。编排器**不**接收 YAML/JSON 文档，
  也**不得**调用 `hypothesis_config.load_hypothesis_config(path)`（它接收 `str | Path` 并读取
  文件，会引入文件系统面，违反第 11.4 节 N3）。类型化解析由调用者在进入编排器之前完成；
  这保留了"typed hypothesis parsing"在链上，同时把 IO 面留在编排器之外。
- `HypothesisConfig` 虽可手工构造，但既有 `_validate_typed_config` 会把它重新解析并比对规范字典，
  不一致即 `NON_CANONICALIZABLE_VALUE`。编排器不捕获该错误，按第 8.4 节透传。

**合成观测的生成规则不在本设计内。** 本设计只冻结"调用者提供、且必须与冻结合同/计划摘要
一致"这一归属；具体合成数值由验收 fixture 提供，不得由编排器发明（否则会出现第二套事实来源）。

### 5.4 注册表元数据与执行证据的结构性分离

- 执行证据 = `result.execution`（既有 `ExecutionArtifactV1`），其内容与门禁完全由既有执行层决定。
- 注册表元数据 = `result.metadata.registry_binding`（第 10 节）。
- **两者不共享任何字段。** `registry_binding` 不出现在 `result.execution` 的任何嵌套位置；
  `result.execution` 的任何字段也不得由 `registry_binding` 派生。
- 注册表记录的 `status` 只作为**只读快照**出现在 `registry_binding.record_status`，
  不参与 `PIPELINE_STATE`、不参与 `stages_completed`、不参与 `execution_authorized`
  （后者由既有执行层恒为 `False`）。
- 省略语义：`registry_binding is None` 且 `registry_binding_digest == canonical_digest(
  {"binding_state": REGISTRY_BINDING_ABSENT})`。省略是**一等公民**，不是错误、不是缺省值填充。

### 5.5 禁止内容面（结构性）

信封的规范字典必须通过既有执行层的禁止内容检查语义（`_check_forbidden_content` 的等价规则），
即：

- 任何嵌套键（小写后）不得落在既有 `FORBIDDEN_KEYS` 中，至少包含：
  `cwd`、`worktree`、`hostname`、`username`、`user`、`home`、`abspath`、`absolute_path`、
  `root_path`、`env`、`environment`、`path`、`session`、`best`、`best_result`、`best_id`、
  `selected`、`selected_id`、`winner`、`aggregate`、`ranking`、`optimize`、`tuned`、`search`。
- 任何字符串值不得匹配绝对路径模式 `(?:[A-Za-z]:[\\/])|(?:\\\\)|(?:/[^/\s]+)`。
  **实测加强**：该模式会对**任何**含 `/` 且其后非空白的子串命中，因此 `"AND/OR"`、`"A/B"`、
  `"x y/z"` 都算命中；而 `"2015-03-16"`、`"SYNTH_ROBUSTNESS_1"`、`"A-B"` 不命中。
  该检查对**字符串值**递归生效，因此信封中不得出现任何含斜杠的字符串
  （含标签、说明、外部引用、参数值）。
- **D6**：编排器**不得**引入任何含 `/` 的字符串字段值。特别地，**既有合同声明的稳健性参数**
  （`robustness_registry` 的 parameters）被**逐字**转发进计划的 `robustness_plan.entries`，因而进入
  信封的 `plan` 权威投影，并被编排器 **V5** 的整信封禁止内容检查拒绝（实测：参数键 `"path"` 或
  参数值 `"A/B"` 使 `run_synthetic_pipeline` 在 S1–S6 **完整执行之后**以既有码
  `FORBIDDEN_ARTIFACT_CONTENT` 失败；`{"trim":"0.0100"}` 通过）。
  **修正一处与实测不符的表述**：既有**有界执行产物 payload 并不含稳健性块**——`_execution_payload`
  只有 `method_configuration`、`sample`、`estimator`、`bootstrap`、`conditional_descriptives`、
  `evidence` 等字段，因此 `execute_bounded_analysis` 在 `parameters={"trim":"A/B"}` /
  `{"path":"0.0100"}` 下**会成功**；本设计**不得**声称执行产物携带稳健性参数，也不得把该拒绝
  描述成执行器内部的扫描结果。稳健性派遣入口 `prepare_registered_robustness_dispatch` 有**自己的**
  既有扫描（`_check_robustness_artifact` → `_robustness_payload` → `_check_forbidden_content`，
  参数被逐字转发后受检），但该入口**不在**本设计的组合链上（第 6.2 节 P7、AC-23），
  其独立探针是 AC-17f。这属于**既有**行为，编排器不新增也不放宽该检查；验收必须分别覆盖
  这两条路径，以免把组合链上的 V5 拒绝误判为编排器引入的缺陷（AC-22d）。
- **D7**：注册表记录的**字节**（编码为 `registry_binding.record_bytes_hex`）是十六进制字符串，
  不参与字符串值扫描的"路径样式"命中（`[0-9a-f]` 不含 `/`、`\`、`:`）；
  但记录内**已解析**的文本字段若被编排器提升为信封字符串字段，就会重新进入扫描面。
  因此编排器**不得**把注册表文本字段复制成 `metadata` 的字符串字段，只允许第 10.2 节列举的
  固定键与其值（均为标识符、64 位十六进制、十六进制编码或既有枚举词）。
- 因此**拟议字段名必须避开上述词表**：本设计的 20 个公开符号与全部字段名已逐一比对通过
  （`registry_binding`、`record_bytes_hex`、`pipeline_digest` 等均不命中）。

---

## 6. 组合顺序与每阶段前后验证（冻结）

### 6.1 冻结步骤序列

下表是本设计的**核心冻结项**。步骤编号 `S0`–`S8` 是稳定标识。任一 `Si` 失败 =>
整个调用抛出该步的稳定错误，**不返回任何对象、不产生部分信封、不做降级或回退**。

| 步 | 名称 | 动作（精确） | 该步之前的验证 | 该步之后的验证 |
| --- | --- | --- | --- | --- |
| S0 | INTAKE | 校验 `request` 类型、`schema_version`、`orchestrator_version`、`registry_record` 类型，并对**入口可得投影**（可选注册表记录投影）检查禁止内容（G14） | 无（入口） | 无 |
| S1 | CONTRACT | `contract = compile_hypothesis_config(request.config)` | S0 已通过 | `validate_contract(contract)`（其内部已重算并比对 `contract_digest`） |
| S2 | PLAN | `plan = build_analysis_plan(contract)` | S1 已通过 | `validate_analysis_plan(plan)`；再比对 `compute_plan_digest(plan) == plan.plan_digest` 且 `plan.source_contract_digest == contract.contract_digest` |
| S3 | SYNTHETIC_INPUT | 对 `request.bound_inputs` 做机械门禁（第 5.3 节四项相等） | S2 已通过 | G7–G11 按第 7.1 节表序通过；失败使用第 8.3 节对应稳定码 |
| S4 | DATASET | `preparation = materialize_analysis_dataset(contract, plan, request.bound_inputs)` | S3 已通过 | `validate_dataset(preparation, contract, plan, request.bound_inputs)`；`execution_authorized is not False` 由既有 `AdapterError("INVALID_INPUT_STRUCTURE")` 拒绝；随后要求 `preparation.status == "READY_SYNTHETIC"`，否则 `PIPELINE_QUALITY_NOT_READY` |
| S5 | MATRIX | `matrix = materialize_design_matrix(preparation, contract, plan, request.bound_inputs)` | S4 已通过 | `validate_design_matrix(matrix, preparation, contract, plan, request.bound_inputs)` |
| S6 | EXECUTION | `execution = execute_bounded_analysis(matrix, preparation, contract, plan, request.bound_inputs)` | S5 已通过 | `validate_execution_artifact(execution, matrix, preparation, contract, plan, request.bound_inputs)` |
| S7 | ENVELOPE | 组装 `metadata` 与 `SyntheticPipelineResultV1`，计算 `registry_binding_digest`，再计算 `pipeline_digest` | S6 已通过 | `validate_pipeline_result(result, request)` |
| S8 | RETURN | 返回 `result` | S7 已通过 | 无（出口） |

### 6.2 顺序不变量

- **P1**：S1 之后必须先跑 `validate_contract`，再进入 S2。既有 `build_analysis_plan` 内部
  `_validated_contract_dict` 也会 `validate_contract` 并重编译比对，但编排器**不得**依赖下游
  替自己做本阶段的检查：每一步的后验验证是编排器自己的义务，也是首错**归属步骤**可判定的前提。
  编排器**不得**在 S1 额外重复"重编译一致性"检查（下游已有），以免放大第 11.3 节上界。
- **P2**：`build_analysis_plan` 会被下游多次重新调用（`_validate_inputs` 在
  `datasets/synthetic.py:437` 起重新 `build_analysis_plan` 并序列化比对）。这是既有的
  链式重算，编排器**不得**用缓存去"优化"掉它。
- **P3**：S4 的 `validate_dataset` 会再次完整重算适配器输出。这意味着一次成功调用中
  `materialize_analysis_dataset` 至少被调用 2 次、`build_analysis_plan` 至少被调用 3 次、
  矩阵投影至少被调用 3 次、`_execute` 至少被调用 2 次（V3 重执行）——全部由既有验证器触发，
  不是本设计新增。实测总计数（含编排器 S2/S4 直调与全部链式重算，且计入 S7
  `validate_pipeline_result` V2 重跑的额外一轮）见第 11.3 节：`build_analysis_plan = 12`、
  `materialize_analysis_dataset = 11`、`_execute = 3`。
- **P4**：`preparation.status != "READY_SYNTHETIC"` 时必须在 S4 之后、S5 之前终止，
  不得进入矩阵与执行。**这条编排器自判不是冗余，而是必需**：实测显示，若把质量拒绝的
  preparation 交给下游，`validate_design_matrix` 会在 `X2` 内先抛既有的
  `MatrixError("DATASET_NOT_READY")`，而执行层那个**携带处置词**的
  `ExecutionError("DATA_QUALITY_REJECTED", disposition=...)` 在组合链上**不可达**。
  为保留既有执行层的处置语义（`FAIL` / `INCONCLUSIVE`），编排器必须在 S4 后自己判定并以
  `PIPELINE_QUALITY_NOT_READY` 终止，消息中携带计划声明的
  `evidence_plan.data_quality_failure_disposition`。**不得**把 `DATA_QUALITY_REJECTED`
  写成组合入口的预期首错。
- **P4b**：同理，`ExecutionError("UNSUPPORTED_DATASET_MODE")` 与执行层行级
  `HOLDOUT_NOT_AUTHORIZED` 在组合链上同样被上游 `X2` 抢先（前者被适配器
  `AdapterError("UNSUPPORTED_MODE")` 取代，后者被合同/计划层的开发期-holdout 不相交校验取代）。
  这些码属于**纵深防御**，设计**不得**把它们声明为组合入口的可达首错；编排器的 S3 门禁
  （`PIPELINE_UNSUPPORTED_MODE`）位于最前，是唯一可达的 mode 拒绝面。
- **P5**：`execution.statistics_computed` 与 `execution.outcome_read` 必须为 `True`，
  `execution.execution_authorized` 必须为 `False`；这三项由既有 `_check_execution_artifact`
  强制，编排器不得改写。
- **P6**：编排器**不得**在 S0–S6 之间插入任何统计计算、插值、修复、重采样、平滑或
  数据补齐。任何"让数据通过质量门"的行为都属于复制统计实现，被第 1.2 节第 5 条禁止。
- **P7**：编排器不得调用 `prepare_registered_robustness_dispatch`。稳健性派遣是既有执行层的
  独立入口，其语义是"只派遣不计算"；把它接进端到端链会改变本设计的证据形状。若后续需要，
  必须另行授权（第 14.2 节 R5）。

### 6.3 不得绕过既有验证器（结构性，而非约定）

- 编排器**不得**直接调用 `_project_validated_matrix`、`_validated_source`、`_execute`、
  `_with_digest`、`_with_matrix_digest`、`_input_payload`、`_domain_dict` 等任何私有函数。
  它们是 `_` 前缀私有实现，不是**编排器**的 acceptance 入口。**唯一例外是验收测试的显式探针**：
  配套验收文档第 1.2 节允许测试在显式标注 `INTERNAL_PROJECTION_PROBE` 后直接调用
  `_project_validated_matrix` 来证明下游项角色防御（AC-17e）；编排器本身**仍不得**调用它。
- 编排器**不得**用 `dataclasses.replace` 改写任何上游产物后继续传递。上游产物一旦产出即不可变；
  唯一允许的 `replace` 在既有模块内部。
- 编排器**不得**自行实现质量门、覆盖门、秩门或处置逻辑；这些全部由既有适配器与执行器给出。

### 6.4 不可变性与"无部分结果"

- **E7**：`SyntheticPipelineRequestV1`、`SyntheticPipelineResultV1`、`PipelineMetadataV1`、
  `RegistryMetadataBindingV1` 全部 `frozen=True`，字段类型不得含 `dict`、`list`、`set` 或
  可变的嵌套 dataclass。
- **E8**：失败路径不返回任何对象。编排器不得返回 `None`、空信封或"带错误字段的信封"。
  没有 `result.errors`、没有 `result.partial`、没有 `ok` 标志位——**错误只以异常表达**。
- **E9**：`pipeline_result_to_canonical_dict` 与 `serialize_pipeline_result` 返回的容器是新建的，
  改动它不得改变 `result` 或任何后续序列化结果。

---

## 7. 来源与授权门禁

### 7.1 门禁清单（在任何计算之前）

S0–S3 构成"计算之前"的门禁区。下面每一条都在**任何统计计算之前**求值：

| # | 门禁 | 拒绝条件 | 错误 |
| --- | --- | --- | --- |
| G1 | 请求形态 | `request` 非 `SyntheticPipelineRequestV1` | `PIPELINE_REQUEST_TYPE_INVALID` |
| G2 | 版本常量 | `schema_version` / `orchestrator_version` 不符 | `PIPELINE_VERSION_UNSUPPORTED` |
| G3 | 配置形态 | `config` 非 `HypothesisConfig` | `PIPELINE_CONFIG_TYPE_INVALID` |
| G4 | 输入类型 | `bound_inputs` 非 `BoundDatasetInputsV1` | `PIPELINE_INPUT_TYPE_INVALID` |
| G5 | 注册表形态 | `registry_record` 既非 `None` 也非 `HypothesisRecordV1` | `PIPELINE_REGISTRY_RECORD_INVALID` |
| G6 | 注册表自洽 | `validate_hypothesis_record` 失败 | `PIPELINE_REGISTRY_RECORD_INVALID` |
| G7 | 合成模式 | `bound_inputs.mode != "SYNTHETIC"` | `PIPELINE_UNSUPPORTED_MODE` |
| G8 | 输入 schema | `bound_inputs.schema_version` 与既有 `SCHEMA` 不符 | `PIPELINE_INPUT_SCHEMA_UNSUPPORTED` |
| G9 | 合同绑定 | `bound_inputs.source_contract_digest != contract.contract_digest` | `PIPELINE_INPUT_BINDING_MISMATCH` |
| G10 | 计划绑定 | `bound_inputs.plan_digest != plan.plan_digest` | `PIPELINE_INPUT_BINDING_MISMATCH` |
| G11 | 资源上界 | 计划声明 `bootstrap_plan.enabled is True` **且** `bootstrap_plan.replications > MAX_BOOTSTRAP_REPLICATIONS`（S3 内、G10 之后求值，第 11.3.1 节）；`enabled is False` 时本条**不求值**（禁用 bootstrap 没有重采样工作，其惰性 `replications` 声明不被拒绝，与 AC-28d 一致） | `PIPELINE_REPLICATIONS_EXCEED_LIMIT` |
| G12 | 注册表身份 | 记录 `hypothesis_id` 与计划 `hypothesis_id` 不等（S7 求值，第 14 节 R15 的分工） | `PIPELINE_REGISTRY_IDENTITY_MISMATCH` |
| G13 | 注册表状态 | 记录 `status` 不在第 10.4 节允许表内（S7 求值） | `PIPELINE_REGISTRY_STATUS_NOT_BINDABLE` |
| G14 | 禁止内容 | S0（仅扫入口可得投影）或 V5/S7（整信封规范字典）的禁止内容检查命中 | 既有 `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")`（**既有类型 + 既有码**；不新增第 15 个编排器码） |

门禁求值时机（`S0` / `S3` / `S7`）是**冻结**的：S0 只做形态、类型与**入口可得投影**的禁止内容
检查；S3 按 G7–G11 依次做 mode、schema、输入绑定与资源上界；S7 做注册表身份与状态。
实现**不得**把 S7 的检查提前到 S0，否则会改变首错归属（第 14 节 R15）。

**S0 禁止内容检查的精确扫描目标（修正一处不可实现的早期表述）**：既有
`_check_forbidden_content` 只作用于**执行/稳健性产物 payload**，且它是私有函数。
早期草案把 `contract_to_canonical_dict(contract)` 与 `plan_to_canonical_dict(plan)` 列为 S0 的扫描面，
这与第 6.1 节的步骤序**矛盾**：**S0 早于 S1/S2，contract 与 plan 在 S0 尚不存在**（它们分别在
S1/S2 才由编排器编译出来）。因此 S0 的扫描面被精确冻结为**入口处已存在的请求投影**：

1. `registry_record` 经 `hypothesis_record_to_canonical_dict(record)`（公开，仅当提供记录时）。

`contract_to_canonical_dict(contract)` 与 `plan_to_canonical_dict(plan)` **不在** S0 扫描面内；
它们的投影——连同 `preparation`/`matrix`/`execution` 的权威投影——由 **V5 在 S7 对完整规范信封
字典**一次性扫描（第 9.5 节 V5；实测该字典逐字包含 contract 与 plan 的投影）。`bound_inputs`
同样**不在**任何扫描面内——既有 `datasets/synthetic.py` 没有公开的字典投影，
而本设计禁止调用私有 `_input_payload`/`_domain_dict`（第 6.3 节）。`bound_inputs` 的字段合法性
完全由既有适配器的 fail-closed 校验负责（`_shape`/`_identifier`/`_hash`/`_date`/`_dec`），
其字符串值也是 `_identifier` 约束的 `[A-Za-z0-9][A-Za-z0-9_.-]*`，**结构上不可能**含 `/`。
S0 与 V5 命中时都以**既有** `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")` 终止
（既有类型 + 既有码），因此 G14 **不**引入第 15 个编排器错误码，也不改变 AC-16 的首错归属。

### 7.2 门禁的排序（首错确定性）

G1–G14 的求值顺序**就是**上表行序。实现不得重排、不得并行、不得"收集全部错误再挑一个"。
每个门禁必须在**前一个通过之后**才求值（短路求值），因此任一请求恰有一个首错。
G7–G11 都在 S3 内按表中行序求值；G12/G13 在 S7 求值。**行序与时序共同构成唯一规范**：
同一时刻内按行序，跨时刻按 `S` 步序（第 6.1 节）。

### 7.3 holdout、真实数据与路径：结构性不可表达

- **holdout**：`run_synthetic_pipeline` 只有一个关键字参数 `request`，请求类型没有 holdout 字段。
  传 `holdout=` 是 `TypeError`。计划层另有 `HOLDOUT_NOT_AUTHORIZED` fail-closed 门
  （既有执行层 X5），编排器不重复实现但**必须**让它自然生效。
- **真实数据/provider/数据库/行情**：编排器不导入 `duckdb`、`requests`、`urllib`、`socket`、
  `subprocess`、`os`、`pathlib`、`io`（第 4.1 节 I4），因此没有可表达真实数据访问的符号面。
- **路径**：编排器不导入 `pathlib`/`os`，不接收任何路径参数；且禁止内容检查会拒绝任何
  含绝对路径模式的字符串值。
- **seed**：请求类型没有 seed 字段；seed 只来自合同→计划固化的 bootstrap 声明（第 2.5 节）。

---

## 8. 首错顺序、稳定错误码与异常映射

### 8.1 首错的定义

一次 `run_synthetic_pipeline` 调用的**首错**是：按第 6.1 节 `S0 → S8` 步骤顺序、在每个步骤内
按第 7.2 节门禁顺序求值，**第一个**失败点抛出的错误。编排器必须在首个失败点立即抛出，
不得继续执行、不得收集多个错误、不得返回部分结果。

### 8.2 编排器自己的错误类型

```python
class PipelineError(ValueError):
    def __init__(self, code: str, message: str | None = None) -> None: ...
    self.code: str
```

与既有错误类型的关系（**实测，逐项**）：

| 来源 | 类型 | 是否带 `.code` |
| --- | --- | --- |
| `hypothesis_config.HypothesisConfigError` | `ValueError` 子类 | **是** |
| `contract_compiler.ContractCompilationError` | `ValueError` 子类 | **是** |
| `datasets.synthetic.AdapterError` | `ValueError` 子类 | **是** |
| `planning.matrix.MatrixError` | `ValueError` 子类 | **是** |
| `execution.bounded.ExecutionError` | `ValueError` 子类 | **是**（并另带 `.disposition`） |
| `planning/compiler.py` 的 44 个码 | **裸 `ValueError`**（`_require` → `raise ValueError(message)`） | **否**：`hasattr(exc, "code") is False`，`str(exc)` 就是码 |

**统一提取规则**：`getattr(exc, "code", str(exc))`（见第 8.6 节）。
`planning/compiler.py` **没有**自定义异常类，其码**只**由异常消息承载。
编排器**不得**写 `except ValueError as exc: exc.code`——对计划阶段的码会 `AttributeError`。

### 8.3 编排器自有错误码（增量为零语义）

编排器拥有下列封闭的 14 个错误码。除它们之外的任何失败都必须以**既有错误类型与既有错误码**
原样向上传播（`raise` 不包装、不改码、不改消息）。

| 码 | 触发步骤 | 精确触发条件 |
| --- | --- | --- |
| `PIPELINE_REQUEST_TYPE_INVALID` | S0 | `request` 类型不符 |
| `PIPELINE_VERSION_UNSUPPORTED` | S0 | `schema_version` 或 `orchestrator_version` 不符 |
| `PIPELINE_CONFIG_TYPE_INVALID` | S0 | `config` 类型不符 |
| `PIPELINE_INPUT_TYPE_INVALID` | S0 | `bound_inputs` 类型不符 |
| `PIPELINE_REGISTRY_RECORD_INVALID` | S0 | `registry_record` 类型不符或 `validate_hypothesis_record` 失败 |
| `PIPELINE_INPUT_SCHEMA_UNSUPPORTED` | S3 | `bound_inputs.schema_version` 不符 |
| `PIPELINE_UNSUPPORTED_MODE` | S3 | `bound_inputs.mode != "SYNTHETIC"` |
| `PIPELINE_INPUT_BINDING_MISMATCH` | S3 | 合同摘要或计划摘要不符 |
| `PIPELINE_QUALITY_NOT_READY` | S4 | `preparation.status != "READY_SYNTHETIC"`（第 6.2 节 P4） |
| `PIPELINE_REPLICATIONS_EXCEED_LIMIT` | S3（G10 之后） | 计划声明 `bootstrap_plan.enabled is True` 且 `bootstrap_plan.replications > MAX_BOOTSTRAP_REPLICATIONS`（第 11.3.1 节 R17.2）；`enabled is False` 时本条不适用 |
| `PIPELINE_REGISTRY_STATUS_NOT_BINDABLE` | S7 | 记录 `status` 不在第 10.4 节的**可绑定状态允许表**内 |
| `PIPELINE_REGISTRY_IDENTITY_MISMATCH` | S7 | 记录 `hypothesis_id` 与计划不等 |
| `PIPELINE_DIGEST_MISMATCH` | V6 | 信封自摘要与按 L14 重算值不符 |
| `PIPELINE_INTERNAL_SOURCE_UNMAPPED` | 任意 | 见第 8.7 节：无法归属到既有码的非 `ValueError` 异常 |

> 计数说明（唯一权威）：上表恰为 14 行，全部属于编排器的封闭错误表；其中
> `PIPELINE_INTERNAL_SOURCE_UNMAPPED` 是唯一兜底码。编排器**不得**新增其他码。
> `PIPELINE_QUALITY_NOT_READY` 是 S4 的**唯一**预期首错；下游既有的
> `MatrixError("DATASET_NOT_READY")` 只是"编排器漏判"时的二次防线，不构成并行的预期答案。
>
> `PIPELINE_QUALITY_NOT_READY` 的**消息模板（冻结）**：
> `"preparation status is not READY_SYNTHETIC; data_quality_failure_disposition=<WORD>"`
> 其中 `<WORD>` 逐字取自 `contract.evidence_rule.data_quality_failure_disposition`
> （既有封闭词表 `{"FAIL", "INCONCLUSIVE"}`）。该模板使 AC-06 的断言可机械检查，
> 并在既有 `ExecutionError.disposition` 于组合链上不可达时（第 8.5 节）保留处置语义。

### 8.4 既有错误码的透传（不得改写）

以下是编排链上**可能**出现的既有码（含只在阶段级探针上可达者，可达面以第 8.5 节为准），
**必须原样透传**。编排器不得把它们改写成 `PIPELINE_*`，也不得改变其类型：

| 步骤 | 既有错误类型 | 代表性既有码（非穷举，实现以既有模块为准） |
| --- | --- | --- |
| S1 | `ContractCompilationError` / `HypothesisConfigError` | `INVALID_CONTRACT_TYPE`、`INVALID_CONTRACT_SCHEMA_VERSION`、`INVALID_CONTRACT_STATE`、`CONTRACT_DIGEST_MISMATCH`、`DEVELOPMENT_HOLDOUT_OVERLAP`、`INVALID_IDENTITY_POLICY`、`UNSUPPORTED_FACTOR_KIND` |
| S2 | `ValueError`（`_require`） | `INVALID_PLAN_VERSION`、`INVALID_PLAN_STATE`、`UNSUPPORTED_ANALYSIS_METHOD`、`INVALID_PLAN_DIGEST_ALGORITHM`、`INVALID_SOURCE_SCHEMA`、`INVALID_SOURCE_IDENTITY`、`INVALID_HYPOTHESIS_ID`、`PLAN_DIGEST_MISMATCH`、`INVALID_DATASET_ROLES`、`INVALID_SECTION_FIELDS` |
| S3/S4 | `AdapterError` | `INVALID_INPUT_STRUCTURE`、`INVALID_DATE`、`INVALID_VALUE`、`UNSUPPORTED_MODE`、`CONTRACT_PLAN_MISMATCH`（其中 `UNSUPPORTED_MODE` 与 `CONTRACT_PLAN_MISMATCH` 在组合入口上不可达，实际可达面见第 8.5 节）、`ROLE_BINDING_MISMATCH`、`UNSUPPORTED_BINDING_POLICY`、`UNSUPPORTED_OUTCOME`、`EMPTY_EXPECTED_DOMAIN`、`EVIDENCE_DIGEST_MISMATCH`、`DUPLICATE_OBSERVATION`、`OUT_OF_DOMAIN`、`IDENTITY_CONFLICT`、`INPUT_DIGEST_MISMATCH` |
| S5 | `AdapterError` / `MatrixError` | 上游全部 + `UNSUPPORTED_PLAN_SCHEMA`、`PLAN_TERM_ROLE_MISMATCH`（其实际可达面见第 8.5.2 节：只在内部投影探针上命中，组合入口不可达）、`DATASET_NOT_READY`、`MATRIX_DIGEST_MISMATCH`、`IDENTITY_CONFLICT` |
| S6 | `ExecutionError`（含上游透传） | `SINGULAR_DESIGN`（满秩门失败）、`UNSUPPORTED_ANALYSIS_METHOD`、`UNSUPPORTED_MODEL_FAMILY`、`ARTIFACT_DIGEST_MISMATCH`、`FORBIDDEN_ARTIFACT_CONTENT`、`IDENTITY_CONFLICT`，以及第 8.5 节的不可达码 |

### 8.5 组合链上**可达**与**不可达**的既有码

本节的分类是**入口级**的：只有能由 `run_synthetic_pipeline(request=...)` 触发的码才算
"组合入口可达"；需要把调用者伪造的**上游对象**直接交给阶段函数的码属于"仅阶段级探针可达"；
更早的上游步骤拦截同一条件的码属于"不可达（纵深防御）"。**任何码都不得被描述成组合入口的
预期首错，除非它能由请求类型实际表达**（请求类型只有 `config`/`bound_inputs`/`registry_record`）。

#### 8.5.1 组合入口可达的既有码（可作为预期首错）

实测（只读探针 + 既有控制流）确认下列既有码**可以**成为组合入口的首错：

| 步骤 | 既有码 | 触发条件 |
| --- | --- | --- |
| S1 | `HypothesisConfigError` 全部 30 个码（经 `compile_hypothesis_config` 的动态透传）、`NON_CANONICALIZABLE_VALUE`、`INVALID_CONFIG_TYPE` | 配置层不合法 |
| S1 | `CONTRACT_DIGEST_MISMATCH`、`INVALID_CONTRACT_SCHEMA_VERSION`、`INVALID_CONTRACT_STATE`、`INVALID_CONTRACT_TYPE`、`DEVELOPMENT_HOLDOUT_OVERLAP` | 合同自摘要/状态/开发-holdout 重叠（由调用者提供的 `config` 驱动） |
| S2 | `NON_CANONICAL_CONTRACT`、`UNSUPPORTED_ANALYSIS_METHOD`（计划层）、`INVALID_PLAN_STATE`、`INVALID_PLAN_VERSION`、`INVALID_FIELD_TYPE`、`PLAN_DIGEST_MISMATCH`、`INVALID_SOURCE_IDENTITY`、`INVALID_HYPOTHESIS_ID` 等计划层裸 `ValueError` 码 | 合同被重写摘要后仍不自洽、或计划层结构问题 |
| S4 | `ROLE_BINDING_MISMATCH`、`UNSUPPORTED_BINDING_POLICY`、`UNSUPPORTED_OUTCOME`、`EMPTY_EXPECTED_DOMAIN`、`DUPLICATE_OBSERVATION`、`OUT_OF_DOMAIN`、`IDENTITY_CONFLICT`（适配器）、`EVIDENCE_DIGEST_MISMATCH`、`INPUT_DIGEST_MISMATCH`、`INVALID_DATE`、`INVALID_VALUE` | 合成输入不合法（**不含** `UNSUPPORTED_MODE`——那被编排器 S3 门禁抢先） |
| S5 | `MATRIX_DIGEST_MISMATCH`、`UNSUPPORTED_PLAN_SCHEMA`、`UNSUPPORTED_TERM_ROLE`、`INVALID_INPUT_STRUCTURE`（矩阵层） | 矩阵不合法 |
| S6 | `INSUFFICIENT_REPLICATIONS`（实测可达：`replications=1` + `enabled=true`）、`CELL_OUT_OF_RANGE`、`NON_FINITE_CELL`、`SINGULAR_DESIGN`、`SINGULAR_RESAMPLE`、`BOOTSTRAP_FAILURE`、`NON_FINITE_ESTIMATE`、`ESTIMATOR_FAILURE`、`INVALID_INTERVAL_ORDER`、`FORBIDDEN_ARTIFACT_CONTENT`、`IDENTITY_CONFLICT`（执行层） | 数值/资源/内容问题 |

#### 8.5.2 不可达的既有码（纵深防御，**不得**作为预期首错）

实测表明，下列码在**组合入口**上永远不会成为首错：或者更早的上游步骤已经拦截同一条件，
或者该条件需要调用者伪造上游对象、而请求类型无法表达它。

| 既有码 | 被谁抢先 / 为何不可达 | 抢先点或可达面 |
| --- | --- | --- |
| `AdapterError("UNSUPPORTED_MODE")` | 编排器 `PIPELINE_UNSUPPORTED_MODE` | 本设计 S3 门禁（G7）前置于适配器 |
| `ExecutionError("UNSUPPORTED_DATASET_MODE")` | 同上（更深一层：`X2` 也先于 `X5`） | 执行层 `X2` → `validate_design_matrix` → 适配器 |
| `ExecutionError("DATA_QUALITY_REJECTED", disposition=…)` | 编排器 `PIPELINE_QUALITY_NOT_READY`（本设计，第 6.2 节 P4）或下游 `MatrixError("DATASET_NOT_READY")` | 矩阵 `_project_validated_matrix` 的 ready 判定 |
| `ExecutionError("HOLDOUT_NOT_AUTHORIZED")`（行级窗口） | 合同/计划层的开发期-holdout 不相交校验 | `validate_contract` 的 `DEVELOPMENT_HOLDOUT_OVERLAP` |
| 计划层 `HOLDOUT_EXECUTION_NOT_AUTHORIZED`、`NON_CANONICAL_HOLDOUT`、`INVALID_ABSENT_HOLDOUT` | `AdapterError("CONTRACT_PLAN_MISMATCH")`（仅消息保留原码字面量） | 适配器 `_validate_inputs` 把计划重编译差异统一映射 |
| `ExecutionError("UNSUPPORTED_ANALYSIS_METHOD")`、`UNSUPPORTED_MODEL_FAMILY` | 计划层同名/同类检查（S2） | `_validated_contract_dict` 的 `UNSUPPORTED_ANALYSIS_METHOD` |
| `UNSUPPORTED_BOOTSTRAP_METHOD`、`UNSUPPORTED_BOOTSTRAP_RNG` | 配置层 `INVALID_BOOTSTRAP_POLICY` / 计划层 `INVALID_BOOTSTRAP_SEMANTICS`（S1/S2） | 合同与计划的 bootstrap 允许表 |
| `UNSUPPORTED_EVIDENCE_DIRECTION` | 配置层 `INVALID_EVIDENCE_RULE` / 计划层 `INVALID_EVIDENCE_BOUNDARY` | 同上 |
| `BLOCK_LENGTH_EXCEEDS_ROWS` | 计划层 `INVALID_SAMPLE_BOUNDARY` / 适配器质量门 | 块长策略 ≤ 20，样本下界由计划与质量门保证 |
| `MISSING_REQUIRED_STATISTIC_ROLE`、`INVALID_CONDITION_INDICATOR` | 计划层 `INVALID_EVIDENCE_STATISTICS` / `INVALID_CONDITION_*` | 计划阶段已固定统计角色与条件编码 |
| `ARTIFACT_DIGEST_MISMATCH` | — | **注意**：它在 `validate_execution_artifact` 的 V1 内求值，位于 S6 的**后验**验证中，因此**可以**在调用者提交被篡改的 `result` 经 V2 时出现（见 AC-15a）；它**不**是 `run_synthetic_pipeline` 的首错，但**是** `validate_pipeline_result` 的合法错误 |
| `MatrixError("DATASET_NOT_READY")` | 编排器 `PIPELINE_QUALITY_NOT_READY` | 第 6.2 节 P4 |
| `CONTRACT_PLAN_MISMATCH` | 组合入口上该条件**不成立**：合同与计划都由编排器在 S1/S2 自行编译，适配器在 S4 的重编译比对不可能发现不一致（同一条件若由调用者制造，早在 S3 就被 G9/G10 以编排器自有码拦下） | **信封层**可达：把伪造的 `result`（其 `contract`/`plan` 互不一致）交给公开的 `validate_pipeline_result`，V2 的 `validate_dataset` 会命中它；此外公开阶段验证器（把伪造计划交给 `validate_design_matrix`）也命中。它同时是 `PLAN_TERM_ROLE_MISMATCH` 的抢先者 |
| `PLAN_TERM_ROLE_MISMATCH` | `CONTRACT_PLAN_MISMATCH`（适配器 `_validate_inputs` 的重编译比对，S4） | 早于矩阵项角色投影（S5）。组合入口**不可达**（请求类型不能提交伪造的 `plan`/`preparation`/`matrix`）；只能由显式标注的**内部/阶段投影探针**证明——即直接调用矩阵投影助手 `_project_validated_matrix`（第 6.3 节禁止编排器调用任何私有助手，但验收测试可以显式标注并使用它）。AC-17e 按此标注 |
| `EMPTY_ROBUSTNESS_DISPATCH`、`DUPLICATE_ROBUSTNESS_ID`、`UNREGISTERED_ROBUSTNESS_ID`、`UNSUPPORTED_ROBUSTNESS_METHOD` | 不适用 | 稳健性派遣**不在**本设计的组合链上（第 6.2 节 P7），因此其全部码都不可达；其内容扫描只在该独立入口自己的探针上出现（AC-17f） |

唯一例外：`ExecutionError.disposition` 字段只在 `DATA_QUALITY_REJECTED` 上被填充，因此本设计在
`PIPELINE_QUALITY_NOT_READY` 的消息中**显式携带**同一个处置词（第 8.3 节消息模板），
以保留既有语义而不依赖不可达路径。

### 8.6 错误码提取的唯一正确方式

实测：`planning/compiler.py` 的 44 个错误码是**裸 `ValueError`**，**没有** `.code` 属性，
`str(exc)` 就是码本身；而五个自定义异常类都有 `.code`，且**当消息非空时 `str(exc)` 不是码**
（例如 `ExecutionError("INVALID_INPUT_STRUCTURE", "cells must be canonical")` 的
`str(exc)` 为 `"cells must be canonical"`）。因此：

- 调用方（与后续验收）提取错误码的**唯一**正确方式是
  `getattr(exc, "code", str(exc))`。
- **不得**用 `str(exc)` 直接当码，也不得假设 `.code` 一定存在。
- 区分"裸 `ValueError`（计划模块）"与"带 `.code` 的既有异常"只能靠
  `type(exc).__name__`，编排器**不**做这种区分（按 M1 一律原样透传）。

### 8.7 异常映射规则（唯一兜底）

- **M1**：既有 `ValueError` 子类（含上表全部）一律**原样传播**：不改类型、不改 `.code`、
  不改 `str(exc)`。`raise` 而非 `raise PipelineError(...) from exc`。
- **M2**：`TypeError` 只在 S0 的门禁处被显式判定（G1/G3/G6）；门禁通过后不得再出现
  `TypeError`。若出现，属于既有模块的缺陷，按 M4 处理并记录，不得静默吞掉。
- **M3**：`KeyError`、`AttributeError`、`IndexError`、`AssertionError`、`ZeroDivisionError`
  在既有模块中**不应**出现（既有验证器以 `_shape`/`_keys` fail-closed 前置）。若出现，
  说明存在未映射的裸异常点，编排器**不得**用 `except Exception` 吞掉。唯一允许的处理是：
  记录该异常的类型与消息来源，按第 14 节 R1 作为设计缺陷上报，并在该次调用中
  以 `PipelineError("PIPELINE_INTERNAL_SOURCE_UNMAPPED")` 终止（`raise ... from exc`
  保留原始链）。实现**不得**扩大兜底范围。
- **M4**：`numpy.linalg.LinAlgError` 等数值异常由既有执行器内部处理或转化为既有码；
  编排器不新增捕获。
- **M5**：编排器**不得**捕获 `BaseException`、不得捕获裸 `Exception`、不得使用
  `contextlib.suppress`、不得重试（无 retry 循环）。

---

## 9. 跨产物绑定：精确摘要链与篡改检测

### 9.1 摘要链（L1–L14：十四个链接，其中六个构成执行层的身份字段串）

下表是**精确**的链式绑定。`D` 表示 `canonical_digest`（既有
`mechanism.model_digest.canonical_digest`，SHA-256 over
`json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",",":"))`）。

| # | 链接 | 产出者 | 字段 | 摘要公式 | 排除项 |
| --- | --- | --- | --- | --- | --- |
| L1 | 源配置 → 合同 | `compile_hypothesis_config` | `contract.source_config_digest` | `D(config_to_canonical_dict(config))` | 无 |
| L2 | 合同自摘要 | `compile_hypothesis_config` | `contract.contract_digest` | `D(contract_to_canonical_dict(c) 去掉 contract_digest)` | `contract_digest` |
| L3 | 合同 → 计划 | `build_analysis_plan` | `plan.source_contract_digest` | 复制 `contract.contract_digest` | — |
| L4 | 计划自摘要 | `build_analysis_plan` | `plan.plan_digest` | `D(plan_to_canonical_dict(p) 去掉 plan_digest)` | `plan_digest` |
| L5 | 计划 → 输入 | 调用者 | `bound_inputs.plan_digest` | 复制 `plan.plan_digest`（编排器在 S3 校验） | — |
| L6 | 输入自摘要 | 调用者 | `bound_inputs.input_digest` | `D(bound_inputs_identity_payload(contract, plan, domain, bindings, observations))`（第 4.5.1 节；与既有 `_input_payload` 深度相等） | 无 |
| L7 | 域摘要 | 适配器 | `preparation.domain_digest` | `D(_domain_dict(x.domain))` | 无 |
| L8 | 准备数据自摘要 | 适配器 | `preparation.dataset_digest` | `D(dataset_to_canonical_dict(p) 去掉 dataset_digest)` | `dataset_digest` |
| L9 | 计划 → 矩阵 | 矩阵构建器 | `matrix.plan_digest` | 复制 `preparation.plan_digest` | — |
| L10 | 矩阵自摘要 | 矩阵构建器 | `matrix.matrix_digest` | `D(matrix_to_canonical_dict(m))`（该字典**不含** `matrix_digest`） | `matrix_digest` |
| L11 | 全链 → 执行 | 执行器 | `execution.source_chain`（`SourceChainV1` 六个字段） | `(contract_digest, plan_digest, input_digest, domain_digest, dataset_digest, matrix_digest)` 直接取自矩阵 | 无 |
| L12 | 执行自摘要 | 执行器 | `execution.artifact_digest` | `D(_execution_payload(a))` | `artifact_digest` |
| L13 | 元数据绑定摘要 | **编排器** | `metadata.registry_binding_digest` | `D({"binding_state": ...})` 或 `D(第 10.2 节绑定载荷)` | 无 |
| L14 | 信封自摘要 | **编排器** | `metadata.pipeline_digest` | `D(pipeline_result_to_canonical_dict(r))` | `pipeline_digest` |

**重要**：L1–L12 全部由**既有**代码产出，编排器不得重算、不得覆盖、不得"修正"。
编排器只新增 L13 与 L14 两个摘要。

### 9.2 摘要的字符串形态

全部摘要字段都是**裸 64 位小写十六进制**（无 `sha256:` 前缀）。实测依据：
`canonical_digest` 返回 `hashlib.sha256(...).hexdigest()`；既有校验用
`re.fullmatch(r"[0-9a-f]{64}", ...)`（`planning/matrix.py` 的 `HASH_RE`、
`datasets/synthetic.py` 的 `_hash`、`execution/bounded.py` 的 `_HASH_RE`）。
编排器的 L13/L14 必须同形：`re.fullmatch(r"[0-9a-f]{64}", value)`。

### 9.3 每个下游验证器实际检查什么（实测，逐条）

| 验证器 | 结构/shape | 自摘要重算 | 上游重算 | 逐字节比对 | 因此能检测的篡改 |
| --- | --- | --- | --- | --- | --- |
| `validate_contract` | 是 | **是**（`CONTRACT_DIGEST_MISMATCH`） | — | — | 合同任一字段被改、摘要被改 |
| `validate_analysis_plan` | 是 | **是**（`PLAN_DIGEST_MISMATCH`） | 结构层校验 `source_contract_digest` 形态（不做全链重算） | — | 计划任一字段被改、摘要被改 |
| `validate_dataset` | 经 `serialize_dataset` | **是**（`INPUT_DIGEST_MISMATCH`，`synthetic.py:784`） | **是**（重新 `materialize_analysis_dataset`） | **是**（`IDENTITY_CONFLICT`） | 准备数据任一字段、输入任一字段、合同/计划被改（经重算链） |
| `validate_design_matrix` | 是 | **是**（`MATRIX_DIGEST_MISMATCH`，`matrix.py:323`） | **是**（`validate_dataset`） | **是**（重投影比对） | 矩阵任一字段、上游全部 |
| `validate_execution_artifact` | 是 | **是**（`ARTIFACT_DIGEST_MISMATCH`） | **是**（`validate_design_matrix`） | **是**（V3 重执行 + V4 比对） | 执行产物任一字段、上游全部 |
| `validate_pipeline_result` | 是 | **是**（重算 L14） | **是**（重跑 S1–S6 的子链） | **是** | 信封任一字段、上游全部 |

### 9.4 篡改检测责任划分（明确盲区）

- **T1**：合同、计划、准备数据、矩阵、执行产物的篡改，全部由**既有**验证器的链式重算检测；
  编排器不新增检测逻辑。
- **T2**：编排器新增的检测责任只有两项：L13 与 L14 的重算比对。
- **T3**：合同自摘要与"重编译一致性"两级检测都已存在，且都在**上游**：
  1. `planning/compiler.py` 的 `_validated_contract_dict` 第一行语义即为 `validate_contract(contract)`，
     后者在 `contract_compiler.py:577-594` 重算 `compute_contract_digest(contract)` 并比对，
     不符即 `CONTRACT_DIGEST_MISMATCH`；
  2. 同一函数还从合同的规范字典重建 A.1 文档、重新
     `compile_hypothesis_config(parse_hypothesis_config(document))`，并要求规范字典逐字节相等，
     否则 `NON_CANONICAL_CONTRACT`。
  因此"字段被改且 `contract_digest` 被相应改写"的合同仍会在 S2 被第 2 级检测拒绝
  （重编译结果与篡改后的 payload 不等）。**本设计因此在 S1 的后验验证中不再重复这两项**，
  只保留 `validate_contract(contract)` 以固定首错的**归属步骤**（第 6.1 节）；重复重编译会
  无谓放大第 11.3 节的调用次数上界。验收场景 AC-06 必须覆盖"合同字段被改且摘要被重写"，
  并断言失败归属 S2、错误为既有 `ValueError`（`CONTRACT_DIGEST_MISMATCH` 或
  `NON_CANONICAL_CONTRACT`）。
- **T4**：`bound_inputs` 的 `domain` 级摘要（`domain_digest`）由适配器从 `x.domain` 重算，
  调用者**不能**直接提供它；因此不存在"伪造域摘要"的面。
- **T5**：编排器不得提供任何"跳过验证"的开关。没有 `verify=False`、没有 `fast=True`、
  没有 `skip_stages`。

### 9.5 `validate_pipeline_result` 的冻结顺序（V1–V6）

```text
V1  类型与 shape：result 必须恰为 SyntheticPipelineResultV1；六个字段类型逐一 _shape 等价检查
V2  五个阶段对象自洽：调用既有 validate_contract / validate_analysis_plan / validate_dataset /
      validate_design_matrix / validate_execution_artifact（与第 6.1 节完全相同的顺序与参数）
V3  摘要链一致：execution.source_chain 六个字段必须逐项等于
      (contract.contract_digest, plan.plan_digest, request.bound_inputs.input_digest,
       preparation.domain_digest, preparation.dataset_digest, matrix.matrix_digest)
      不符 => PIPELINE_DIGEST_MISMATCH（封闭码；V3 在结构上被 V2 的逐字节比对抢先，见第 9.4 节 T1）
V4  元数据绑定：pipeline_state == PIPELINE_STATE；stages_completed == REQUIRED_STAGES_COMPLETED；
      registry_binding_digest 重算相符；registry_binding 与 request.registry_record 相符
      （第 10.3 节 RB1–RB6）
      V4 的**结构失败**（pipeline_state 或 stages_completed 不符）=> 既有封闭码
      PIPELINE_DIGEST_MISMATCH（同一伪造在 V6 也得到该码，因此不引入新的可观察错误）；
      **绑定条款**失败 => 第 10.3 节的 PIPELINE_REGISTRY_RECORD_INVALID /
      PIPELINE_REGISTRY_IDENTITY_MISMATCH
V5  禁止内容：对规范字典执行既有等价的禁止内容检查（第 5.5 节）；命中 => 既有
      ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")（既有类型 + 既有码，不新增编排器码）
V6  信封自摘要：重算 L14 并比对，否则 PIPELINE_DIGEST_MISMATCH
```

> 注意：`validate_pipeline_result` **不**重新计算 `pipeline_digest` 以外的任何摘要，
> 也不重新执行统计；V2 已经通过既有验证器完成了重算与重执行（第 6.2 节 P3）。
> 若实现为了"更安全"在 V2 之后再加一次 `execute_bounded_analysis`，属于**新增**计算，
> 本设计不允许（会改变资源边界，第 11.3 节）。

---

## 10. M4-B 注册表记录的元数据绑定

### 10.1 语义

- 绑定是**只读、可选、非证据**的。提供的记录不改变 `PIPELINE_STATE`、不进入证据块、
  不触发任何状态转换、不触发执行、不影响任何统计量。
- 省略（`registry_record=None`）是**一等公民**：`binding_state = REGISTRY_BINDING_ABSENT`，
  `registry_binding_digest = D({"binding_state": REGISTRY_BINDING_ABSENT})`。
- 提供时 `binding_state = REGISTRY_BINDING_PRESENT`。
- 编排器**不得**调用 `transition_hypothesis_record`、`validate_state_transition`、
  `build_hypothesis_registry_snapshot` 中的任何一个。

### 10.2 绑定载荷与摘要

提供记录时：

```text
payload = {
  "binding_state": REGISTRY_BINDING_PRESENT,
  "record_digest": <hypothesis_record_digest(record)>,
  "record_identity_digest": <hypothesis_record_identity_digest(record)>,
  "record_status": <record.status>,
  "record_hypothesis_id": <record.hypothesis_id>,
  "record_hypothesis_version": <record.hypothesis_version>,
  "record_bytes_sha256": sha256(<serialize_hypothesis_record(record)>).hexdigest(),
}
registry_binding_digest = D(payload)
```

省略时：

```text
payload = {"binding_state": REGISTRY_BINDING_ABSENT}
registry_binding_digest = D(payload)
```

约束：

- **B1**：`record_bytes_hex` 恰为既有 `serialize_hypothesis_record(record)` 字节的十六进制
  编码（第 J1–J3 条）；不得重新序列化、不得美化、不得截断。
- **B2**：`record_bytes_sha256` 使用 `hashlib.sha256` 直接对**字节**求值（**不是**
  `canonical_digest`，因为输入是字节而非字典）。这是 I4 允许导入 `hashlib` 的唯一原因。
- **B3**：三个记录摘要（`record_digest`、`record_identity_digest`、`record_bytes_sha256`）
  必须来自既有 `registry` API；编排器不得自行实现记录序列化。
- **B4**：`binding_state` 是封闭二词表；没有第三值。
- **B5**：`record_bytes_hex` 参与 L13 与 L14（它是 `metadata` 的字段）；但**不**参与
  `record_digest`/`record_identity_digest`（后两者由既有 API 对记录本体求值）。

### 10.3 `validate_pipeline_result` 对绑定的检查（RB1–RB6）

```text
RB1  binding_state 必须是 REGISTRY_BINDING_ABSENT / REGISTRY_BINDING_PRESENT 之一
RB2  registry_binding_digest 必须等于按第 10.2 节重算的值
RB3  若 binding_state == ABSENT：request.registry_record 必须为 None，且 binding 必须为 None
RB4  若 binding_state == PRESENT：binding 不得为 None；其七个字段必须按第 10.2 节映射：
      binding_state 原样；hypothesis_id/hypothesis_version 映射到
      record_hypothesis_id/record_hypothesis_version；record_identity_digest、record_digest、
      record_status 原样；record_bytes_hex 映射为其字节 SHA-256 的 record_bytes_sha256
RB5  PRESENT 时：parse_hypothesis_record(bytes.fromhex(binding.record_bytes_hex)) 必须成功，且
      hypothesis_record_identity_digest / hypothesis_record_digest 重算相符；
      binding.record_status 必须等于重解析记录的 status；record_bytes_sha256 重算相符
RB6  注册表记录内容不参与 PIPELINE_STATE、stages_completed 或任何执行字段
```

- **绑定条款**任一不符 => `PIPELINE_REGISTRY_RECORD_INVALID`（结构/字节/摘要）或
  `PIPELINE_REGISTRY_IDENTITY_MISMATCH`（身份），按 V4 内部固定顺序取首错。**RB4 的映射保留**：
  `binding.record_bytes_hex` 是 `bytes.fromhex` 可解码的小写十六进制，其字节的 SHA-256 即
  `record_bytes_sha256`（第 10.2 节载荷字段），据此与 RB2 的重算值比对。
  V4 中**不**属于绑定块的**结构**失败（`pipeline_state` / `stages_completed` 不符）用封闭码
  `PIPELINE_DIGEST_MISMATCH`（第 9.5 节 V4），**不**使用本节的注册表码——这样 V4 的每条失败
  都有唯一的既有封闭码，不新增第 15 个编排器码。
- **RB6**：注册表记录的内容**不**参与 `PIPELINE_STATE`、`stages_completed` 或任何执行字段。
  改动注册表记录只会改变 L13/L14 与本块，不会改变任何统计量——验收 AC-16 必须断言这一点。

### 10.4 可绑定状态允许表（claim-boundary 冻结）

**问题（独立审查发现）**：`HypothesisRecordV1.status` 是既有 12 状态词表之一，其中
`DEVELOPMENT_EXECUTED`、`ROBUSTNESS_EXECUTED`、`OOS_EXECUTED`、`ESTABLISHED` 等状态在既有
注册表层携带**执行/证据语义**（既有 `states.py` 要求这些状态伴随 `authorization_ref` 与
证据种类）。若只校验 `hypothesis_id`，一个处于执行态的合法记录就能被绑定，其状态被逐字复制
进合成信封——那会让"一次合成运行"看起来像"一次已注册的开发期执行"。
这是**声明边界**问题，必须机械禁止。

**冻结：可绑定状态允许表（封闭集合）**

```text
BINDABLE_REGISTRY_STATUSES = (
    "DISCOVERED",
    "LITERATURE_REVIEWED",
    "A_SHARE_FEASIBILITY_REVIEWED",
    "NOT_TESTED",
    "PRE_REGISTERED",
    "DEFERRED",
)
```

- **BS1**：只有**执行前**状态可绑定。它们都不承载执行、证据或结论语义。
- **BS2**：`DEVELOPMENT_EXECUTED`、`ROBUSTNESS_EXECUTED`、`OOS_EXECUTED`、`NOT_ESTABLISHED`、
  `ESTABLISHED`、`INCONCLUSIVE` **一律不可绑定**；命中即抛
  `PipelineError("PIPELINE_REGISTRY_STATUS_NOT_BINDABLE")`，在 S7 求值，**不**回退、
  **不**降级、**不**只警告。
- **BS3**：该门是**编排器层**的策略，**不**修改既有注册表状态机、**不**改变
  `LEGAL_TRANSITIONS`、**不**新增状态、**不**声称任何既有状态非法。处于执行态的既有记录
  在既有 API 下完全合法——它们只是**不能作为合成运行的元数据绑定**。
- **BS4**：绑定**不**表示、也**不**暗示：记录已被执行、已被验证、已建立、已被提升，
  或合成运行对该假设构成任何证据。`record_status` 只是"绑定时记录处于哪个执行前阶段"的
  只读快照。
- **BS5**：编排器**不得**借绑定去改变记录状态（第 10.1 节）；`BINDABLE_REGISTRY_STATUSES`
  是**读取**侧的允许表，不是写入侧的状态机。
- **BS6**：`BINDABLE_REGISTRY_STATUSES` **不**进入公开 `__all__`（与 C6/R17.5 同理）；
  验收通过行为断言（AC-25d）。

### 10.5 为什么记录字节可以被安全纳入

既有 `_check_forbidden_content` 的路径/主机/选择键禁令适用于**执行产物内部**；
本设计的绑定块位于 `metadata`，其键名已逐一通过第 5.5 节词表比对。记录字节是 `bytes`，
不参与"字符串值的绝对路径扫描"，因此不会因注册表自由文本里的路径样式字符而误伤。
同时 R5 要求重解析，使"字节被截断/替换"必然被发现。

---

## 11. 确定性与资源边界

### 11.1 重复运行确定性

- **C1**：`run_synthetic_pipeline(request)` 对同一 `request` 的两次调用（同一进程内与跨进程）
  必须返回 `serialize_pipeline_result` **逐字节相等**的结果，**前提**是第 C5 条的上下文固定条件成立。
- **C2**：确定性来源全部来自既有层：合同的规范字典、计划的规范字典、适配器的域序与
  `sorted(rs)` 原因码、执行器的 `PCG64(seed)`。编排器不引入任何新熵源
  （无时钟、无 UUID、无 `id()`、无 `hash()`、无环境变量、无集合迭代顺序）。
- **C3**：编排器不得使用 `set`/`frozenset` 参与规范字典构造；所有序列必须是 `tuple` 或
  既有产物的既有顺序。
- **C4**：浮点绝不进入信封本体：执行产物的数值以既有 `Float64ValueV1` 的规范十进制**文本**
  承载；编排器不得把文本转回 `float`。
- **C5（关键，独立审查发现）**：**ambient `decimal` 上下文会改变产物字节。**
  既有 `canonical_decimal`（`hypothesis_config.py`）与执行层 `_interval_indices`
  （`execution/bounded.py:909-920`）使用**当前** `decimal` 上下文；实测：同一代码、同一输入、
  同一 seed，在 `prec=28` / `8` / `4` 下产出的 `artifact_digest` 与序列化字节**互不相同**
  （伴随十进制分别为 `0.24691357802487854` / `0.24691358` / `0.2469`）。
  既有代码没有任何 `localcontext` 固定。**本设计因此冻结**：

  ```text
  DECIMAL_CONTEXT_PRECISION = 28
  ```

  编排器必须在 S0 之前进入 `decimal.localcontext()` 并把 `prec` 设为
  `DECIMAL_CONTEXT_PRECISION`，在 S8 返回之前退出；即整条 S0–S7 都在该固定上下文内求值。
  约束：
  1. 不得修改**全局** `decimal.getcontext()`（不得写 `decimal.getcontext().prec = 28`）；
     必须使用 `localcontext()`，以保证调用前后宿主的全局上下文逐字段不变（验收断言）；
  2. 不得吞掉 `decimal` 的陷阱设置差异——`localcontext()` 只固定 `prec`，
     **不**固定 traps/flags；因此 C1 的字节相等承诺以"宿主 `decimal` 默认陷阱设置"为前提，
     若宿主改了陷阱设置，属于第 14 节 R16 的已知边界；
  3. 该上下文只影响既有代码读取 ambient 上下文的位置；编排器**不得**用它去"修正"任何既有数值。
- **C6**：`DECIMAL_CONTEXT_PRECISION = 28` 是**新增常量**，但它**不**进入第 4.4 节的公开
  `__all__`（它是实现细节而非公共契约面）；验收通过行为断言它，而不是通过导入它。

### 11.2 seed 与 RNG 归属

- seed 只来自 `HypothesisConfig.bootstrap_policy` → 合同 → 计划的固化值（第 2.5 节）。
- 编排器**不得**接收、派生、覆盖或记录 seed；信封不含任何 seed 字段。
  （计划字典中已含 `bootstrap_plan.seed`，那是既有产物内容，编排器只转发。）

### 11.3 有界资源行为

既有链在一次成功调用中会触发多次重算（第 6.2 节 P3）。本设计冻结以下上界，
并把它作为验收项（AC-28）：

| 界 | 依据 |
| --- | --- |
| 阶段函数调用次数是**常量级**，与输入规模无关（不含随数据增长的循环） | 既有验证器的固定 4 步/5 步结构 |
| `build_analysis_plan` 调用次数 ≤ 12（**实测值**，非估计） | 编排器 S2 直调 1 次 + 经适配器模块内引用的链式重算 11 次（每次 `materialize_analysis_dataset` 都经 `_validate_inputs` 重编译 1 次；该链共调用 `validate_dataset` 10 次、`validate_design_matrix` 7 次）。S7 的 `validate_pipeline_result` V2 单独贡献 +4 |
| `materialize_analysis_dataset` 调用次数 ≤ 11（**实测值**，非估计） | 编排器 S4 直调 1 次 + 经适配器模块内引用的链式重算 10 次（每次 `validate_dataset` 都会"重算 + 逐字节比对"，共 10 次调用）。S7 的 `validate_pipeline_result` V2 单独贡献 +4 |
| `_execute` 调用次数 ≤ 3（**实测值**，非估计） | S6 `execute_bounded_analysis` 1 次 + `validate_execution_artifact` 的 V3 重执行 1 次 + S7 `validate_pipeline_result` V2 内 V3 重执行 1 次（重执行内部对 bootstrap 的循环由计划声明界定量；因此工作量约为 `3 × replications`） |
| **bootstrap `replications` 绝对上界 = `MAX_BOOTSTRAP_REPLICATIONS`**（新增 pipeline 策略门；**仅当 `bootstrap_plan.enabled is True` 时求值**） | 见下方 R17 说明；禁用 bootstrap 时无重采样工作，惰性声明不被拒绝（AC-28d） |
| 矩阵行数上界 = `domain.expected_dates` 长度 | 适配器按域逐日投影 |
| 单元格绝对值上界 = 既有 `MAX_ABS_CELL_DECIMAL = "1000000"` | 既有执行层常量 |
| 观测条数上界 = `len(roles) × len(expected_dates)` | 适配器 `_validate_inputs` 的域内唯一性 |
| 递归深度上界 = 输入的 JSON 嵌套深度 | 编排器不新增递归；不得调用 `sys.setrecursionlimit` |
| 线程/进程/协程：0 | 编排器不得导入 `threading`、`multiprocessing`、`asyncio`、`concurrent.futures` |

> 上表**前三行**已按实现评审的**实测**改定（其中原 ≤6/≤8 两项不成立，`_execute <= 3` 经实测确认，
> 见第 14 节 R2）；其余各行仍是设计声明。**为什么公开产出者计数包含验证重算**：计数打在
> **公共产出者符号**上，既统计编排器 S2/S4 的直调，也统计既有验证器触发的每一次链式重算，
> 因此它必然包含验证重算；早期草案的 ≤6/≤8 只估到链路的一部分，漏掉了
> `validate_pipeline_result` V2 会**再跑一遍** S1–S6 的验证链（该重跑由第 9.5 节 V2 与
> 第 6.1 节 S7 强制）。实现评审**不得放宽**这三个上界；实测若超出，属于设计缺陷，
> 按第 14 节 R1 上报。这三项是**与输入规模无关**的拓扑常量。

#### 11.3.1 R17：为什么必须有绝对上界，以及它是什么

**问题（独立审查发现）**：既有配置层对 `bootstrap_policy.replications` **没有上界**
（`hypothesis_config.py` 接受 `10**9`），而执行器按 `for _ in range(replications)`
逐个重复（`execution/bounded.py`）。由于 V2/V3 会重执行，一次调用的实际工作量约为
`3 × replications` 次重采样与 OLS 拟合。因此第 11.3 节若只写"上界 = 计划声明值"，
等价于说"**没有绝对上界**"，这与 Goal 第 6 条要求的"bounded resource behavior"不符。

**本设计的选择（新增 pipeline 策略，不改既有层）**：

```text
MAX_BOOTSTRAP_REPLICATIONS = 100000
```

- **R17.1**：该常量是**编排器层**的策略门，**不**修改 `hypothesis_config.py`、
  **不**修改任何既有 `__all__`、**不**改变既有执行器行为。直接调用既有
  `execute_bounded_analysis` 的调用者不受它约束（既有行为一字不变）。
- **R17.2**：编排器在 S0 门禁中读取合同/计划声明前的**配置层**值不可行（尚未编译），
  因此该门在 **S3 内 G10 之后**求值：若计划声明 `bootstrap_plan.enabled is True` **且**
  `bootstrap_plan.replications > MAX_BOOTSTRAP_REPLICATIONS`，抛
  `PipelineError("PIPELINE_REPLICATIONS_EXCEED_LIMIT")`，**在 S4 之前**终止，不做任何重采样。
  **求值条件含 `enabled is True`（与 AC-28d 一致，修正 G11 与 AC-28d 的冲突）**：
  `enabled is False` 的计划**没有**重采样工作，其 `replications` 声明是惰性的，
  **不**被本门拒绝；本门约束的是重采样工作量，不是声明值的形状。
- **R17.3**：该码加入第 8.3 节，成为编排器自有码之一（第 8.3 节给出唯一权威计数）。
- **R17.4**：本设计**不**声称该上界是"统计上合适"的——它只是资源界的机械上限；
  它**不**构成对任何重复次数的充分性、有效性或显著性的主张。
- **R17.5**：`MAX_BOOTSTRAP_REPLICATIONS` **不**进入公开 `__all__`（与 C6 同理，
  它是实现细节）；验收通过行为断言它。

### 11.4 无副作用（结构性）

- **N1**：编排器模块不得**直接**导入 `os`、`pathlib`、`io`、`socket`、`subprocess`、`tempfile`、
  `shutil`、`glob`、`duckdb`、`requests`、`urllib`、`http`、`logging`。
  **注意**：这只能约束**直接**导入。既有依赖链
  （`model_digest` → `analysis_contracts` → `pandas`）在**进程内**必然带入 `pandas`、`pyarrow`、
  `socket`、`pathlib`、`yaml`（第 4.1 节 I4 实测）。因此**不得**断言
  `"socket" not in sys.modules` 或 `"pathlib" not in sys.modules`——那是**不可满足**的断言，
  会把一个正确的实现判为失败。
- **N2**：编排器不得调用 `print`、不得写 `sys.stdout`/`sys.stderr`、不得配置日志。
- **N3**：编排器不得读写任何文件、不得读取环境变量、不得读取时钟、不得访问网络。
- **N4**：验收断言方式（修正一处早期草案的误述）。仓库**既有**做法就是对
  `builtins.open`/`Path.open`/`socket.socket`/`socket.create_connection` 做 monkeypatch
  （`tests/test_m4_bounded_execution.py` 中的 `no_external_io` 用例，实测通过），
  早期草案说"monkeypatch 与既有风格冲突"是**错误**的。推荐组合（由强到弱，三条都要）：
  1. **AST / 源码级**断言：只对**新模块**检查被禁**直接**导入与 `open(`/`print(`/`socket.`
     等直接调用。这是唯一能覆盖"函数内部惰性导入"的静态手段；
  2. **目录快照**：在仓库外临时目录执行，比对调用前后的工作目录与相对文件清单不变；
  3. **运行时探针**：在**完整导入之后**对 `builtins.open`、`Path.open`、`socket.socket`、
     `socket.create_connection` 打 monkeypatch 并断言零调用——这是既有做法，能抓住静态检查
     看不见的传递调用。
  断言**不得**使用 `sys.modules` 的"不存在"形式（见 N1）。

---

## 12. 验收矩阵与实现白名单

### 12.1 验收矩阵总览

完整案例清单在配套文档
[M4 合成端到端流水线验收场景 v1](m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md)。
矩阵覆盖**七类**：

| 类别 | 覆盖内容 | 案例区间 |
| --- | --- | --- |
| 正常 / positive | 成功链路、字节相等、重复运行、信封形态、公开导出面 | AC-01 – AC-04 |
| 边界 / boundary | 最小域、缺省注册表绑定、`REJECTED_QUALITY`、版本常量、bootstrap 两态、资源上界、decimal 上下文 | AC-05 – AC-09、AC-28 – AC-29 |
| 篡改 / tamper | 合同、计划、输入、准备数据、矩阵、执行产物、信封逐层篡改 | AC-10 – AC-15 |
| 错误顺序 / error-order | 首错归属、多故障并存时的唯一首错、异常映射类型、可达/不可达码 | AC-16 – AC-19 |
| 结构性禁令 / structural-ban | holdout/真实数据/provider/数据库/路径/seed/排序 的不可表达性、无副作用、公开入口可达性 | AC-20 – AC-23、AC-30 |
| 授权 / authorization | 合成来源显式标记、解释边界、注册表非证据与状态允许表、就绪≠授权 | AC-24 – AC-26 |
| 回归 / regression | 既有回归与治理测试保持通过、冻结 blob 不变 | AC-27 |

### 12.2 Goal「Required behavior」到案例的逐条映射

| Goal 要求（第 56–78 行） | 承载案例 |
| --- | --- |
| 1 单一入口 + 不可变信封 + 精确名称/输入/输出/版本/序列化/摘要/导出面 | AC-01、AC-02、AC-03、AC-04 |
| 2 精确组合顺序 + 每阶段前后验证 + 不复制统计 + 不绕过验证器 | AC-05、AC-16、AC-17、AC-23 |
| 3 合成来源与授权门禁 + 注册表元数据与执行证据分离 | AC-20、AC-21、AC-24、AC-25、AC-26 |
| 4 确定性首错顺序 + 稳定错误码 + 异常映射 + 无部分结果 | AC-16、AC-17、AC-18、AC-19 |
| 5 跨产物绑定 + 精确摘要链 + 篡改检测责任 | AC-10、AC-11、AC-12、AC-13、AC-14、AC-15 |
| 6 不可变性 + 规范字节相等 + 重复运行确定性 + 有界资源 + 无副作用 | AC-02、AC-03、AC-13、AC-21、AC-28、AC-29 |
| 7 可选 M4-B 记录作为元数据绑定 + 不改变状态 + 省略语义 | AC-08、AC-25 |
| 8 完整验收矩阵 + 后续 Goal 实现白名单 | 本文档全文 + 第 12.3 节 |
| 9 显式非目标与残余风险（含"不是通用真实数据研究执行器"） | 第 1.2、14 节 + AC-20、AC-23、AC-26 |

> Goal 第 6 条现在有**专属**案例：`AC-28`（有界资源上界，含 `replications` 上界与
> `PIPELINE_REPLICATIONS_EXCEED_LIMIT`）与 `AC-29`（decimal 上下文固定与跨 `prec` 字节相等）。
> 早期草案把"有界资源"挂在 AC-17 上，属于错误引用，已修正。

### 12.3 后续实现 Goal 的实现白名单

若后续另行授权实现，新 Goal 的允许写入面**只**包括：

```text
src/ashare_research/mechanism/pipeline/__init__.py
src/ashare_research/mechanism/pipeline/orchestrator.py
tests/test_m4_synthetic_pipeline_orchestrator.py
README.md                              （仅状态/授权措辞）
agent/goals/<新实现 Goal>.md
agent/record/<新实现记录>.md
acceptance/<新实现验收>.md
```

禁止面（与本文第 1.2 节一致，且必须在实现 Goal 中逐条重述）：

- 不得修改本文、配套验收场景文档、任何既有 `docs/**`、任何既有 `reports/**`、
  任何既有 `acceptance/**`、任何既有 `tests/**`；
- 不得修改 `src/ashare_research/mechanism/` 下**任何既有模块**（含其 `__all__`）；
- 不得修改任何既有冻结 blob（第 13 节的五个）；
- 不得新增依赖、不得修改 `pyproject.toml`、不得修改 `.github/**`；
- 不得引入真实数据、provider、数据库、行情、文献、holdout、回测、排序或推荐能力。

---

## 13. 可追溯性与授权语义

### 13.1 条款编号

| 编号族 | 含义 | 首次出现 |
| --- | --- | --- |
| `S0`–`S8` | **步骤**序列（唯一用途） | 第 6.1 节 |
| `P1`–`P7` | 顺序不变量 | 第 6.2 节 |
| `E7`–`E9` | 无部分结果与不可变性条款 | 第 6.4 节 |
| `G1`–`G14` | 门禁 | 第 7.1 节 |
| `M1`–`M5` | 异常映射规则 | 第 8.7 节 |
| `L1`–`L14` | 摘要链 | 第 9.1 节 |
| `T1`–`T5` | 篡改检测责任 | 第 9.4 节 |
| `V1`–`V6` | 信封验证顺序 | 第 9.5 节 |
| `B1`–`B5` | 注册表绑定载荷条款 | 第 10.2 节 |
| `RB1`–`RB6` | 注册表绑定**校验**条款 | 第 10.3 节 |
| `BS1`–`BS6` | 可绑定状态（bindable status）允许表条款 | 第 10.4 节 |
| `C1`–`C6` | 确定性条款 | 第 11.1 节 |
| `J1`–`J4` | `record_bytes_hex` 编码条款 | 第 4.4 节 |
| `A1`–`A5` | `bound_inputs_identity_payload` 条款 | 第 4.5.1 节 |
| `R17.1`–`R17.5` | 资源上界条款 | 第 11.3.1 节 |
| `D1`–`D7` | 信封 schema 与禁止内容约束 | 第 5.1、5.5 节 |
| `N1`–`N4` | 无副作用条款 | 第 11.4 节 |
| `I1`–`I6` | 实现落点与导入约束 | 第 4.1 节 |
| `AC-01`–`AC-30` | 验收案例（稳定标识，不得重排或留孤儿编号） | 配套验收场景文档 |

### 13.2 授权矩阵（冻结）

| 能力 | 本设计 | 需要的单独授权 |
| --- | --- | --- |
| 冻结端到端编排设计 | ✅ 本文交付 | — |
| 实现 `run_synthetic_pipeline` | ❌ 不授权 | 新 Goal + 明确实现授权 |
| 在合成 fixture 上运行编排器 | ❌ 本阶段未实现，无法运行 | 实现授权后另行验收 |
| 真实数据执行（任何形式） | ❌ 禁止 | 单独授权 |
| 真实候选 / 注册数据集创建或加载 | ❌ 禁止 | 单独授权 |
| 文献 / 教材获取 | ❌ 禁止 | 单独授权 |
| 访问 provider / 数据库 / 真实行情 | ❌ 禁止 | 单独授权 |
| 访问 holdout | ❌ 禁止（且结构性不可表达） | 单独授权（始终不授权执行） |
| 由编排器触发 M4-B 状态转换 | ❌ 禁止 | 单独授权 |
| 回测 / 排序 / 提升 / 推荐 / 交易结论 | ❌ 禁止 | 单独授权 |
| 推送 / PR / 合并 | ❌ 本阶段不执行 | 用户明确指令 |
| 进入实现或下一阶段 | ❌ 不自动进行 | 用户明确授权 |

### 13.3 冻结 blob 引用

本设计**不修改**下列冻结产物的字节（引用 Goal 第 26–31 行的记录）：

```text
docs/m4_bounded_execution_and_evidence_design_v1.md         9617f64360b6c3d9a6148ec08c25fa0209a0f9f4
docs/m4_bounded_execution_acceptance_cases_v1.md            f857b9948c7f396a855a1e0f6506752f0065d667
docs/m4b_hypothesis_registry_design_v1.md                   6d9c292001c09a4b1a8e895e54619dc1e8826f3d
docs/m4b_hypothesis_registry_acceptance_cases_v1.md         4a9b227204fc1c0eabc28e1e8b3d60a53c46f0b2
reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json dfd41eaafc099e7748499f72de7ddd800bf97f69
```

---

## 14. 未决与风险

| # | 风险/未决项 | 处理 |
| --- | --- | --- |
| R1 | 既有模块中可能存在未映射的裸异常点（`KeyError`/`IndexError`/`AssertionError`），编排器按 `M3` 只能以 `PIPELINE_INTERNAL_SOURCE_UNMAPPED` 终止 | 实现评审时用恶意合成输入探测；若发现，属既有模块缺陷，另行按独立 Goal 修复，**不得**在本设计内扩大兜底 |
| R2 | 第 11.3 节的三项调用次数上界原为**设计声明**（≤6/≤8/≤3），实现评审实测证明其中两项不成立：`build_analysis_plan = 12`、`materialize_analysis_dataset = 11` | **已按实测更正**为 ≤12/≤11/≤3（第 11.3 节）；计数打在公共产出者符号上，因此包含既有验证器的链式重算与 S7 `validate_pipeline_result` V2 的额外一轮（+4/+4/+1）。其余行仍为设计声明；实现评审**不得放宽**这三项 |
| R3 | 合同自摘要与重编译一致性（第 9.4 节 T3）由**既有**上游两级检测覆盖（`validate_contract` + 重编译比对） | 编排器在 S1 只调用 `validate_contract` 以固定首错**归属**；AC-11 必须覆盖"字段被改且摘要被重写"并断言失败归属 S2 |
| R4 | `BoundDatasetInputsV1` 由调用者构造，其合成观测的"研究含义"不受本设计约束 | 本设计只冻结归属与摘要一致性；合成数值的语义由既有适配器设计与验收 fixture 决定 |
| R5 | 稳健性派遣入口（`prepare_registered_robustness_dispatch`）未接入端到端链 | 有意为之（第 6.2 节 P7）；若后续需要，须另行授权并重新评估证据形状 |
| R6 | 编排器新增 14 个自有错误码，扩大了公共错误面（唯一权威计数见第 8.3 节） | 已最小化：仅覆盖"编排器自己引入的失败点"；所有上游失败一律透传既有码 |
| R7 | 第 5.5 节词表比对是对**当前** `FORBIDDEN_KEYS` 的快照 | 若既有执行层未来扩展该词表，新增字段名可能命中；实现评审须重新比对 |
| R8 | "无副作用"的断言依赖三层检查（AST 直接导入 + 目录快照 + 运行时 monkeypatch），而非运行时隔离 | 见第 11.4 节 N4；本设计接受该强度，并明确不承诺沙箱级隔离 |
| R9 | 本设计**没有**实现任何函数；第 4、5、10 节全部为拟议 API | 第 1.2 节第 1 条已声明；实现审查不得把本文读成已实现 |
| R10 | **跨环境字节相等的边界**：既有 `MethodConfigurationV1.numeric_runtime` 绑定 `numpy.__version__`（`execution/bounded.py:212`、`:814`、`:1493`），该字符串进入 `_execution_payload` 因而进入 `artifact_digest` | 第 11.1 节 C1 的"字节相等"只承诺**同一解释器与同一 numpy 版本**；跨 numpy 版本的字节相等**不在本设计的保证范围内**。验收 AC-03 必须固定同一环境执行，跨版本差异按 AC-03d 显式记录为已知差异而**不是**失败 |
| R11 | `record_bytes_hex` 的长度对**具体**记录必然有限，但**没有一致的有限上界**：既有 M4-B schema 的四个知识元组基数、`state_history` 长度、`authorization_ref` 与 `schema_version` 均无上限，逐字段文本上限（`NOTES_MAX_LEN = 4000` 等）只约束单个字段 | 第 J4 条已按此更正：**不**冻结总上限、**不**新增尺寸门（也不得把测试里的"有界文本骨架"实测值表述为 schema 保证）。绑定语义（J1–J3、RB4/RB5、小写十六进制与逐字节往返）保持不变 |
| R12 | `numeric_runtime` 只钉住 numpy 的**版本字符串**，不钉住 BLAS/LAPACK 构建；`numpy.linalg.lstsq` 的位级输出可能随 BLAS 构建而变 | 与 R10 同属"跨环境"边界：同一环境内字节相等成立（既有测试已验证），跨 BLAS 构建的一致性**不**在本设计保证内。实现评审若需更强保证，须另行授权并把 BLAS 身份纳入身份链（属 schema 变更，须停下报告） |
| R13 | 编排器新增的 `metadata.interpretation_boundary` 与既有 `registry.snapshot.INTERPRETATION_BOUNDARY` **同名不同值** | 第 4.1 节 I6 已冻结处理：信封必须取执行层字面量，禁止同模块同时顶层导入两者 |
| R14 | 编排器新增的 mode/quality 拒绝面与既有执行层同类码**并存**，存在"两处判同一件事"的维护风险 | 第 6.2 节 P4/P4b 与第 8.5 节已冻结可达性划分；编排器负责"可达首错"，执行层同类码保留为纵深防御且**不得**被写成预期首错 |
| R15 | 第 7.1 节 G12/G13（注册表身份与状态）与第 10.3 节 R5（绑定重解析）都涉及注册表记录，且跨 S0 与 S7 两个时刻 | 明确分工：S0 只做**类型与自洽**（G5/G6），S7 才做**身份、状态与字节重解析**（G12/G13/R5）。实现不得把它们提前到 S0，否则会改变首错归属（AC-16 的确定性依赖这一划分） |
| R16 | 第 11.1 节 C5 只固定 `decimal` 的 `prec`，**不**固定 traps/flags | 字节相等以"宿主保持 `decimal` 默认陷阱设置"为前提；宿主改动陷阱设置属于已知边界，实现评审须在实现测试中显式记录该前提 |
| R17 | 既有配置层对 `replications` 无上界（接受 `10**9`），第 11.3 节早期措辞等价于"没有绝对上界"，与 Goal 第 6 条"bounded resource behavior"不符；且早期 G11 未写启用条件，与 AC-28d 冲突 | 第 11.3.1 节新增编排器层 `MAX_BOOTSTRAP_REPLICATIONS` 与 `PIPELINE_REPLICATIONS_EXCEED_LIMIT`；**不**修改既有层。该门**仅在 `bootstrap_plan.enabled is True` 时求值**（第 7.1 节 G11、第 11.3.1 节 R17.2），禁用 bootstrap 的惰性声明不被拒绝。该上界只是资源界，**不**构成任何统计充分性主张 |
| R18 | 第 4.5.1 节的公开 `bound_inputs_identity_payload` 必须与既有**私有** `_input_payload` 保持深度相等 | 这是对既有私有实现的**语义镜像**：若既有实现未来修改排序或键集，本函数必须同步。实现评审须加等价性测试（第 A2 条）；该同步义务记入实现 Goal |
| R19 | 请求类型只接受 `config`/`bound_inputs`/`registry_record`，调用者**无法**提交合同/计划/准备数据/矩阵/执行产物 | 验收场景文档已按此重新分类，且分类必须与第 8.5 节一致：**组合入口可达** = AC-12b、AC-13、AC-16、AC-17a、AC-17c、AC-17d、AC-22d；**信封层**（公开 `validate_pipeline_result`）= AC-15e/f；**阶段级探针**（显式标注 `STAGE_LEVEL_PROBE`，直接调用既有阶段验证器）= AC-10、AC-11、AC-12a、AC-12c、AC-14、AC-15a–d、AC-17b、AC-17f；**内部投影探针**（显式标注，直接调用私有投影助手）= AC-17e；"上游对象不可提交"本身被列为最强的结构性保证（AC-30）。**不得**把任何探针案例写成组合入口行为 |
| R20 | 若宿主环境改变了 `decimal` 陷阱或 numpy/BLAS，第 C1/C5 的字节相等不再成立 | 见 R10/R12/R16；AC-03d 与 AC-29c 负责把这类差异**显式记录**为环境差异，而不是静默通过 |

### 14.1 明确不在本设计内的事情

- 本设计不是通用真实数据研究执行器。它只编排**已验证合成输入**上的五个冻结阶段；
  没有可传入真实数据的位置，没有 provider 适配层，没有数据库会话，没有 holdout 窗口。
- 本设计不定义合成数据生成算法，也不定义真实候选的准入规则。
- 本设计不授权、不规划、也不暗示任何 M4-A 之后的研究结论。

### 14.2 边界声明

本设计为设计规范，**不是**实现、不是证据、不是执行授权。`M4 SYNTHETIC PIPELINE NOT IMPLEMENTED`；
真实假设执行 `NOT AUTHORIZED`；真实注册表数据 `NOT AUTHORIZED`；holdout 访问 `NOT AUTHORIZED`。
推送、PR、合并与进入实现/下一阶段各需单独明确授权。
