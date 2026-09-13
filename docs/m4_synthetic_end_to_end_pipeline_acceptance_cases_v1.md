# M4 合成端到端流水线验收场景 v1

状态：DESIGN_ONLY / ACCEPTANCE_CASES_NOT_IMPLEMENTED。**2026-09-12 设计更正**：本文与配套设计的
可达性分类、`AC-22d`、`AC-28d`、`AC-10`/`AC-12b`/`AC-17a`/`AC-17e` 的入口级标注已按实现评审的
**实测证据**更正（依据：实现保全提交 `8a71fb9` 的源码、测试与记录；契约见
`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`）。
本次更正**不删除、不放宽**任何既有验收义务，只按实测修正**入口归属**，并新增与更正直接对应的
断言（AC-25 第 7 条"无总上限/无尺寸门"、AC-22d 双路径分离、AC-28 关键断言第 4 条"G11 仅在
`enabled=true` 时求值"）；另有两处同类计数/引用更正（AC-27 白名单 `6 → 7`、AC-29d 失败路径改为
组合入口）。本文是
[M4 合成端到端流水线设计 v1](m4_synthetic_end_to_end_pipeline_design_v1.md) 的配套验收场景清单，
与设计文档同为**规范性**文件。编排入口**尚未实现**，因此本文不含任何真实运行结果、
系数、区间、p 值或处置；本文也**不声称**任何编排器测试已通过。

每个案例都写明五件事：**输入变化**、**预期结果 / 错误**、**验证阶段**（设计第 6.1 节 `S0`–`S8`
编号与第 9.5 节 `V1`–`V6` 编号）、**授权解释**（该案例证明了哪一条授权边界），
需要时另有**关键断言**。

编号说明：本清单编号（`AC-01`–`AC-30`）是稳定标识，**不得**留下"索引里有条目、正文里没有对应
小节"的孤儿编号，也不得在正文出现索引外的编号；子案例以小写字母后缀在同一小节内表达
（如 `AC-03d`）。删除案例必须留空号，不得重排。

---

## 0. 验证入口与前置条件

### 0.1 拟议入口（尚未实现）

```python
from ashare_research.mechanism.pipeline import (
    run_synthetic_pipeline, SyntheticPipelineRequestV1,
    SyntheticPipelineResultV1, PipelineError,
    pipeline_result_to_canonical_dict, serialize_pipeline_result, validate_pipeline_result,
)

result = run_synthetic_pipeline(request=SyntheticPipelineRequestV1(
    schema_version="M4_SYNTHETIC_PIPELINE_RESULT_V1",
    orchestrator_version="M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V1",
    config=config,              # 已解析的 HypothesisConfig
    bound_inputs=bound_inputs,  # 调用者声明的合成输入
    registry_record=None,       # 省略 => REGISTRY_BINDING_ABSENT
))
```

本清单**不构成**实现授权：上列符号全部为拟议 API，在当前 HEAD 不存在。
`ashare_research.mechanism.pipeline` 在当前 HEAD 不存在，导入会 `ModuleNotFoundError`。

### 0.2 唯一的实现前置入口是既有 `validate_design_matrix`

与既有执行层一致，编排链的篡改检测**不新造机制**：全部依赖既有验证器的"重算 + 逐字节比对"
（设计第 2.3、9.3 节）。编排器只新增两项检查：`registry_binding_digest`（L13）与
`pipeline_digest`（L14）的重算比对。

### 0.3 复现口径

- 除 AC-03d 外，全部案例在**同一解释器与同一 numpy 版本**下执行；这是设计第 11.1 节 C1 与
  第 14 节 R10 的字节相等承诺范围。
- 全部案例只使用**合成** fixture：合成观测值、合成日期、合成 `source_record_id`。不含任何
  真实行情、真实候选、真实论文或真实 A 股结果。
- 全部案例在**仓库外临时工作目录**下执行，以同时验证工作目录无关性（设计第 11.4 节 N4）。
- 探针只读派生对象、不写工作树文件、不开数据库、不调用 provider，也**不调用**
  `regression.py` / `bootstrap.py` / `robustness.py` / `evidence.py` / `crash.py`。
  统计量只经由 `execute_bounded_analysis` 产生。

### 0.4 基础上游身份（设计阶段只读复核，实测）

| 项 | 实测值 / 事实 | 来源 |
| --- | --- | --- |
| 工作树 | `D:/量化分析-m4-synthetic-pipeline-design` | 本会话 `git status` |
| 分支 | `codex/m4-synthetic-pipeline-design` | 同上 |
| 任务起始 HEAD | `f6ec598ac819c2d8db14f7a2e8c910a6ed85b301`（仅含 Goal 文件） | `git show --stat HEAD` |
| 基线 `origin/main` | `fd1cc35ee824aa9449f7e7800c12d0d80c845e05` | `git rev-parse origin/main` |
| 阶段 3 入口 | `materialize_analysis_dataset(contract, plan, bound_inputs)` | `datasets/synthetic.py:562` |
| 阶段 4 入口（**参数序不同**） | `materialize_design_matrix(preparation, contract, plan, bound_inputs)` | `planning/matrix.py:483` |
| 阶段 5 入口 | `execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs)` | `execution/bounded.py:1841` |
| 既有禁止键集合 | 24 键（`cwd`…`search`） | `execution/bounded.py` `FORBIDDEN_KEYS` |
| 既有解释边界字面量 | `INTERPRETATION_BOUNDARY`（`SYNTHETIC_TEST_ONLY: …`） | `execution/bounded.py` |
| 注册表快照层的**同名不同值**常量 | `INTERPRETATION_BOUNDARY`（`REGISTRY_METADATA_ONLY: …`） | `registry/snapshot.py:22` |
| 既有斜杠禁令模式 | `_ABSOLUTE_PATH_RE`（任何 `/`+非空白即命中） | `execution/bounded.py:148` |
| 既有 numpy 运行时 | `numpy 2.5.3`（进入 `numeric_runtime`，因而进入 `artifact_digest`） | 本会话只读探针 |
| 既有执行来源类 | `PROVENANCE_CLASS = "SYNTHETIC_TEST_ONLY"` | `execution/bounded.py:80` |
| 既有合成模式词 | `SYNTHETIC_DATASET_MODE = "SYNTHETIC"` | `execution/bounded.py` |
| 既有单元格上界 | `MAX_ABS_CELL_DECIMAL = "1000000"` | `execution/bounded.py` |
| 既有 RNG | `numpy.random.Generator(numpy.random.PCG64(seed))`，seed 来自计划 | `execution/bounded.py:965` |
| 五个阶段模块副作用导入 | **零命中**（无 `open(`/`os`/`pathlib`/`requests`/`duckdb`/…） | 本会话静态扫描 |

### 0.5 正例 fixture 的形状要求（设计推导，非实测数值）

正例必须是**满秩**合成矩阵，且满足：

1. 合同的 `analysis_method.method_id == "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"`；
2. 合同策略为 `factor.transform_semantics == "RETURN"`、`factor.factor_kind == "SYNTHETIC_REGISTERED"`、
   `target.identity_policy == "SYNTHETIC_FIXED_IDENTITY"`、
   `universe.membership_policy == "SYNTHETIC_FIXED_UNIVERSE"`、`universe.pit_policy == "EXPLICIT_PIT"`；
3. `outcome.horizon == "1D"`、`outcome.observation_timing == "CLOSE_TO_CLOSE"`；
4. `bound_inputs.domain` 的 `universe_id` / `target_series_id` / `development_start` /
   `development_end` 与合同逐项相等；
5. `bound_inputs.bindings` 的 `(role, series_id)` 序列与
   计划 `dataset_requirements.requirements` 的顺序逐项相等；
   `TARGET_OUTCOME` 的 `outcome_id` 等于 `contract.outcome.outcome_id`，其余角色为 `None`；
   全部绑定的 `unit == "DECIMAL_RETURN"`、`adjustment_policy == "SYNTHETIC_DECLARED_RETURN"`、
   `value_semantics == "DAILY_RETURN"`、`horizon == "1D"`、
   `observation_timing == "CLOSE_TO_CLOSE"`；
6. 每个 `(role, trade_date)` 恰一条观测；`trade_date ∈ domain.expected_dates`；
7. 覆盖率达到 `contract.data_quality_gates.coverage_gate`，使
   `preparation.status == "READY_SYNTHETIC"`；
8. 四个调用者自算摘要（两个证据摘要、每个观测的 `evidence_digest`、`input_digest`）
   按设计第 5.3 节的精确公式计算。

> 本节只给出**形状**要求，不含任何具体数值、摘要字符串或统计结果——设计阶段不计算这些量。

---

## 1. 案例索引

| ID | 案例 | 类型 | 验证阶段 | 授权解释 |
| --- | --- | --- | --- | --- |
| AC-01 | 正例：满秩合成链的完整信封 | 正常 | S0–S8 / V1–V6 | 合成流水线就绪 ≠ 真实研究授权 |
| AC-02 | 信封不可变性与公开导出面恰好 20 符号 | 正常 | S7 / V1 | 设计可用 ≠ 实现已授权 |
| AC-03 | 规范字节相等与重复运行确定性 | 正常 | S7–S8 | 可复现 ≠ 可外推 |
| AC-04 | 六层规范字典逐层使用既有投影 | 正常 | S7 | 只组合，不重定义 |
| AC-05 | 边界：最小可物化域（单日或多日下界） | 边界 | S3–S6 | 边界通过 ≠ 统计有效 |
| AC-06 | 边界：质量拒绝（`REJECTED_QUALITY`）在 S4 后终止 | 边界 | S4 | 不降级、不修补、不回退 |
| AC-07 | 边界：版本常量不符 | 边界 | S0 | 版本是门禁，不是提示 |
| AC-08 | 边界：省略注册表绑定是显式一等形态 | 边界 | S7 / V4 | 省略有语义，不是缺省填充 |
| AC-09 | 边界：计划声明的 bootstrap 禁用与启用两态 | 边界 | S6 | 不发明统计语义 |
| AC-10 | 篡改：合同字段被改（摘要未改） | 篡改 | S1（阶段级） | 上游篡改必须 fail-closed |
| AC-11 | 篡改：合同字段被改且摘要被重写 | 篡改 | S2（阶段级） | 重编译一致性是第二道检测 |
| AC-12 | 篡改：计划字段/摘要被改 | 篡改 | S3（组合入口）+ S2（阶段级） | 计划是绑定对象，不可改写 |
| AC-13 | 篡改：`bound_inputs` 三处摘要与观测级篡改 | 篡改 | S3–S4 | 输入不可伪造 |
| AC-14 | 篡改：准备数据与矩阵逐层重哈希伪造 | 篡改 | S5（阶段级） | 重算 + 逐字节比对 |
| AC-15 | 篡改：执行产物与信封逐层篡改 | 篡改 | S6（阶段级）/ V2–V6（信封层） | 全链身份覆盖到底 |
| AC-16 | 首错：多故障并存时唯一的首错归属 | 错误顺序 | S0–S3 | 顺序是规范，不是实现细节 |
| AC-17 | 首错：阶段内错误码透传且不被改写 | 错误顺序 | S1–S6（组合入口 + 阶段级/内部投影探针） | 编排器不吞错、不改码 |
| AC-18 | 首错：`TypeError` 只来自签名与 S0 门禁 | 错误顺序 | S0 | 签名是第一道拒绝面 |
| AC-19 | 首错：无部分结果、无错误信封、无兜底吞错 | 错误顺序 | S0–S8 / M1–M5 | 失败必须显式 |
| AC-20 | 结构禁令：holdout 与真实数据不可表达 | 结构性禁令 | S0 | 不可表达 > 约定禁止 |
| AC-21 | 结构禁令：provider/数据库/网络/文件系统面为零 | 结构性禁令 | S0 / N1–N3 | 无副作用是结构性的 |
| AC-22 | 结构禁令：路径、seed、排序与选择字段不可表达 | 结构性禁令 | S0 / V5（AC-22d 为组合入口，在 V5 命中） | 禁止键是闭集 |
| AC-23 | 结构禁令：不调用稳健性派遣，不复制统计实现 | 结构性禁令 | S6 / P6–P7 | 单一统计入口 |
| AC-24 | 授权：合成来源显式标记与解释边界透传 | 授权 | S6 / V2 | 合成证据不得升级 |
| AC-25 | 授权：注册表元数据非证据且不改变状态 | 授权 | S7 / RB1–RB6 | registry 元数据 ≠ 证据 |
| AC-26 | 授权：就绪 ≠ 授权（`execution_authorized` 恒 `False`） | 授权 | S4–S7 | 就绪不产生授权 |
| AC-27 | 回归：既有五套回归与治理测试保持通过、冻结 blob 不变 | 回归 | 全链 | 设计阶段不改既有契约 |
| AC-28 | 边界：`replications` 资源上界门 | 边界 | S3 / G11（G10 后，**仅 `enabled=true`**） | 资源界不等于统计充分性 |
| AC-29 | 确定性：decimal 上下文固定与跨 `prec` 字节相等 | 正常 | S0–S8 | 字节相等有环境前提 |
| AC-30 | 结构禁令：上游对象不可由调用者提交 | 结构性禁令 | S0 / V1 | 不可提交 > 运行时校验 |

### 1.1 合同要求覆盖映射（逐条对齐 Goal 的「Required behavior to freeze」）

| Goal 要求（`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md` 第 56–78 行） | 承载案例 |
| --- | --- |
| 1 单一公共编排入口 + 不可变结果信封（名称/输入/输出/版本/序列化/身份/导出面） | AC-01、AC-02、AC-03、AC-04 |
| 2 精确组合顺序 + 每阶段前后验证 + 不复制统计 + 不绕过既有验证器 | AC-05、AC-16、AC-17、AC-23 |
| 3 合成来源与授权门禁 + 注册表元数据与执行证据逻辑分离 | AC-20、AC-21、AC-24、AC-25、AC-26 |
| 4 确定性首错顺序 + 稳定错误码 + 异常映射 + 失败无部分结果 | AC-16、AC-17、AC-18、AC-19 |
| 5 跨产物绑定 + 精确摘要链 + 篡改检测责任 | AC-10、AC-11、AC-12、AC-13、AC-14、AC-15 |
| 6 不可变性 + 规范字节相等 + 重复运行确定性 + 有界资源 + 无副作用 | AC-02、AC-03、AC-13、AC-21、**AC-28**、**AC-29** |
| 7 可选 M4-B 记录作为元数据绑定 + 不改变状态/不触发执行 + 省略语义 | AC-08、AC-25 |
| 8 完整验收矩阵 + 后续 Goal 实现白名单 | 本文档全文 + 设计第 12.3 节 |
| 9 显式非目标与残余风险（含"不是通用真实数据研究执行器"） | 设计第 1.2、14 节 + AC-20、AC-23、AC-26 |

额外覆盖（设计新增的验收关注点）：AC-06（质量拒绝不降级）、AC-07（版本门禁）、
AC-09（bootstrap 两态）、AC-18（签名拒绝面）、AC-22（禁止键与 seed 不可表达）、
AC-27（回归与冻结 blob）、**AC-28**（资源上界）、**AC-29**（decimal 上下文）、
**AC-30**（上游对象不可提交）。

### 1.2 可达性分类（独立审查发现，冻结）

请求类型只接受 `config`/`bound_inputs`/`registry_record`，因此调用者**无法**把
合同/计划/准备数据/矩阵/执行产物提交给 `run_synthetic_pipeline`。全部案例因此必须标明其
**可达入口**，且该标注与设计第 8.5 节的入口级分类逐条一致：

| 类别 | 可达入口 | 案例 |
| --- | --- | --- |
| 组合入口 | `run_synthetic_pipeline(request=...)`（公开，S0–S8） | AC-12b、AC-13、AC-16、**AC-17a**、AC-17c、AC-17d、**AC-22d** |
| 信封层 | `validate_pipeline_result(forged_result, request)`（公开，V2/V6） | AC-15e、AC-15f |
| 阶段级探针 | **非**组合入口；直接调用既有阶段验证器，必须在本节显式标注 | AC-10、AC-11、AC-12a、AC-12c、AC-14、AC-15a–d、AC-17b、AC-17f |
| 内部投影探针 | **非**组合入口；直接调用既有**私有**投影助手（设计第 6.3 节禁止**编排器**调用私有助手，验收测试可显式标注后使用） | AC-17e |
| 静态证明 | 源码/AST/字段集检查，无运行时入口 | AC-02（子项）、AC-18g、AC-20、AC-21（子项）、AC-23、AC-30 |

**阶段级与内部投影探针的标注要求**：这些案例**不是**组合入口的验收，而是"既有阶段仍然
fail-closed"的回归证据。实现阶段必须把它们写成显式命名的独立测试，并在测试名或注释中标注
`STAGE_LEVEL_PROBE`（内部投影探针另标 `INTERNAL_PROJECTION_PROBE`）。**不得**把它们伪装成
组合入口的行为；**不得**为任何阶段级码编造组合入口路径。

**上游对象不可提交是结构性的**：`SyntheticPipelineRequestV1` 没有合同/计划/准备数据/矩阵/执行
产物字段，因此"用伪造上游对象驱动组合入口"在**类型层**不可表达（AC-30）。下列码因此在组合
入口上不可达，其真实可达面必须按第 1.2 节表格标注，**不得**写成组合入口行为：
`CONTRACT_PLAN_MISMATCH`（信封层：公开 `validate_pipeline_result` 的 V2；阶段级探针也可命中）、
`ARTIFACT_DIGEST_MISMATCH`（信封层 V2 与阶段级）、`PLAN_TERM_ROLE_MISMATCH`（只能由**内部投影
探针**证明，其公开路径被 `CONTRACT_PLAN_MISMATCH` 抢先，见 AC-17e）、`MATRIX_DIGEST_MISMATCH`
（阶段级的矩阵重哈希伪造）。

**注意不要过度归类**：`INPUT_DIGEST_MISMATCH`、适配器层 `IDENTITY_CONFLICT`、
`EVIDENCE_DIGEST_MISMATCH`、`ROLE_BINDING_MISMATCH` 等**仍然**可由调用者提交的 `bound_inputs`
在**组合入口**的 S4 触发（AC-13e–g、AC-17c、AC-17d；设计第 8.5.1 节 S4 行）；只有
"准备数据/矩阵被伪造"这一**阶段级**场景下的同名码（AC-14）才由探针证明。二者**不得**混为一谈。

---

## 2. 正常案例

### AC-01 正例：满秩合成链的完整信封

**输入变化**：合法 `SyntheticPipelineRequestV1`，`registry_record=None`，其余按第 0.5 节形状。

**预期结果**：
`run_synthetic_pipeline` 返回 `SyntheticPipelineResultV1`，且：

1. `metadata.pipeline_state == "SYNTHETIC_PIPELINE_COMPLETED"`；
2. `metadata.stages_completed` 逐项等于设计第 3 节 `REQUIRED_STAGES_COMPLETED`（6 项）；
3. `metadata.orchestrator_version == "M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V1"`；
4. `metadata.pipeline_schema_version == "M4_SYNTHETIC_PIPELINE_RESULT_V1"`；
5. 六个阶段对象字段的类分别为 `FrozenMechanismContract`、`DeterministicAnalysisPlan`、
   `DatasetPreparationV1`、`MatrixPreparationV1`、`ExecutionArtifactV1`，且
   `result.preparation.status == "READY_SYNTHETIC"`；
6. `result.execution.statistics_computed is True`、`result.execution.outcome_read is True`、
   `result.execution.execution_authorized is False`；
7. `result.preparation.execution_authorized is False`、`result.matrix.execution_authorized is False`；
8. `validate_pipeline_result(result, request)` 无异常返回。

**关键断言**：`result.execution.provenance.provenance_class == "SYNTHETIC_TEST_ONLY"`；
`result.execution.provenance.synthetic_test_only is True`；
`result.execution.provenance.real_data_used is False`；
`result.execution.provenance.holdout_accessed is False`。

**验证阶段**：S0–S8；`validate_pipeline_result` 的 V1–V6。

**授权解释**：证明"编排器在合成输入上跑通"。合成流水线就绪**不等于**真实研究授权，
也不是统计显著、经济有效、可交易或任何 A 股机制结论。

---

### AC-02 信封不可变性与公开导出面恰好 20 符号

**输入变化**：在 AC-01 成功信封上尝试写入。

**预期结果**：

1. `result.metadata.pipeline_state = "X"`、`result.execution = None`、
   `result.metadata.registry_binding = None` 各自抛出 `dataclasses.FrozenInstanceError`；
2. `result.metadata.stages_completed` 为 `tuple`，`result.metadata.registry_binding` 为
   `None` 或 `RegistryMetadataBindingV1`，字段类型中不含 `dict`/`list`/`set`；
3. `ashare_research.mechanism.pipeline.__all__` 的**集合**恰为设计第 4.4 节冻结的
   **20** 个符号（必须**机器计数**断言：`len(__all__) == 20` 且 `set(__all__)` 逐项相等；
   **不得**只数 `PIPELINE_*` 前缀，该前缀恰为 4 个）；
4. `mechanism/__init__.py`、`planning/__init__.py`、`datasets/__init__.py`、
   `execution/__init__.py`、`registry/__init__.py` 的 `__all__` 与实现前逐项相等。

**验证阶段**：S7；V1。

**授权解释**：证明"设计可用 ≠ 实现已授权"——本案例在实现前无法通过，因为模块不存在。

---

### AC-03 规范字节相等与重复运行确定性

**输入变化**：同一 `request` 连续调用两次；再用跨进程调用一次。

**预期结果**：

1. `serialize_pipeline_result(run(request)) == serialize_pipeline_result(run(request))`（同进程）；
2. 跨进程 `hashlib.sha256(serialize_pipeline_result(...)).hexdigest()` 相等；
3. 输出以 `b"\n"` 结尾且恰有一个；不含 `b"\r"`；
4. 解析回 JSON 后重新 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`
   与去掉末尾换行的原文逐字节相等（规范 JSON 自洽）。

**子案例**：

| 子案例 | 变化 | 预期 |
| --- | --- | --- |
| AC-03a | 同一 `request` 调用两次 | 字节相等 |
| AC-03b | `bound_inputs.observations` 以**不同元组顺序**给出（内容相同） | 字节相等（既有 `_input_payload` 按 `(trade_date, binding 序)` 排序） |
| AC-03c | 工作目录改为仓库外临时目录 | 字节相等 |
| AC-03d | **不同 numpy 版本**的解释器 | 允许 `artifact_digest` 与信封字节不同；本子案例只断言"差异被记录为已知环境差异"，**不**断言相等——见设计第 14 节 R10 |

**验证阶段**：S7–S8。

**授权解释**：可复现**不等于**可外推；字节相等只承诺同一解释器与同一 numpy 版本。

---

### AC-04 六层规范字典逐层使用既有投影

**输入变化**：对 AC-01 的 `result` 调用 `pipeline_result_to_canonical_dict`。

**预期结果**：

1. 返回字典的键集恰为 `{metadata, contract, plan, preparation, matrix, execution}`；
2. `payload["contract"] == contract_to_canonical_dict(result.contract)`；
   `payload["plan"] == plan_to_canonical_dict(result.plan)`；
   `payload["preparation"] == dataset_to_canonical_dict(result.preparation)`；
   `payload["matrix"] == matrix_to_canonical_dict(result.matrix)`；
   `payload["execution"] == execution_artifact_to_canonical_dict(result.execution)`；
3. `payload["metadata"]` **不含** `pipeline_digest`；
4. 改动返回字典的任意嵌套值后，`serialize_pipeline_result(result)` 不变。

**验证阶段**：S7。

**授权解释**：编排器只组合既有投影，不重定义任何既有 schema。

---

## 3. 边界案例

### AC-05 边界：最小可物化域

**输入变化**：把 `domain.expected_dates` 缩到既有适配器与矩阵仍能物化的最小长度，
并相应调整观测与 `input_digest`。

**预期结果**：要么成功返回且 `stages_completed` 完整，要么以既有 `AdapterError` /
`MatrixError` 稳定错误终止；两种结果都**不得**产生部分信封。若 `expected_dates` 为空元组，
`ExpectedDomainV1` 的 `__post_init__` 抛 `EMPTY_EXPECTED_DOMAIN`。

**验证阶段**：S3–S6。

**授权解释**：边界通过**不等于**统计有效；最小样本不构成任何有效性声明。

---

### AC-06 边界：质量拒绝在 S4 后终止

**输入变化**：构造覆盖率低于 `contract.data_quality_gates.coverage_gate` 的合成输入，
使 `preparation.status == "REJECTED_QUALITY"`。

**预期结果**：调用在 S4 之后、S5 之前终止，抛
`PipelineError("PIPELINE_QUALITY_NOT_READY")`，且其消息**携带**计划声明的处置词
（`contract.evidence_rule.data_quality_failure_disposition` ∈ `{"FAIL", "INCONCLUSIVE"}`）。
`result` 不返回；`preparation.complete_rows == ()`。

**关键断言**：

1. 编排器**不得**尝试补齐、插值、放宽 `coverage_gate`、改 `missingness_policy` 或重采样
   以使数据通过；
2. 首错**不是** `MatrixError("DATASET_NOT_READY")`，也**不是**
   `ExecutionError("DATA_QUALITY_REJECTED")`——后者在组合链上不可达（设计第 8.5 节）；
3. 既有执行层那个携带 `.disposition` 的码不可达，因此**处置词必须由编排器在消息中保留**，
   否则处置语义会在组合链上丢失。

**验证阶段**：S4；设计第 6.2 节 P4、第 8.5 节。

**授权解释**：不降级、不修补、不回退——质量门是拒绝面，不是调参面；且组合不得丢失既有处置语义。

> 二义性与语义丢失都已消除：设计第 6.2 节 P4 要求编排器在 S4 后**自己**判定
> `status == "READY_SYNTHETIC"`，唯一正确答案是 `PIPELINE_QUALITY_NOT_READY` + 处置词。

---

### AC-07 边界：版本常量不符

**输入变化**：分别把 `schema_version`、`orchestrator_version` 改为错误值或非字符串。

**预期结果**：`PipelineError("PIPELINE_VERSION_UNSUPPORTED")`，在 S0 抛出，
不进入 S1，不产生任何合同对象。

**验证阶段**：S0；G2。

**授权解释**：版本是门禁而不是提示；未知版本一律 fail-closed。

---

### AC-08 边界：省略注册表绑定是显式一等形态

**输入变化**：`registry_record=None`。

**预期结果**：

1. `result.metadata.registry_binding is None`；
2. `metadata.registry_binding_digest == canonical_digest({"binding_state": "NO_M4B_REGISTRY_METADATA_BOUND"})`；
3. `serialize_pipeline_result` 中 `metadata.registry_binding` 序列化为 `null`；
4. `validate_pipeline_result` 的 RB1–RB3 通过。

**子案例**：

| 子案例 | 变化 | 预期 |
| --- | --- | --- |
| AC-08a | `registry_record=None` | 上述四项 |
| AC-08b | 请求对象**缺省** `registry_record` 键（而非显式 `None`） | 构造即 `TypeError`（字段无默认值），证明"省略键"不可表达，因此省略语义可判定 |

**验证阶段**：S7；V4；RB1–RB3。

**授权解释**：省略有显式语义，不是缺省值填充；省略**不是**错误。

---

### AC-09 边界：计划声明的 bootstrap 两态

**输入变化**：分别构造 `bootstrap_policy.enabled = True` 与 `enabled = False`
（`method_id = "DISABLED"`）的合同。

**预期结果**：

1. `enabled = True` 时 `result.execution.bootstrap.enabled is True`，且
   `bootstrap.seed` 等于计划声明的 seed；
2. `enabled = False` 时 `result.execution.bootstrap.enabled is False`，区间端点为 `None`，
   不建立 generator；
3. 两种情况下信封都不含任何 seed 字段（seed 只在既有计划/产物内部）。

**验证阶段**：S6。

**授权解释**：编排器不发明统计语义，也不接收或派生 seed。

---

## 4. 篡改案例

### AC-10 篡改：合同字段被改（摘要未改）

**输入变化**：`dataclasses.replace` 改 `contract.evidence_rule` 的一个语义字段，保留原
`contract_digest`。

**可达性**：`STAGE_LEVEL_PROBE`（第 1.2 节）。**组合入口不可表达**：`SyntheticPipelineRequestV1`
没有合同字段，调用者只能提交 `config`，而 S1 会用 `compile_hypothesis_config(request.config)`
自行编译出一份**自洽**的合同——因此"提交一份摘要未更新的合同"在组合入口上不存在
（AC-30 已把这一点列为结构性保证）。本案例的探针入口是**直接调用**既有
`validate_contract(forged_contract)`。

**预期结果**：既有 `validate_contract` 重算 `compute_contract_digest` 并比对，
抛 `ContractCompilationError("CONTRACT_DIGEST_MISMATCH")`。

**验证阶段**：S1（阶段级探针）。

**授权解释**：上游篡改必须 fail-closed；摘要不是装饰。**不得**把本案例写成
`run_synthetic_pipeline` 的行为。

---

### AC-11 篡改：合同字段被改且摘要被重写

**输入变化**：改合同语义字段**并**用 `replace(..., contract_digest=compute_contract_digest(t))`
把摘要改成自洽值，再走完整调用。

**预期结果**：S1 的 `validate_contract` 通过（摘要自洽）；失败发生在 S2，由
`_validated_contract_dict` 的"重编译一致性"检查抛出既有 `ValueError`
（`NON_CANONICAL_CONTRACT`）或 `CONTRACT_DIGEST_MISMATCH`。**不得**产生任何结果对象。

**关键断言**：这证明设计第 9.4 节 T3 的第 2 级检测真实存在；编排器**不得**在 S1 重复该检查，
因此本案例的首错归属必须是 S2 而不是 S1。

**可达性**：`STAGE_LEVEL_PROBE`（第 1.2 节）。本案例构造一份**自洽的伪造合同**并直接交给
计划层；组合入口**无法**接收调用者提供的合同（AC-30），因此本案例只作为既有阶段仍然
fail-closed 的回归证据，**不得**写成组合入口的行为。

**验证阶段**：S2/阶段级。

**授权解释**：自我一致的伪造仍被"重编译 + 逐字节比对"拒绝。

---

### AC-12 篡改：计划字段/摘要被改

**输入变化**：三个子案例。

| 子案例 | 变化 | 入口 | 预期 |
| --- | --- | --- | --- |
| AC-12a | 改计划语义字段，保留 `plan_digest` | 阶段级探针：`validate_analysis_plan(forged_plan)` | `PLAN_DIGEST_MISMATCH` |
| AC-12b | 调用者改 **`config`**（如 `hypothesis_id`），使编排器在 S1/S2 编译出**不同的**合同与计划，而 `bound_inputs` 仍带着旧摘要 | 组合入口 | S3 的 `PIPELINE_INPUT_BINDING_MISMATCH`。**门禁归属**：改 `config` 会同时改变 `contract_digest`，因此通常由 **G9** 先命中（G10 与之同码，不可区分也不影响可观察行为）。**修正一处不可表达的早期表述**：调用者**不能**提交被篡改的计划，因而"调用者同步改了 `bound_inputs`"意味着提交一份**自洽的新请求**（那是合法请求，不是篡改路径，不会报错）；适配器的 `CONTRACT_PLAN_MISMATCH` 在组合入口上不可达（设计第 8.5.2 节） |
| AC-12c | 只改 `plan.source_contract_digest` | 阶段级探针：`validate_analysis_plan(forged_plan)` | 形态仍合法但摘要重算失败 → 既有 `ValueError`（`PLAN_DIGEST_MISMATCH`） |

**预期结果**：任一子案例都在 S2/S3 终止（AC-12b 在 S3；AC-12a/12c 在 S2 阶段级），
不进入 S5/S6。

**可达性**：AC-12b 为**组合入口**；AC-12a/12c 为 `STAGE_LEVEL_PROBE`（第 1.2 节）。

**验证阶段**：S3（组合入口）；S2（阶段级探针）。

**授权解释**：计划是绑定对象，不可改写；输入摘要不能"跟随"被篡改的计划——而"改了配置并
重新绑定输入"是一次合法的新请求，不是对旧绑定的篡改。

---

### AC-13 篡改：`bound_inputs` 摘要与观测级篡改

**输入变化**：七个子案例。

| 子案例 | 变化 | 预期错误 | 阶段 |
| --- | --- | --- | --- |
| AC-13a | `source_contract_digest` 改为其他 64 位十六进制 | `PIPELINE_INPUT_BINDING_MISMATCH` | S3 |
| AC-13b | `plan_digest` 改为其他 64 位十六进制 | `PIPELINE_INPUT_BINDING_MISMATCH` | S3 |
| AC-13c | `mode` 改为 `"REAL"` 或 `"UNKNOWN"` | `PIPELINE_UNSUPPORTED_MODE` | S3 |
| AC-13d | `schema_version` 改为其他值 | `PIPELINE_INPUT_SCHEMA_UNSUPPORTED` | S3 |
| AC-13e | 改一条观测的 `value`，`input_digest` 不变 | `EVIDENCE_DIGEST_MISMATCH`（观测级） | S4 |
| AC-13f | 改一条观测的 `value` 并重算 `input_digest` | `EVIDENCE_DIGEST_MISMATCH`（观测级先失败） | S4 |
| AC-13g | 改 `domain.calendar_evidence.evidence_digest` | `EVIDENCE_DIGEST_MISMATCH`（证据级） | S4 |

**关键断言**：AC-13c 的首错必须是编排器 S3 门禁的 `PIPELINE_UNSUPPORTED_MODE`，
**不是**既有适配器的 `UNSUPPORTED_MODE`（更不是执行层不可达的 `UNSUPPORTED_DATASET_MODE`）；
`input_digest` 的位级篡改与观测级篡改**分别**被两级检测覆盖，不存在"只改摘要就能过"的路径。

**验证阶段**：S3–S4。

**授权解释**：合成输入不可伪造；"合成"不是跳过证据摘要的理由。编排器门禁前置于适配器，
因此真实/未知 mode 在任何计算之前即被拒绝。

---

### AC-14 篡改：准备数据与矩阵逐层重哈希伪造

**输入变化**：四个子案例，全部沿既有测试已验证的伪造路径。

| 子案例 | 变化 | 预期错误 | 阶段 |
| --- | --- | --- | --- |
| AC-14a | 改 preparation 语义字段并重写 `dataset_digest` 自洽 | `IDENTITY_CONFLICT`（重算后逐字节不等） | S5 |
| AC-14b | 改 preparation 语义字段，保留 `dataset_digest` | `INPUT_DIGEST_MISMATCH`（`serialize_dataset` 自检） | S5 |
| AC-14c | 改 matrix 单元格并重写 `matrix_digest` 自洽 | `IDENTITY_CONFLICT`（重投影比对） | S5 |
| AC-14d | 改 matrix 单元格，保留 `matrix_digest` | `MATRIX_DIGEST_MISMATCH` | S5 |

**可达性**：四个子案例都是 `STAGE_LEVEL_PROBE`（第 1.2 节）。**组合入口不可表达**：
`SyntheticPipelineRequestV1` 没有 preparation/matrix 字段（AC-30）；探针入口是直接调用既有
`validate_design_matrix(forged_matrix, forged_preparation, contract, plan, bound_inputs)`
（a/b 的伪造对象是 preparation，经由 S5 链内的 `validate_dataset` 检出；c/d 的伪造对象是 matrix）。

**预期结果**：四个子案例全部在 S5 终止，**不**进入 S6，**不**产生任何统计量。AC-14d 由
`_validated_matrix_payload` 的自摘要重算检出；AC-14a/c 的"自洽伪造"由**重算 + 逐字节比对**检出。

**验证阶段**：S5（阶段级探针）；V2。

**授权解释**：重算 + 逐字节比对使"自洽的伪造"也不可表达。**不得**把本案例写成
`run_synthetic_pipeline` 的行为。

---

### AC-15 篡改：执行产物与信封逐层篡改

**输入变化**：六个子案例。

| 子案例 | 变化 | 预期错误 | 阶段 |
| --- | --- | --- | --- |
| AC-15a | 改 `execution.estimator` 一个系数，保留 `artifact_digest` | `ARTIFACT_DIGEST_MISMATCH` | S6 |
| AC-15b | 改系数并重写 `artifact_digest` 自洽 | `IDENTITY_CONFLICT`（V3 重执行 + V4 比对） | S6 |
| AC-15c | 改 `execution.source_chain` 任一字段 | `INVALID_INPUT_STRUCTURE` 或 `IDENTITY_CONFLICT` | S6 |
| AC-15d | 改 `execution.provenance.real_data_used` 为 `True` | `INVALID_INPUT_STRUCTURE`（`_check_provenance`） | S6 |
| AC-15e | 改 `result.metadata.pipeline_digest` | `PIPELINE_DIGEST_MISMATCH` | V6 |
| AC-15f | 改 `result.preparation` 并重写其 `dataset_digest`，同时改 `metadata.pipeline_digest` 自洽 | `IDENTITY_CONFLICT`（V2 既有链） | V2 |

**预期结果**：全部终止且不返回部分结果。AC-15f 证明"重写信封摘要"不能掩盖上游篡改，
因为 V2 会经由既有验证器重算上游。

**可达性**：AC-15a–d 为 `STAGE_LEVEL_PROBE`（把伪造产物交给既有 `validate_execution_artifact`）；
AC-15e/f 可经公开的 `validate_pipeline_result(forged_result, request)` 到达，属**信封层**（第 1.2 节）。
组合入口本身**不**接收执行产物（AC-30）。

**验证阶段**：S6（阶段级 a–d）；V2/V6（信封层 e/f）。

**授权解释**：全链身份覆盖到底；编排器新增的两层摘要不替代上游五层。

---

## 5. 错误顺序案例

### AC-16 首错：多故障并存时唯一的首错归属

**输入变化**：一次调用中**同时**注入多个故障，观察哪一个被报出。

**子案例**：

| 子案例 | 同时注入的故障 | 预期首错 | 首错阶段 |
| --- | --- | --- | --- |
| AC-16a | `schema_version` 错误 **且** 合同字段非法 **且** `mode="REAL"` | `PIPELINE_VERSION_UNSUPPORTED` | S0 |
| AC-16b | 合同非法 **且** `mode="REAL"` | 既有合同错误（`ContractCompilationError` / `HypothesisConfigError`） | S1 |
| AC-16c | `mode="REAL"` **且** `plan_digest` 不符 | `PIPELINE_UNSUPPORTED_MODE`（G7 早于 G10） | S3 |
| AC-16d | `plan_digest` 不符 **且** 观测 `value` 非规范十进制 | `PIPELINE_INPUT_BINDING_MISMATCH`（G10 早于 S4） | S3 |
| AC-16e | 观测重复 **且** 覆盖率不足 | `DUPLICATE_OBSERVATION`（`_validate_inputs` 内唯一性早于覆盖率判定） | S4 |

**预期结果**：每个子案例恰报出一个错误，且与表中阶段一致。实现**不得**收集多个错误、
不得并行求值、不得"挑一个更友好的"。

**验证阶段**：S0–S4；第 7.2 节门禁顺序。

**授权解释**：顺序是规范而非实现细节——首错不稳定就无法做确定性验收。

---

### AC-17 首错：既有错误码透传且不被改写

**输入变化**：分别触发既有六类错误中的一个代表码。

| 子案例 | 触发方式 | 可达入口 | 预期类型与码 |
| --- | --- | --- | --- |
| AC-17a | 调用者提供的 `config` 的 `holdout_policy` 与开发期重叠 | **组合入口**（S1） | `ContractCompilationError("DEVELOPMENT_HOLDOUT_OVERLAP")`。**修正早期标注**：本案例可由 `config` 表达，因此是组合入口可达，不是阶段级探针 |
| AC-17b | 伪造计划的方法不是 `DAILY_CONDITIONAL_CONTROLLED_OLS_V1`，再调用既有 `validate_analysis_plan(forged_plan)` | 阶段级探针（S2） | 既有**裸 `ValueError("UNSUPPORTED_ANALYSIS_METHOD")`**（`hasattr(exc, "code") is False`）。**为什么不用 `config` 触发**：配置层的类型化解析会先在解析阶段以自己的错误码拒绝未知方法，因此**计划层**的裸 `ValueError` 只由伪造计划的阶段级探针证明 |
| AC-17c | 绑定 role 序列与计划不符 | **组合入口**（S4） | `AdapterError("ROLE_BINDING_MISMATCH")` |
| AC-17d | `input_digest` 位级错误 | **组合入口**（S4） | `AdapterError("INPUT_DIGEST_MISMATCH")` |
| AC-17e | 交换计划 `design_plan.ordered_terms` 中两个 `term_role`，再**直接调用既有私有投影助手** `matrix_module._project_validated_matrix(preparation, forged_plan)` | **内部投影探针**（`INTERNAL_PROJECTION_PROBE`） | `MatrixError("PLAN_TERM_ROLE_MISMATCH")` |
| AC-17f | 把合法矩阵交给**组合链之外**的稳健性派遣入口 `prepare_registered_robustness_dispatch`，其注册参数含禁止键或含 `/` 的值 | 阶段级探针（组合链外） | `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")` |

**AC-17e 的精确可达性（修正一处虚构的公开路径）**：`PLAN_TERM_ROLE_MISMATCH` 是**下游纵深防御**，
在组合入口上**不可达**；即使把同一份伪造计划交给**公开**的矩阵验证器
`validate_design_matrix(matrix, preparation, contract, forged_plan, bound_inputs)`，也会先在
`validate_dataset` 的重编译比对处抛出 `AdapterError("CONTRACT_PLAN_MISMATCH")`（设计第 8.5.2 节）。
因此本案例必须双断言：(1) 内部投影探针得到 `PLAN_TERM_ROLE_MISMATCH`；(2) 公开阶段验证器得到
`CONTRACT_PLAN_MISMATCH`——两条都写下来，才既证明防御存在，又证明它**不是**组合入口行为。
**不得**把 `PLAN_TERM_ROLE_MISMATCH` 写成 `run_synthetic_pipeline` 的预期错误（设计第 6.3 节禁止
**编排器**调用私有助手，但验收测试可以显式标注后使用它）。

**预期结果**：异常的**类型**与 `.code` 与既有模块一致，`str(exc)` 不被前缀或包装；
调用方必须用 `getattr(exc, "code", str(exc))` 提取错误码——**不得**写
`except ValueError as exc: exc.code`，因为计划阶段的 44 个码是**裸 `ValueError`**，
没有 `.code` 属性（实测 `hasattr(exc, "code") is False`），直接取属性会 `AttributeError`。
同理，**不得**用 `str(exc)` 当码：当消息非空时 `str(exc)` 是消息而不是码。编排器**不得**
把它们改写成 `PIPELINE_*`，也不得用 `raise PipelineError(...) from exc` 替换。

**验证阶段**：S1–S6；M1。

**授权解释**：编排器不吞错、不改码；错误面增量最小。AC-17b/f 为**阶段级探针**、AC-17e 为
**内部投影探针**（第 1.2 节），均不得伪装成组合入口行为；AC-17a/c/d 为组合入口行为。

---

### AC-18 首错：`TypeError` 只来自签名与 S0 门禁

**输入变化**：以非法调用形态调用。

| 子案例 | 调用 | 预期 |
| --- | --- | --- |
| AC-18a | `run_synthetic_pipeline(config=config)` | `TypeError` |
| AC-18b | `run_synthetic_pipeline(cfg, bound)`（位置参数） | `TypeError` |
| AC-18c | `run_synthetic_pipeline(request=r, holdout=True)` | `TypeError` |
| AC-18d | `run_synthetic_pipeline(request=r, seed=7)` | `TypeError` |
| AC-18e | `run_synthetic_pipeline(request=r, real_data=True)` | `TypeError` |
| AC-18f | `run_synthetic_pipeline(request=r, path="C:/x")` | `TypeError` |
| AC-18g | 反射检查函数签名 | 恰一个 `KEYWORD_ONLY` 参数 `request`，无 `VAR_KEYWORD`、无 `VAR_POSITIONAL`、无默认值 |
| AC-18h | `run_synthetic_pipeline(request=object())` | `PipelineError("PIPELINE_REQUEST_TYPE_INVALID")`（S0 门禁，不是 `TypeError`） |

**预期结果**：AC-18a–f 为 `TypeError`（签名拒绝面）；AC-18h 为稳定 `PipelineError`。
两者分工明确：**签名**负责"不可表达"，**S0 门禁**负责"表达错误"。

**验证阶段**：S0；G1。

**授权解释**：签名是第一道拒绝面——holdout、seed、路径、真实数据开关在语法层就不可传。

---

### AC-19 首错：无部分结果、无错误信封、无兜底吞错

**输入变化**：对 AC-10 – AC-18 的每个失败路径检查返回面与异常面。

**预期结果**：

1. 任一失败路径都**不返回**任何对象（异常而非返回值）；
2. 信封类型**没有** `errors`、`ok`、`partial`、`warnings`、`status_code` 字段；
3. 编排器源码中不存在 `except Exception`、`except BaseException`、
   `contextlib.suppress`、`retry` 循环；
4. 若出现未映射的裸异常，唯一表现为
   `PipelineError("PIPELINE_INTERNAL_SOURCE_UNMAPPED")` 且 `__cause__` 保留原异常；
   该码**不得**被用于吞掉既有 `ValueError` 子类（M1 优先于 M3）。

**验证阶段**：S0–S8；M1–M5。

**授权解释**：失败必须显式；"看起来能跑"不能靠兜底实现。

---

## 6. 结构性禁令案例

### AC-20 结构禁令：holdout 与真实数据不可表达

**输入变化**：静态检查请求类型与编排器模块。

**预期结果**：

1. `SyntheticPipelineRequestV1` 的字段集恰为设计第 4.3 节的 5 个字段，不含 `holdout`、
   `holdout_window`、`real_data`、`provider`、`db`、`path`、`seed`、`token` 等任何同类名；
2. `SyntheticPipelineResultV1` 的字段集恰为 6 个阶段/元数据字段；
3. 编排器模块的导入集合不含 `duckdb`、`requests`、`urllib`、`http`、`socket`、`subprocess`、
   `os`、`pathlib`、`io`、`tempfile`、`shutil`、`glob`、`logging`、`threading`、
   `multiprocessing`、`asyncio`、`concurrent.futures`；
4. 编排器模块不导入 `mechanism/regression.py`、`bootstrap.py`、`robustness.py`、`evidence.py`、
   `crash.py`、`analysis_dataset.py`、`analysis_contracts.py`；
5. `hypothesis_config.load_hypothesis_config` **不被**编排器调用（它接收路径并读取文件）。

**验证阶段**：S0。

**授权解释**：不可表达优于约定禁止——没有入口就没有越权路径。

---

### AC-21 结构禁令：provider/数据库/网络/文件系统面为零

**输入变化**：在仓库外临时目录执行一次 AC-01，并在前后比对文件清单与工作目录。

**预期结果**：

1. 调用前后工作目录不变；
2. 调用前后（临时目录与仓库）相对文件清单不变，无新增/修改/删除；
3. `sys.modules` 中不出现 `duckdb`、`requests`、`urllib.request`——**仅限这三个**。
   **不得**断言 `socket`/`pathlib`/`pandas` 缺席：既有依赖链
   （`model_digest` → `analysis_contracts` → `pandas`）在完整导入后必然使它们出现在
   `sys.modules` 中（设计第 4.1 节 I4、第 11.4 节 N1 实测）。这类断言**不可满足**，
   会把正确实现判为失败；
4. 调用不产生任何 stdout/stderr 输出；
5. **AST / 源码级**断言（只针对新模块）：不含被禁的**直接**导入，也不含
   `open(`、`print(`、`socket.`、`os.`、`pathlib.` 的直接调用。这是唯一能覆盖"函数内部惰性导入"的静态手段；
6. **运行时探针**（在完整导入之后）：对 `builtins.open`、`Path.open`、`socket.socket`、
   `socket.create_connection` 打 monkeypatch 并断言零调用。这是仓库**既有**做法
   （`tests/test_m4_bounded_execution.py` 的 `no_external_io` 用例，实测通过），
   早期设计草案称其"与既有风格冲突"是**错误**的。

**验证阶段**：S0；N1–N3。

**授权解释**：无副作用是结构性的；但断言必须可满足——用"直接导入面 + 惰性调用探针"，
而不是对传递依赖做 `sys.modules` 缺席断言。

---

### AC-22 结构禁令：路径、seed、排序与选择字段不可表达

**输入变化**：对信封规范字典执行禁止内容检查。

**预期结果**：

| 子案例 | 变化 | 预期 |
| --- | --- | --- |
| AC-22a | 信封规范字典全部嵌套键（小写后） | 无一落在既有 24 键 `FORBIDDEN_KEYS` 中 |
| AC-22b | 向 `metadata` 注入键 `"path"` / `"Path"` / `"PATH"` | `FORBIDDEN_ARTIFACT_CONTENT`（大小写不敏感精确匹配） |
| AC-22c | 向 `metadata` 注入键 `"my_path"` | 通过（实测既有语义为**精确**匹配，不是子串匹配） |
| AC-22d | 合同声明的稳健性参数值含 `/`（如 `"A/B"`）或参数键为 `"path"`（**经计划投影进入信封**） | **组合入口**：在 S1–S6 **完整执行之后**由 **V5** 的整信封禁止内容检查命中，抛既有 `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")`——这是**既有**码，不是编排器新增码。**修正一处与实测不符的早期表述**：有界执行产物的 payload **不含**稳健性块，`execute_bounded_analysis` 在该参数下**会成功**；因此本案例不是"执行器内部扫描"的结果，而是信封层 V5 的结果（设计第 5.5 节 D6） |
| AC-22e | 注入含 `"AND/OR"` 的字符串值 | `FORBIDDEN_ARTIFACT_CONTENT`（`_ABSOLUTE_PATH_RE` 对任何 `/`+非空白命中） |
| AC-22f | 注入 `"2015-03-16"` / `"SYNTH_ROBUSTNESS_1"` / `"A-B"` | 通过（非命中样例） |
| AC-22g | 检查规范字典中是否存在 seed 字段或选择/排序/调优语义字段 | 均不存在 |

**关键断言**：`_ABSOLUTE_PATH_RE` 会对任何含 `/` 且其后为非空白的子串命中；因此信封中
**不得**出现任何含斜杠的字符串值（设计第 5.5 节 D6/D7）。

**AC-22d 的两条路径必须分开断言**：(1) **组合入口**的拒绝发生在 V5（上文），因为计划投影
携带了稳健性参数；(2) **组合链之外**的稳健性派遣入口 `prepare_registered_robustness_dispatch`
有**自己的**既有扫描（参数被逐字转发后受检），由 AC-17f 以显式标注的阶段级探针覆盖。
两者码相同、路径不同，**不得**混写成同一条执行器内部行为。

**验证阶段**：S0（入口可得投影的规则级检查）；V5/S7（AC-22b/c/d/e/f；其中 AC-22d 为组合入口）。

**授权解释**：禁止键是闭集；排序与选择不可表达。斜杠禁令是既有执行层的既有语义，
设计不改动它，但必须让它显式可见。

---

### AC-23 结构禁令：不调用稳健性派遣，不复制统计实现

**输入变化**：源码级检查 + 调用图检查。

**预期结果**：

1. 编排器模块中不存在对 `prepare_registered_robustness_dispatch` 的引用或调用；
2. 编排器模块中不存在对 `numpy`、`scipy`、`statsmodels`、`pandas` 的导入；
3. 编排器模块中不存在 OLS、bootstrap、均值/中位数/分位数、覆盖门、秩门或处置逻辑的任何实现
   （既无这些名字的函数，也无这些量的算术表达式）；
4. 唯一产生统计量的调用是 `execute_bounded_analysis`。

**验证阶段**：S6；P6–P7。

**授权解释**：单一统计入口；编排器不发明第二种统计实现。

---

## 7. 授权案例

### AC-24 授权：合成来源显式标记与解释边界透传

**输入变化**：AC-01 的成功信封。

**预期结果**：

1. `result.execution.provenance.provenance_class == "SYNTHETIC_TEST_ONLY"`；
2. `result.execution.evidence.interpretation_boundary` 逐字符等于既有
   `ashare_research.mechanism.execution.INTERPRETATION_BOUNDARY` 的值（编排器**不得**改写、
   缩写或翻译该字面量）。**注意字段路径**：它在 `evidence` 块内，**不在**
   `method_configuration` 内（独立审查实测确认）；
3. `metadata.interpretation_boundary` 逐字符等于设计第 3 节所引既有
   `INTERPRETATION_BOUNDARY` 常量值（编排器**不得**改写、缩写或翻译该字面量）；
4. 信封中不存在 `p_value`、`significant`、`established`、`recommendation`、
   `expected_return`、`tradable` 等同类语义字段。

**验证阶段**：S6；V2。

**授权解释**：合成来源证据不得升级为真实研究证据；解释边界是不可改写的字面量。

---

### AC-25 授权：注册表元数据非证据且不改变状态

**输入变化**：三个子案例。

| 子案例 | 变化 | 预期 |
| --- | --- | --- |
| AC-25a | 提供合法合成 `HypothesisRecordV1`，其 `hypothesis_id` 等于 `plan.hypothesis_id` | 成功；`binding_state == "M4B_REGISTRY_METADATA_BOUND_READ_ONLY"`；RB1–RB6 通过 |
| AC-25b | 提供 `hypothesis_id` 与计划不等的记录 | `PipelineError("PIPELINE_REGISTRY_IDENTITY_MISMATCH")` |
| AC-25c | 提供未通过 `validate_hypothesis_record` 的记录（或用 `object()` 冒充） | `PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")` |
| AC-25d | 提供**合法但处于执行态**的记录（`DEVELOPMENT_EXECUTED` / `ROBUSTNESS_EXECUTED` / `OOS_EXECUTED` / `NOT_ESTABLISHED` / `ESTABLISHED` / `INCONCLUSIVE`） | `PipelineError("PIPELINE_REGISTRY_STATUS_NOT_BINDABLE")`（设计第 10.4 节允许表：只允许执行前状态） |
| AC-25e | 提供处于允许表内状态（如 `NOT_TESTED`）的记录 | 成功绑定，且 `record_status` 等于该状态 |

**关键断言**（AC-25a）：

1. 传入的 `registry_record` 对象本身**未被修改**：调用前后
   `hypothesis_record_digest(record)` 与 `record.status`、`record.state_history` 逐项相等；
2. `result.execution` 的**任何**字段都不因提供记录而变化：与 AC-01（`registry_record=None`）
   相比，`serialize_execution_artifact(result.execution)` **逐字节相等**；
3. `registry_record.status` **不**影响 `metadata.pipeline_state`、`stages_completed` 或
   `execution.execution_authorized`；
4. 编排器不调用 `transition_hypothesis_record`、`validate_state_transition`、
   `build_hypothesis_registry_snapshot`；
5. 篡改 `binding.record_bytes_hex` 一个十六进制字符 → R5 重解析/摘要比对失败 →
   `PIPELINE_REGISTRY_RECORD_INVALID`；
6. `bytes.fromhex(binding.record_bytes_hex)` 逐字节等于 `serialize_hypothesis_record(record)`；
7. **无总尺寸上限、无尺寸门**（设计第 4.4 节 J4、第 14 节 R11）：`record_bytes_hex` 对每条**具体**
   记录都有限，且恰为 `2 × len(serialize_hypothesis_record(record))`；但既有 M4-B schema
   **不**对全体合法记录给出统一的有限上界——四个知识元组（`known_*`）的基数、`state_history`
   长度、`authorization_ref` 与 `schema_version` 均无上限。因此实现**不得**新增
   `MAX_RECORD_BYTES` 之类的编排器层尺寸门，也**不得**把测试里"有界文本骨架"的实测值声明为
   schema 总上界（只能说成该骨架的实测证据）；
8. **claim boundary**：处于执行态的记录**不可**绑定（AC-25d）；绑定**不**使信封出现任何
   "已执行/已建立/已提升"字段或取值。

**验证阶段**：S7；V4；RB1–RB6。

**授权解释**：registry 元数据 ≠ 证据；绑定是只读的，既不改变记录状态，也不触发执行。

---

### AC-26 授权：就绪 ≠ 授权

**输入变化**：AC-01 的成功信封。

**预期结果**：

1. `result.preparation.execution_authorized is False`；
2. `result.matrix.execution_authorized is False`；
3. `result.execution.execution_authorized is False`；
4. 信封中不存在任何"授权执行"或"授权真实数据"的字段或取值；
5. `metadata.pipeline_state` 是 `SYNTHETIC_PIPELINE_COMPLETED`，**不**是
   `ESTABLISHED`、`AUTHORIZED`、`READY_FOR_REAL_DATA` 或任何同类词。

**验证阶段**：S4–S7。

**授权解释**：跑通合成链不产生任何真实研究授权；本设计也不是通用真实数据研究执行器。

---

## 8. 回归案例

### AC-27 回归：既有测试与冻结 blob 不变

**输入变化**：无（本设计阶段不修改任何 `src/**`、`tests/**`、`reports/**`、`fixture`）。

**预期结果**：

1. 既有五套阶段回归测试全部通过（合同、计划、适配器、矩阵、有界执行 + M4-B 注册表）；
2. 既有项目入口与 Stage4P 治理测试全部通过；
3. `ruff check` 对既有 `mechanism` 包与既有测试文件通过；
4. 五个受保护冻结 blob 的 `git hash-object` 与设计第 13.3 节记录逐一相等；
5. 受保护数据库 SHA256 不变；stash 不变；原始 M2 工作树 HEAD 不变；
6. 变更路径集合恰为设计第 12.3 节/Goal 白名单列举的 **7 条**路径（`pipeline/__init__.py`、
   `pipeline/orchestrator.py`、`tests/test_m4_synthetic_pipeline_orchestrator.py`、`README.md`
   的措辞改动、实现 Goal、实现记录、实现验收），且与白名单**逐项相等**，无第 8 条路径。

**验证阶段**：全链（非编排器实现测试，而是设计阶段的真实回归）。

**授权解释**：本设计不改既有契约；编排器是**可加**设计。

---

### AC-28 边界：`replications` 资源上界门

**输入变化**：构造三份配置，其余相同。

| 子案例 | `bootstrap_policy` | 预期 |
| --- | --- | --- |
| AC-28a | `enabled=true`，`replications=1` | 既有 `ExecutionError("INSUFFICIENT_REPLICATIONS")`（实测可达） |
| AC-28b | `enabled=true`，`replications` 在 `[2, MAX_BOOTSTRAP_REPLICATIONS]` 内 | 成功；`bootstrap.replications` 等于声明值 |
| AC-28c | `enabled=true`，`replications > MAX_BOOTSTRAP_REPLICATIONS`（如 `10**9`） | `PipelineError("PIPELINE_REPLICATIONS_EXCEED_LIMIT")`，在 S3 内 G10 之后、S4 之前终止，**不**做任何重采样 |
| AC-28d | `enabled=false`（`method_id="DISABLED"`），即使 `replications` 声明为 `10**9` | 成功；不建立 generator；`bootstrap.replications` 为 `None`；上界门**不适用**——**G11 只在 `bootstrap_plan.enabled is True` 时求值**，该惰性声明不被拒绝 |

**关键断言**：

1. AC-28c 的拒绝**先于**任何 bootstrap 计算——不得"先跑再发现超界"；
2. 该上界是**编排器层策略**，**不**修改既有 `hypothesis_config.py`；
   直接调用既有 `execute_bounded_analysis` 的调用者**不受**该门约束（既有行为一字不变）；
3. 该上界**不**构成任何统计充分性、有效性或显著性的主张；它只是资源界的机械上限；
4. **G11 与 AC-28d 的冲突已显式解决**（设计第 7.1 节 G11、第 11.3.1 节 R17.2）：门的求值条件
   含 `bootstrap_plan.enabled is True`。理由是资源语义——上界约束的是**重采样工作量**，
   禁用 bootstrap 的计划**没有**重采样工作，其 `replications` 声明是惰性的。实现**不得**
   把该门写成对 `replications` 声明的无条件检查。

**验证阶段**：S3；G11（G10 后）；设计第 11.3.1 节 R17。

**授权解释**：有界资源是机械保证，不是统计保证。Goal 第 6 条的"bounded resource behavior"
由本案例承载（早期草案错误地把它挂在 AC-17 上）。

---

### AC-29 确定性：decimal 上下文固定与跨 `prec` 字节相等

**输入变化**：在**不同 ambient `decimal` 上下文**下执行同一次 AC-01 调用。

| 子案例 | `decimal.getcontext().prec` | 预期 |
| --- | --- | --- |
| AC-29a | 默认（28） | 与 AC-03a 字节相等 |
| AC-29b | 8 | 与 AC-03a 字节**相等**（编排器必须用 `decimal.localcontext(prec=28)` 覆盖宿主设置） |
| AC-29c | 4 | 与 AC-03a 字节**相等**（同上） |
| AC-29d | 8，且调用失败（任一**组合入口**失败路径，如 AC-13 或 AC-12b） | 调用前后 `decimal.getcontext()` 的 `prec`/`traps`/`flags` 逐字段不变（编排器**不得**写全局上下文） |

**关键断言**：

1. 编排器必须在 S0 之前进入 `decimal.localcontext()` 并把 `prec` 设为
   `DECIMAL_CONTEXT_PRECISION = 28`，在 S8 返回之前退出；整条 S0–S7 都在该上下文内求值；
2. **不得**修改全局 `decimal.getcontext()`；
3. 该门是必需的：实测同一代码、同一输入、同一 seed，在 `prec=28`/`8`/`4` 下
   `artifact_digest` 与序列化字节**互不相同**（伴随十进制分别为
   `0.24691357802487854` / `0.24691358` / `0.2469`），因为既有 `canonical_decimal` 与
   执行层 `_interval_indices` 读取 ambient 上下文；
4. C5 只固定 `prec`，**不**固定 traps/flags；AC-29 因此以"宿主保持默认陷阱设置"为前提，
   该前提必须在实现测试中显式记录（设计第 14 节 R16）。

**验证阶段**：S0–S8；C5/C6。

**授权解释**：字节相等有明确的环境前提；前提被写下来而不是被假设。

---

### AC-30 结构禁令：上游对象不可由调用者提交

**输入变化**：检查请求类型与导入面。

**预期结果**：

1. `SyntheticPipelineRequestV1` 的字段集**恰为** 5 个：`schema_version`、
   `orchestrator_version`、`config`、`bound_inputs`、`registry_record`；**没有**任何字段可以
   接收合同、计划、准备数据、矩阵或执行产物；
2. 因此"用一份伪造的合同/计划/矩阵去驱动编排器"**在类型层不可表达**——这是比任何运行时
   校验都强的结构性保证；
3. 需要验证伪造上游对象时的入口只有三类（且必须按第 1.2 节标注）：
   **信封层** `validate_pipeline_result(forged_result, request)`（AC-15e/f）；**阶段级探针**
   （AC-10、AC-11、AC-12a、AC-12c、AC-14、AC-15a–d、AC-17b、AC-17f）；
   **内部投影探针**（AC-17e，直接调用私有 `_project_validated_matrix`）。
   **不得**声称任何上游对象可由 `run_synthetic_pipeline` 提交；
4. 实现**不得**为"便于测试"而在请求类型上增加任何上游对象字段或 `**kwargs` 逃生口。

**验证阶段**：S0；V1。

**授权解释**：不可提交优于运行时校验；上游身份只由编排器自己编译产生。

---

## 9. 本设计阶段实际执行的验证（非实现测试）本节只记录**设计阶段**真实执行过的验证，不记录任何编排器实现测试（编排器不存在）。

| # | 验证 | 命令 / 方法 | 结果 |
| --- | --- | --- | --- |
| 1 | 基线分支与 HEAD | `git status --short --branch`、`git rev-parse HEAD` | 见 `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md` |
| 2 | 冻结 blob 未变 | `git hash-object` 五个受保护文档 | 与设计第 13.3 节逐一相等 |
| 3 | 受保护数据库未变 | `Get-FileHash -Algorithm SHA256` | 与 Goal 记录相等 |
| 4 | 既有回归测试 | Goal「Required validation commands」中的 pytest 命令 | 记录实际退出码与通过数 |
| 5 | 静态检查 | `ruff check src/ashare_research/mechanism …` | 记录实际结果 |
| 6 | Markdown 链接/锚点确定性校验 | 仓库外临时路径的校验脚本 | 记录实际结果；工作树不留生成物 |
| 7 | 五个阶段副作用面静态扫描 | 对五个模块的 import 与 `open(`/`requests`/`duckdb`/… 模式扫描 | 零命中 |

> 本设计阶段**没有**运行任何编排器测试，因为编排入口**尚未实现**。AC-01 – AC-30 在实现阶段
> 才可执行；AC-27 中的回归部分在本阶段已执行。

---

## 10. 实现阶段的验收顺序要求

实现阶段（另行授权的 Goal）必须按下列顺序验收，不得跳步：

1. 先断言**结构性禁令**：AC-20、AC-21、AC-22、AC-23、**AC-30**。任何一个失败即停止，
   不得用"功能测试通过"掩盖结构性越权。
2. 再断言**授权面**：AC-24、AC-25、AC-26。特别是 AC-25a 的
   "提供记录不改变执行产物字节"与"记录对象未被修改"，以及 AC-25d 的
   **执行态记录不可绑定**（claim boundary）。
3. 再断言**首错与异常映射**：AC-16、AC-17、AC-18、AC-19。
4. 再断言**篡改检测**：AC-10 – AC-15，逐层从下到上。AC-11 与 AC-15f 是两条
   "自洽伪造"的关键反例，必须在实现中被真实复现。按第 1.2 节把 AC-10、AC-11、AC-12a、AC-12c、
   AC-14、AC-15a–d、AC-17b、AC-17f 写成显式标注 `STAGE_LEVEL_PROBE` 的独立测试，把 AC-17e 写成
   显式标注 `INTERNAL_PROJECTION_PROBE` 的独立测试，**不得**伪装成组合入口行为；
   AC-12b、AC-13、AC-16、AC-17a、AC-17c、AC-17d、AC-22d 则必须是真实组合入口调用，
   AC-15e/f 必须是公开 `validate_pipeline_result` 调用。
5. 再断言**边界与资源**：AC-05、AC-06、AC-07、AC-08、AC-09、**AC-28**。AC-06 的预期首错是
   `PIPELINE_QUALITY_NOT_READY` 且消息按冻结模板携带处置词；AC-28c 的拒绝必须**先于**任何
   bootstrap 计算，且 AC-28d 必须证明 `enabled=false` 时该门**不**适用。
6. 再断言**正常与确定性**：AC-01、AC-02、AC-03、AC-04、**AC-29**。AC-03d 的跨 numpy 版本差异
   与 AC-29 的跨 `prec` 断言方向相反：AC-03d **记录**环境差异，AC-29 **要求**字节相等
   （因为编排器必须自己固定 `prec`）。
7. 最后断言**有界资源**：设计第 11.3 节的三项调用次数上界**已经**是实测值
   （`build_analysis_plan <= 12`、`materialize_analysis_dataset <= 11`、`_execute <= 3`），
   实现必须逐项断言 `<=` 并记录实测计数；计数打在公共产出者符号上，因此必须同时统计编排器直调
   与既有验证器触发的链式重算。**不得放宽**这三个上界；实测若超出，属设计缺陷，
   须回到设计评审而**不是**就地放宽。
8. 全程回归：AC-27 的六项在实现阶段每一步后重跑。

---

## 11. 边界声明

- 本文与配套设计文档都是**设计规范**，不是实现、不是证据、不是执行授权。
- 编排入口
  `ashare_research.mechanism.pipeline.run_synthetic_pipeline`
  **尚不存在**；本文**不声称**任何编排器测试已通过。AC-01 – AC-30 在实现前**不可执行**；
  其中 AC-10、AC-11、AC-12a、AC-12c、AC-14、AC-15a–d、AC-17b、AC-17f 明确标注为**阶段级探针**，
  AC-17e 明确标注为**内部投影探针**（第 1.2 节）。
- 本文不含任何真实候选、真实引用、真实论文/教材内容、真实 A 股结果、系数、区间、p 值或处置。
- 本清单**不构成**实现授权、统计执行授权、真实数据授权、真实候选/注册数据集授权、
  文献采集授权、provider/数据库访问授权、holdout 授权或 M4-B 授权。
- 合成流水线就绪只表示"五阶段组合顺序已冻结 + 门禁与身份链已冻结 + 产物可复现"，
  不表示任何统计性质，也不表示任何 A 股机制结论。
- 合成来源证据与解释边界字面量**不得**升级为真实研究证据或研究结论。
- `M4 SYNTHETIC PIPELINE NOT IMPLEMENTED`；真实假设执行 `NOT AUTHORIZED`；
  真实注册表数据 `NOT AUTHORIZED`；holdout 访问 `NOT AUTHORIZED`。
- 推送、PR、合并与进入实现/下一阶段各需单独明确授权。
