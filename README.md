# A-Share Research Lab

> A股价值评估与市场机制验证实验室

本地运行、免费数据优先的可解释研究平台。提供数据底座、中石油价值评估切片、日频机制研究记录，以及通用假设合同与分析计划编译能力。
仅用于数据分析、统计研究和软件工程学习，不构成投资建议，也不提供自动交易能力。

## 当前可用能力

主线已包含 PIT/TTM 修复、A.2 冻结设计、A.2I 计划编译、合成数据适配器、不可变设计矩阵与仅限合成 fixture 的有界执行器（PR #9、#11、#12、#13 均已合并）。有界执行器只在合成 fixture 上计算系数、bootstrap 区间与证据处置；没有通用研究执行器，真实数据执行与 holdout 仍未授权。M4-B 最小元数据注册表 API 已实现，仅用于合成/schema 校验；真实注册表数据、文献采集与真实假设执行仍未授权。五个合成阶段（合同 → 计划 → 合成数据集 → 设计矩阵 → 有界执行）的单一端到端编排入口已按冻结设计实现为**仅合成、纯内存**的编排器 `run_synthetic_pipeline(request=...)`。该编排器只接收调用者提供的合成策略输入，自己编译合同/计划/准备数据/矩阵/执行产物，输出不可变、规范序列化、摘要绑定的结果信封；它不新增真实数据能力，不改变任何既有冻结契约，也不产生任何研究、显著性、可交易性或 A 股机制结论。

| 能力 | 当前状态 | 如何使用 | 限制 | 证据 |
| --- | --- | --- | --- | --- |
| M1 数据底座 | 已实现 | 下方数据获取 CLI；Parquet/DuckDB 存储 | 获取需网络，免费源可能失效 | [数据服务测试](tests/test_data_service.py) |
| M2 价值评估 | M2 已条件关闭；中石油 PIT 切片 | 下方离线胶囊；真实输入需显式提供 | ROIC 证据不足；PE 数值评分暂缓，无生产排名 | [完成矩阵](reports/m2_value_assessment_completion_matrix.md)、[缺口台账](reports/m2_explicit_gap_ledger.md) |
| M3 机制验证 | CONDITIONALLY CLOSED；日频机制未建立 | 阅读开发期研究与最终处置 | holdout primary inconclusive；不支持因果或行为主体推断 | [最终验收](acceptance/m3_stage3e_daily_mechanism_final_disposition_and_milestone_closeout_preflight.md) |
| M4-A.1 假设合同 | CANONICAL ON MAIN | 下方 Python 编译接口与合成测试 | 仅配置校验、合同冻结和摘要，没有通用研究执行器 | [编译验收](acceptance/m4_stage4a1_typed_hypothesis_config_and_frozen_contract_compiler.md) |
| M4-A.2 分析计划 | 已在主线（冻结设计 + A.2I 计划编译实现） | 下方 `build_analysis_plan(contract)` Python 入口与合成测试 | 计划编译已实现；统计执行仅限合成 fixture；没有通用研究执行器；holdout 始终不授权执行 | [冻结设计](reports/m4_stage4a2_deterministic_analysis_plan_design_v1.json)、[实现验收](acceptance/2026-09-07_m4a2i_analysis_plan_compiler.md) |
| M4-A.2D 合成数据适配器 | 已在主线（PR #11） | `materialize_analysis_dataset(contract, plan, bound_inputs)` 与合成测试 | 仅合成模式；不读取真实数据、provider、数据库或行情 | [适配器设计](docs/m4_dataset_adapter_design_v1.md)、[适配器测试](tests/test_m4_synthetic_dataset_adapter.py) |
| M4-A.2M 设计矩阵 | 已在主线（PR #12） | `materialize_design_matrix(preparation, contract, plan, bound_inputs)` 与合成测试 | 质量边界内的投影；本身不含回归、bootstrap、稳健性或证据判定 | [矩阵设计](docs/m4_analysis_matrix_design_v1.md)、[矩阵测试](tests/test_m4_analysis_matrix.py) |
| M4-A.2E 有界执行 | 已实现（仅合成 fixture）；真实执行未授权 | 下方 `execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs)` 与合成测试 | 只在已验证合成 fixture 上计算 OLS/bootstrap/处置；无 provider、数据库、holdout 或 M4-B；注册稳健性只派遣不计算 | [设计](docs/m4_bounded_execution_and_evidence_design_v1.md)、[验收案例](docs/m4_bounded_execution_acceptance_cases_v1.md)、[执行测试](tests/test_m4_bounded_execution.py)、[实现验收](acceptance/2026-09-12_m4_bounded_execution_implementation.md) |
| M4-A.2P 端到端编排 | 已实现（仅合成、纯内存）；真实执行未授权 | 下方 `run_synthetic_pipeline(request=...)` 与 [合成测试](tests/test_m4_synthetic_pipeline_orchestrator.py)；调用者按两遍协议提供 `config` 与 `bound_inputs` | 只编排已验证合成输入；请求类型无 holdout、真实数据、provider、数据库、路径或 seed 字段；不做质量修补、排序、选择、注册表状态转换或真实研究结论；跑通合成链**不等于**研究授权 | [设计](docs/m4_synthetic_end_to_end_pipeline_design_v1.md)、[验收案例](docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md)、[实现验收](acceptance/2026-09-13_m4_synthetic_pipeline_post_ac05_acceptance.md) |
| M4-EIA-PIT 离线进度检查 | 已实现（只读、离线、固定路径诊断） | `python agent/tools/check_m4_progress.py`（`--json` 可选） | 只复核冻结的 EIA 传输/PIT 元数据证据；不联网、不写文件、不读取原始观测值或凭据；不构成完整 K2 或全项目就绪结论，也不授权研究或执行 | [工具](agent/tools/check_m4_progress.py)、[测试](tests/test_m4_progress_check.py) |
| M4 合成演示 CLI | 已实现（离线、仅合成、固定样例） | `python -m ashare_research.synthetic_demo`（`--json` 可选） | 只跑固定的虚构 24 行示例；没有输入/配置/seed/provider/数据库/输出路径/注册表参数；合成演示不等于真实研究授权 | [模块](src/ashare_research/synthetic_demo.py)、[测试](tests/test_m4_synthetic_demo_cli.py) |
| M2 离线研究包 | 已实现（固定来源汇编、离线、无新计算） | `python -m ashare_research.tools.value_research_bundle`（`--json`、`--output NEW_DIR`、`--verify DIR`） | 只汇编九个固定基线报告：混合日期历史汇编，不是统一 PIT 查询或研究刷新；无总体评分、排名、资格或建议；缺失证据不视为 0 或负面结论 | [模块](src/ashare_research/tools/value_research_bundle.py)、[测试](tests/test_value_research_bundle.py) |
| M2 既有指标 PIT 重放 | 已实现（离线只读、内存重放既有七个指标） | 下方 `python -m ashare_research.tools.pit_metric_replay` | 只用既有已批准定义，无新公式/评分/排名/建议；缺失保持缺失；重放不是发布 | [模块](src/ashare_research/tools/pit_metric_replay.py)、[测试](tests/test_pit_metric_replay.py) |
| M4-B 理论/假设注册表 | 最小元数据 API 已实现（仅合成/schema 校验） | `ashare_research.mechanism.registry` 的 `parse_hypothesis_record(document)`、显式状态转换与有界快照入口 | 不创建或加载真实候选数据集，不采集文献，不访问 provider、数据库、真实行情或 holdout；真实假设执行仍未授权 | [设计](docs/m4b_hypothesis_registry_design_v1.md)、[验收场景](docs/m4b_hypothesis_registry_acceptance_cases_v1.md)、[实现测试](tests/test_m4b_hypothesis_registry.py)、[实现验收](acceptance/2026-09-12_m4b_hypothesis_registry_implementation.md)、[冻结前置合同](reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json) |

### 研究结论与边界

**Milestone 2: CONDITIONALLY CLOSED; SCORING ADDENDUM CONDITIONALLY CLOSED**。
PE 决定为 `PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE`；原始 PE 和 3Y/5Y 分位仅作描述证据。ROIC 保持 `not_computable_under_strict_evidence_contract`，没有替代数值。

M3 最终处置为 `M3_DAILY_MECHANISM_NOT_ESTABLISHED`。Holdout 已使用一次性解封机会，但覆盖率 `0.9736963544070143` 低于冻结门槛 `0.99`，状态为 `M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`，未运行 holdout 回归/bootstrap。

### 历史停止与当前授权

历史脉络见 [阶段历史](docs/project-history.md)。为区分当时与当前，保留以下验收声明：

- M3 Stage 3A research contracts are frozen. Stage 3B completed fail-closed. Stage 3B-R1 primary-proxy resolution is current within the frozen M3 market-proxy lineage.
- At M3 closeout, further holdout recovery, minute escalation, index contribution, and M4 were not authorized.
- Historical M3 closeout stop: `STOP_FOR_NORTH_STAR_REVIEW`.
- Subsequently, M4-A.1 has since been implemented and canonicalized on main. M4-A.2 design, A.2I compile-only plan compilation, the synthetic dataset adapter, the immutable design matrix and the synthetic-fixture-only bounded executor are merged on main. The M4-B minimum metadata registry is implemented for synthetic/schema validation only. The M4-A.2P synthetic end-to-end pipeline orchestration design is IMPLEMENTED as a synthetic-only, in-memory composed entry (`run_synthetic_pipeline`); the design is no longer design-only, and its orchestrator is no longer missing. A generic research executor, real-data execution and holdout remain unauthorized; a real M4-B registry dataset and literature acquisition remain NOT AUTHORIZED, real hypothesis execution remains NOT AUTHORIZED, and real-research M4-B NOT STARTED.
- No real mechanism inference beyond the frozen development-primary and registered robustness execution has been executed.

## M4 假设配置与研究计划入口

将自己的假设配置交给现有 M4 编译器，直接查看冻结合同、分析计划和所需数据：

```powershell
ashare-research research plan --hypothesis docs/examples/m4_hypothesis.json
ashare-research research plan --hypothesis MY_HYPOTHESIS.json --json
ashare-research research plan --hypothesis MY_HYPOTHESIS.json --output new-plan-package
ashare-research research plan --verify new-plan-package --json
ashare-research research plan --hypothesis MY_HYPOTHESIS.json --archive new-plan.zip
ashare-research research plan --verify-archive new-plan.zip --json
```

可复制并编辑 [示范配置](docs/examples/m4_hypothesis.json) 的条件、窗口、控制项等。
当前 V1 仅支持既有合成身份与词汇；真实身份策略会拒绝，未新增真实研究能力。
Markdown 显示数据角色、序列、观测时序、样本窗口、质量门槛、模型项、bootstrap、
稳健性注册和 holdout 边界。JSON 保留原编译器的规范配置、冻结合同、完整分析计划
及其摘要，并记录实际加载源文件的 SHA256。格式变化只改变源文件摘要；
研究语义变化按原编译器改变合同和计划身份。

仅读取显式 UTF-8 JSON（最多 1MiB），拒绝重复键、非有限常量、非对象根和无效配置；
错误时无部分结果。无需配置数据库，不联网、不获取数据、不运行统计或访问 holdout。
`FROZEN` 和摘要只是编译结果的内容身份，不代表独立封存、历史证据审查或执行授权；
`research_ready` 与各执行状态保持 false。输出到 stdout，文件留存由调用者选择。

计划包包含原始 `hypothesis.json`、完整 `plan.json`、可读 `plan.md` 和
`manifest.json` 字节清单。可将整个目录移到其他位置再复核；复核使用当前安装的编译器
重新编译包内假设，逐字节检查全部文件，不联网或执行统计研究。原始假设只读取一次。
输出必须是现有父目录下的新目录，已有文件或目录、符号链接及 Windows 重解析路径均拒绝。
写入失败返回错误，保留部分输出供检查；不会覆盖、删除或自动重试该目录。
复核要求恰好四个普通文件，缺失、额外文件或任意内容改动均拒绝。清单和编译摘要只证明
一致性；不验证作者、独立封存、历史来源或真实研究就绪，也不构成执行授权。

也可直接生成单文件 ZIP，再用 `--verify-archive` 在内存中复核，无需解压或创建中间目录。
ZIP 内容与目录计划包一致，输出仍必须是现有父目录下的新文件；已有路径不覆盖。
原生 ZIP 固定四个普通成员、无压缩、无附加字段或注释，文件顺序及元数据固定。
复核限制包与成员大小，在解析前限制中央目录；拒绝重复、危险路径、目录、链接、压缩、
加密、CRC 损坏及内容不一致。ZIP 字节摘要仍只是内容标识，不表示独立封存或执行授权。

两份计划可以先完整复核，再对比规范配置、冻结合同和数据／方法要求：

```powershell
ashare-research research plan-compare --left old-plan-package --right-archive new-plan.zip
ashare-research research plan-compare --left-archive old-plan.zip --right-archive new-plan.zip --json
```

源文件 SHA256 与配置、合同、计划摘要分开展示；仅 JSON 格式变化会显示源摘要不同，
规范内容变化为零。差异按对象和 JSON Pointer 列出完整前后值，缺失与 `null` 分开，
列表按原始索引比较。比较只读，不推断对象对齐、方案优劣或执行授权；任一输入复核失败
即返回错误，不输出部分对比。目录与原生 ZIP 可混用，现有 ZIP 格式限制继续适用。

已复核计划可与显式虚构输入一起做数据及矩阵准备检查：

```powershell
ashare-research research prepare --package new-plan-package --inputs docs/examples/m4_bound_inputs.json
ashare-research research prepare --archive new-plan.zip --inputs docs/examples/m4_bound_inputs.json --json
ashare-research research prepare --archive new-plan.zip --inputs MY_INPUTS.json --summary --role FACTOR --gaps-only
```

`--summary` 提供质量诊断速览，可用重复的 `--role` 选择角色，并用 `--gaps-only`
只展示所选角色的无效单元及原始原因、日期和证据引用。角色计数始终覆盖全部审计日期，
全局覆盖分母、拒绝日期、准备状态和摘要保持原样；已知角色没有缺口会明确提示。
这些筛选只能与 `--summary` 合用。速览不显示观测值或矩阵单元，也不计算统计结果；
省略新参数仍输出完整的原准备报告。

[输入示例](docs/examples/m4_bound_inputs.json) 绑定上述示范假设，包含四个显式虚构日期，
不是真实交易日历。输入沿用现有 `BoundDatasetInputsV1`：日历、成员、角色、观测与
摘要必须显式提供并相互一致；修改假设或数据后应通过既有 API 重新绑定摘要，工具不会修补。
仅读取显式 UTF-8 JSON（最多 1MiB），不获取数据、不写文件。输出完整质量诊断和矩阵；
质量拒绝保留缺口且矩阵为 `null`。退出码 0 只表示诊断生成，`READY_SYNTHETIC` 不代表
可估计或执行授权。检查仅读取显式提供的合成观测，不运行回归、秩检查、bootstrap 或 holdout，
也不把合成模式或摘要解释为真实来源证据。

## M4 离线进度检查（只读，无网络）

一条命令复核已冻结的 EIA 传输/PIT 元数据证据，输出确定性的当前研究阻塞与最小下一步；不需要参数选择根目录、路径或来源：

```powershell
python agent/tools/check_m4_progress.py
python agent/tools/check_m4_progress.py --json
```

工具只读取固定的仓库内元数据（dossier、allowlist 授权的 authorization/goal/ledger 链接、保留的 PIT 评估），校验链接摘要与冻结身份，重算评估并与保留字节逐字比对，不信任旧的 readiness 标记。它不联网、不写文件、不读取原始观测值、密文、凭据或数据库。

- 退出码 0：诊断完成，证据校验通过，研究仍被历史 PIT 证据缺失阻塞（`research_ready=false`、`execution_authorized=false`、三个 `REAL_*_MISSING` 原因码）。
- 退出码 2：证据校验失败（摘要/链接/重复键/保留评估不一致等），只输出净化后的错误码，不输出原始值或 traceback。

范围仅为 `FROZEN_EIA_TRANSPORT_DOSSIER_ONLY`：这不是完整 K2 或全项目就绪评估。下一步是单独授权的第一方历史 PIT 证据审查（publication/availability/revision-vintage），之后才考虑任何新采集或执行。

## 系统要求

- Python >= 3.11
- Windows / macOS / Linux
- 不需要数据库服务器

---

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

---

## M4-A.1 Python 接口

接口位于 `ashare_research.mechanism.hypothesis_config` 与 `ashare_research.mechanism.contract_compiler`：
`load_hypothesis_config(path)` / `parse_hypothesis_config(document)` → `compile_hypothesis_config(config)` → `serialize_frozen_contract(contract)`。
返回 `FrozenMechanismContract`；通过 `validate_contract` 验证，以 `compute_contract_digest` 计算摘要。
只编译合同，不获取数据或执行统计研究；目前没有 M4 执行 CLI。

完整合成配置与用法见 [类型化合同测试](tests/test_m4_stage4a1_typed_contract.py)。安装后可离线运行：

```powershell
python -m pytest -q tests/test_m4_stage4a1_typed_contract.py
```

## M4-A.2I Python 接口

在已有 `FrozenMechanismContract` 上编译不可变的 `DeterministicAnalysisPlan`：

```python
from ashare_research.mechanism.planning import (
    build_analysis_plan,
    plan_to_canonical_dict,
    serialize_analysis_plan,
    compute_plan_digest,
    validate_analysis_plan,
)

plan = build_analysis_plan(contract)
validate_analysis_plan(plan)
payload = plan_to_canonical_dict(plan)  # 独立副本
encoded = serialize_analysis_plan(plan)  # UTF-8、排序键、紧凑 JSON、结尾换行
digest = compute_plan_digest(plan)
```

计划声明语义角色、有序控制项、条件、窗口、质量门槛和调度规则。
Bootstrap 只声明块长策略；稳健性及证据规则只保存调度说明。
编译不读取数据、不计算回归或 bootstrap，也不授权 holdout。
合成数据适配（`ashare_research.mechanism.datasets`）与不可变设计矩阵
（`ashare_research.mechanism.planning.matrix`）已在主线；
有界执行器（`ashare_research.mechanism.execution`）已按
[有界执行与证据处置设计 v1](docs/m4_bounded_execution_and_evidence_design_v1.md)
实现，但只处理已验证的合成 fixture。
仅需安装依赖即可运行 [合成计划测试](tests/test_m4_stage4a2i_analysis_plan.py)：

```powershell
python -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py
```

## M4-A.2E Python 接口（仅合成 fixture）

在已验证的五元组 `(matrix, preparation, contract, plan, bound_inputs)` 上运行冻结的
OLS / moving-block bootstrap / 证据处置，或只绑定注册稳健性派遣：

```python
from ashare_research.mechanism.execution import (
    execute_bounded_analysis,
    execution_artifact_to_canonical_dict,
    serialize_execution_artifact,
    validate_execution_artifact,
    prepare_registered_robustness_dispatch,
    robustness_artifact_to_canonical_dict,
    serialize_robustness_artifact,
    validate_robustness_artifact,
)

artifact = execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs)
validate_execution_artifact(artifact, matrix, preparation, contract, plan, bound_inputs)
encoded = serialize_execution_artifact(artifact)  # UTF-8、排序键、紧凑 JSON、结尾换行

dispatch = prepare_registered_robustness_dispatch(
    matrix, preparation, contract, plan, bound_inputs, ("SYNTH_ROBUSTNESS_1",)
)
```

八个入口都必须接收完整五元组，没有只吃 `matrix` 的路径，也没有 `**kwargs`：
任何未声明关键字（`holdout=`、`window=`、`split=`、`real_data=`）都是 `TypeError`。
每个入口都先用既有 `validate_design_matrix` 重新验证来源链，再读取任何取值。
`execute_bounded_analysis` 是唯一的**统计执行**入口；`prepare_registered_robustness_dispatch`
只验证请求、绑定注册项并完整转发既有 canonical parameters，
其产物 `statistics_computed` / `outcome_read` 恒为 `False`，
不计算任何稳健性统计量，也不含选择、排序或聚合字段。
产物是显式 `SYNTHETIC_TEST_ONLY` 来源、不可变、可复算摘要；
`execution_authorized` 恒为 `False`。

限制与授权边界：这些入口只在合成 fixture 上就绪，不读取真实数据、provider、数据库或行情，
不访问 holdout，也不授权 M4-B；合成执行就绪**不等于**真实研究授权，也不是统计显著、
经济有效、可交易或任何 A 股机制结论。可运行
[有界执行验收测试](tests/test_m4_bounded_execution.py)：

```powershell
python -m pytest -q tests/test_m4_bounded_execution.py
```

## M4-A.2P Python 接口（仅合成、纯内存编排）

单一公共入口把五个已冻结阶段串成一条确定性链，并输出不可变结果信封：

```python
from ashare_research.mechanism.contract_compiler import compile_hypothesis_config
from ashare_research.mechanism.datasets import BoundDatasetInputsV1
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import build_analysis_plan
from ashare_research.mechanism.pipeline import (
    ORCHESTRATOR_VERSION,
    PIPELINE_SCHEMA_VERSION,
    SyntheticPipelineRequestV1,
    bound_inputs_identity_payload,
    run_synthetic_pipeline,
    serialize_pipeline_result,
    validate_pipeline_result,
)

# 第一遍：先编译合同与计划，学到两个摘要（调用者缓存它们）
contract = compile_hypothesis_config(config)
plan = build_analysis_plan(contract)

# 第二遍：用**公开**负载函数计算 input_digest，再构造请求
input_digest = canonical_digest(
    bound_inputs_identity_payload(contract, plan, domain, bindings, observations)
)
bound_inputs = BoundDatasetInputsV1(
    "M4_BOUND_SYNTHETIC_DATASET_V1", "SYNTHETIC",
    contract.contract_digest, plan.plan_digest,
    domain, bindings, observations, input_digest,
)

request = SyntheticPipelineRequestV1(
    schema_version=PIPELINE_SCHEMA_VERSION,
    orchestrator_version=ORCHESTRATOR_VERSION,
    config=config,               # 已解析的 HypothesisConfig
    bound_inputs=bound_inputs,   # 调用者声明的合成输入
    registry_record=None,        # 显式 None => REGISTRY_BINDING_ABSENT（一等形态）
)
result = run_synthetic_pipeline(request=request)
validate_pipeline_result(result, request)
encoded = serialize_pipeline_result(result)  # UTF-8、排序键、紧凑 JSON、恰一个结尾换行
```

只做门禁、转发与组合：合同、计划、准备数据、矩阵与执行产物全部由编排器自己编译，
调用者**无法**提交它们（请求类型只有 5 个字段）。`run_synthetic_pipeline` 只有一个关键字专用参数 `request`，
因此 `holdout=`、`real_data=`、`provider=`、`db=`、`path=`、`seed=` 在语法层就是 `TypeError`。
整条 S0–S7 在固定的 `decimal.localcontext(prec=28)` 内求值，宿主全局上下文不被改写。
编排器不定义任何统计、数值、质量判定或摘要算法：统计量只来自 `execute_bounded_analysis`，
摘要只来自既有 `canonical_digest` 与既有 `compute_*_digest`；它不做文件、网络、环境、
数据库、holdout 或文献访问，也不做质量修补、排序、选择、推荐或注册表状态转换。

可选的 M4-B 记录只作为**只读、非证据**元数据绑定：绑定不改变记录状态、不进入执行产物、
不参与 `PIPELINE_STATE`，且只允许执行前状态（`DISCOVERED`、`LITERATURE_REVIEWED`、
`A_SHARE_FEASIBILITY_REVIEWED`、`NOT_TESTED`、`PRE_REGISTERED`、`DEFERRED`）；
处于执行态的记录一律以 `PIPELINE_REGISTRY_STATUS_NOT_BINDABLE` 拒绝。

限制与授权边界：该入口只在调用者提供的**合成**策略输入上就绪；它没有真实数据、provider、
数据库、行情或 holdout 的可表达位置，也不创建真实候选数据集或采集文献。合成流水线就绪
**不等于**真实研究授权，也不是统计显著、经济有效、可交易或任何 A 股机制结论。
可运行 [编排器验收测试](tests/test_m4_synthetic_pipeline_orchestrator.py)：

```powershell
python -m pytest -q tests/test_m4_synthetic_pipeline_orchestrator.py
```

## 一次生成完整离线研究交付

首次使用可按 [交付指南](docs/m2_delivery_handoff.md) 走通“生成 ZIP → 接收复核 →
恢复浏览 → 比较内容”，其中包含可执行命令、回执解读与失败后的处理方法。

将档案、指标速览、证据缺口台账与可选两时点对比放到一个带导航的新目录：

```powershell
ashare-research research workflow --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-offline-workflow
ashare-research research verify --package tmp/m2-offline-workflow --json
```

打开 `tmp/m2-offline-workflow/index.md` 即可浏览。指定 `--compare-with` 时包含
`session/`、`review/`、`audit/`、`compare/` 共 131 个文件；未指定时包含前三类包，
共 80 个文件。各子目录保留原有完整包格式，可以单独复核；根目录复核还检查导航、
完整清单及全部嵌套文件。年度、指标和口径选择器与既有档案一致，支持重复 `--year`
和 `--metric`，不请求日期则不会使用当前日期补齐。

生成前先组装全部字节，只接受不存在且不经过符号链接的输出路径。失败不覆盖或清理
调用方已有路径；迟到的写入失败会保留自有的部分目录用于检查，返回错误而非成功。
这不是原子目录发布。内容沿用固定来源、原有计算与证据限制；价值资料的混合日期不
变成统一 PIT 证据，缺失原始父记录不会被补造，验证不授予真实研究或生产资格。

### 将完整研究资料作为一个文件交付

直接从请求生成已完整复核的 ZIP，无需创建中间目录：

```powershell
ashare-research research deliver --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-direct-delivery.zip --json
```

支持与 `workflow` 相同的日期、重复 `--year` / `--metric` 和 `--scope` 查询条件；
`--as-of` 必填，未请求对比时包含 80 个文件，请求对比时包含 131 个文件。
命令在自有临时目录组装原有工作流，再完整复核并生成相同格式的确定性 ZIP。
只写指定的新 ZIP，成功返回既有打包回执；失败不输出成功结果。输出存在或经过
符号链接时在组装前拒绝；迟到的写入失败保留自有部分 ZIP，不覆盖或清理调用方
文件，也不承诺原子发布。该入口沿用固定来源及原有研究、证据限制。

已经有研究目录时，仍可分别打包、复核和恢复：

```powershell
ashare-research research archive --package tmp/m2-offline-workflow --output tmp/m2-offline-workflow.zip --json
ashare-research research archive --verify tmp/m2-offline-workflow.zip --json
ashare-research research archive --restore tmp/m2-offline-workflow.zip --output tmp/m2-offline-workflow-restored --json
```

支持价值包、档案、速览、缺口台账、对比及完整工作流六类目录。打包前完整复核，
只使用本次验证返回的规范字节，不在验证后重新读取源文件。ZIP 使用排序的文件名、
固定日期与权限、不压缩存储；相同包在不同目录打包得到相同 ZIP 字节和 SHA256。
解包先在自有临时目录中检查成员并逐字节验证整包，再创建新目标目录；根索引和
嵌套包的原有格式保持不变。ZIP 的 CRC 或清单哈希相符不能替代内容复核。

接收方可以用 `--verify ZIP` 直接完整复核，无需指定或创建恢复目录。该模式与恢复
共用有界读取、安全成员检查和整包内容复核，临时解码仅写入自有临时目录。
成功返回 `status: verified`、原 ZIP 的 SHA256、文件数量、清单摘要与完整验证说明；
失败返回退出码 2，不输出成功结果。`--verify` 不接受 `--output`，打包和恢复仍
必须提供新输出路径。复核不会修改原 ZIP，也不生成附加文件。

只接受新输出路径，拒绝符号链接祖先和源包内部的 ZIP 输出。恢复拒绝路径穿越、
重复或大小写冲突、Windows 设备名、链接及非普通文件、加密或不支持的压缩方法、
损坏 ZIP 和超限成员。上限为 256 文件、单文件 32 MiB、解包总量 128 MiB、ZIP
129 MiB；成员名最多 512 字节、路径最多 32 层，在前缀检查前拒绝超限元数据。
恢复不调用 `extractall`。错误不会覆盖或清理调用方路径；迟到的写入
失败保留自有部分输出并返回错误，不承诺原子发布。恢复需要兼容的已安装固定基线，
不证明真实性、历史可得性，也不改变研究或生产资格。

### 直接阅读交付包中的指标与证据

不必先恢复目录，即可阅读已完整复核 ZIP 中的速览、缺口台账或既有两时点对比：

```powershell
ashare-research research read --archive tmp/m2-direct-delivery.zip --section review
ashare-research research read --archive tmp/m2-direct-delivery.zip --section audit --json
ashare-research research read --archive tmp/m2-direct-delivery.zip --section compare
```

也可用 `--package DIR` 读取工作流目录或对应的独立速览／台账／对比包。
`--json` 返回完整原报告和整包复核说明；默认沿用原报告的可读格式。未生成对比
部分的工作流会返回 `SECTION_NOT_PRESENT`。读取只使用本次完整验证返回的规范
字节，不在验证后重新读取源文件，也不创建调用方恢复目录。

要比较两次交付中的财务指标，而非文件字节，可直接使用档案或完整工作流 ZIP：

```powershell
ashare-research research compare --left-archive old.zip --right-archive new.zip --json
ashare-research research compare --left-archive tmp/m2-direct-delivery.zip --right-archive tmp/m2-direct-delivery.zip --right-view compare_with
```

每侧可改为原有的 `--left SESSION_DIR`／`--right SESSION_DIR`。ZIP 会完整验证
外层报告和嵌套档案，再取其中的原始指标记录；视图选择、比较规则和可选
`--output NEW_DIR` 的独立可复核导出格式保持不变。数值、单位、输入事实与证据
缺口原样保留；这些功能不重新证明历史发布，也不补齐来源或授予研究资格。

### 按研究问题聚焦缺口台账

读取 `audit` 时可按指标、指标年度或事实 ID 筛选，三个参数均可重复。
`--gaps-only` 只保留原台账有 gap 代码的事实及原有缺失输入：

```powershell
ashare-research research read --archive delivery.zip --section audit --metric cash_based_free_cash_flow_proxy --year 2023 --gaps-only
ashare-research research read --package WORKFLOW_DIR --section audit --fact FACT_ID --json
```

年度按指标的原引用用途匹配，例如 2023 年同比仍包含其 2022 年输入事实。
事实 ID 匹配已选输入或直接父引用；多个事实取并集，再与指标／年度条件取交集。
事实筛选不包含缺失输入，因为缺失角色没有已选事实 ID。显示保留来源缺失字段、
未解决父数、原 gap 代码、匹配用途和原缺失原因；父引用保留原状态。
JSON 使用 `m2_verified_focused_audit_view_v1`，在 `source_read` 留存完整原台账及
整包复核说明。未知指标／年度／事实分别返回 `METRIC_NOT_SELECTED`、
`YEAR_NOT_SELECTED`、`FACT_NOT_REFERENCED`；已知条件无交集时明确返回空结果，
不表示证据齐全。`--fact` 和 `--gaps-only` 仅用于 `audit`；
无效参数会在读取来源前拒绝。
没有筛选时原报告显示和 JSON 保持原样；筛选不补齐证据、计算指标或判断质量。

### 按指标和年度阅读速览或缺失结果

读取 `review` 时也支持可重复的 `--metric` 和 `--year`，可加
`--missing-only` 只看原值为 null 的结果：

```powershell
ashare-research research read --archive delivery.zip --section review --metric cash_based_free_cash_flow_proxy --year 2023
ashare-research research read --package WORKFLOW_DIR --section review --year 2025 --missing-only --json
```

选择条件取交集；原值、单位、状态、输入日期上界、缺失角色和历史年度原样保留。
两时点对比保留任一选中行对应的完整原条目，因此缺失结果的另一个时点可能有值。
零值不会被当作缺失；各时点事实条数仍是原速览总数，并非筛选后的输入数量。
JSON 使用 `m2_verified_focused_review_view_v1`，`source_read` 保留完整复核源，
`review` 包含选中行和对应原始对比。未知指标／年度返回上述错误码；
已知条件没有匹配时明确显示空结果。`--missing-only` 仅用于 `review`。
没有筛选时保持原输出；选择不会重新计算指标或补齐证据。

### 逐项追溯指标的原始证据

指定指标和年度，可直接从完整工作流或研究档案的 ZIP／目录查看两个请求时点
的原始指标记录、输入角色、事实 ID、来源字段和未解决父记录：

```powershell
ashare-research research trace --archive tmp/m2-direct-delivery.zip --metric cash_based_free_cash_flow_proxy --year 2023
ashare-research research trace --package tmp/m2-offline-workflow/session --metric cash_based_free_cash_flow_proxy --year 2023 --json
```

输出沿用档案中原有的指标比较类别，不重新计算或解释变化原因。JSON 保留完整
输入、上下文、溯源和来源引用；可读输出突出原始值与证据缺口。仅有一个请求
时点时只显示该时点。未选择的指标或年度返回 `METRIC_NOT_SELECTED`，缺失值
保持缺失。读取前完整复核整包，只消费本次返回的规范字节，无需恢复目录。

拿到事实 ID 后，使用反向查询查看交付包内引用它的全部所选指标、年份和时点：

```powershell
ashare-research research trace --archive tmp/m2-direct-delivery.zip --fact FACT_ID
ashare-research research trace --package tmp/m2-offline-workflow --fact FACT_ID --json
```

结果区分原始指标输入与直接父记录引用，保留完整指标记录和输入证据。查询未
留存的父记录只会展示已有引用及其原始状态，不表示已取得该父记录，也不推断
间接依赖或因果影响。查询范围限于包内请求的指标和时点；没有引用时返回
`FACT_NOT_REFERENCED`。`--fact` 不与 `--metric` 或 `--year` 混用。

### 同时比较指标与输入证据

要把指标差异与输入证据一起比较，在既有指标比较命令加上 `--evidence`：

```powershell
ashare-research research compare --left-archive old.zip --right-archive new.zip --evidence
ashare-research research compare --left SESSION_DIR --right-archive new.zip --right-view compare_with --evidence --json
```

原指标分类和值保持不变；逐输入角色展示左右事实 ID、原始值、状态，以及
实际变化的原始字段，包括来源引用和父记录。JSON 保留完整原比较与输入，并
区分未记录字段和空值。未变化角色也保留，输入缺失与指标未选择分别显示。
只报告字段差异，不推断变化原因或证据质量。`--evidence` 不与 `--output` 混用；
未加该标志的显示和交付格式保持原样。

### 聚焦指标、年度与变化项

普通比较或证据比较都可按原比较中的指标／年度筛选，两者均可重复指定：

```powershell
ashare-research research compare --left-archive old.zip --right-archive new.zip --metric cash_based_free_cash_flow_proxy --year 2023 --changes-only
ashare-research research compare --left SESSION_DIR --right-archive new.zip --right-view compare_with --evidence --metric cash_based_free_cash_flow_proxy --year 2023 --changes-only --json
```

普通“只看变化”沿用原指标分类；证据模式还包含输入字段变化，并只展开变化
角色。JSON 使用明确的聚焦格式，保留完整原报告、筛选条件和匹配项；未加
筛选的原输出保持原样。已知选择没有匹配项时成功返回空结果；未知指标或
年度分别报 `METRIC_NOT_COMPARED`／`YEAR_NOT_COMPARED`。筛选不与 `--output`
混用，也不重新计算指标、补齐缺失或推断变化原因。

### 从事实引用定位相关指标比较

把 `trace --fact` 查到的事实 ID 用于两份档案比较，直接查看原始输入或直接父
引用它的指标；`--fact` 可重复，多个事实取并集，再与指标、年份及变化筛选取交集：

```powershell
ashare-research research compare --left-archive old.zip --right-archive new.zip --fact FACT_ID
ashare-research research compare --left SESSION_DIR --right-archive new.zip --right-view compare_with --fact FACT_ID --evidence --year 2023 --changes-only --json
```

引用表标明左／右、指标、角色、输入／直接父引用及父记录原状态。JSON 使用
`m2_verified_fact_comparison_v1`，在 `comparison.source_report` 保留完整原报告，
同时保留匹配引用的原始输入和父记录。引用表描述匹配指标的原始引用；“只看变化”
仍可列出这些指标中未变化角色的引用，不表示该事实造成变化。任何未知事实返回
`FACT_NOT_REFERENCED`；已知事实与其他条件没有交集时成功返回空结果。空事实 ID
或与 `--output` 混用会在读取来源前拒绝。未留存的父记录仍未解决，不推断间接
影响或重新计算指标；未指定事实时原显示、筛选和交付格式保持原样。

### 一页对比速览

在任何指标比较上加 `--summary`，集中显示左右请求视图、日期、原值／单位／
状态、原比较分类，以及选中的证据角色和直接事实引用：

```powershell
ashare-research research compare --left-archive old.zip --right-archive new.zip --summary
ashare-research research compare --left SESSION_DIR --right-archive new.zip --right-view compare_with --fact FACT_ID --evidence --changes-only --summary
ashare-research research compare --left-archive old.zip --right-archive new.zip --evidence --metric cash_based_free_cash_flow_proxy --year 2023 --summary --json
```

速览保留缺失／未选择的区别，明确显示空结果和原始限制，不展开证据字段 JSON。
`--summary --json` 使用 `m2_verified_comparison_summary_v1`，保留完整 `source_report`、
原始指标行、已选证据角色和匹配引用。金额与 ratio 均不换算，也不计算差额或排名。
速览沿用已完成的完整复核及筛选，不重新读取来源；不可与 `--output` 混用。
未加 `--summary` 时原有完整显示、JSON 和交付格式保持原样。

### 对比两次交付的文件变化

```powershell
ashare-research research diff --left-archive old.zip --right-archive new.zip --json
ashare-research research diff --left tmp/m2-offline-workflow --right-archive tmp/m2-direct-delivery.zip
```

每侧明确选择目录或 ZIP，支持六类研究包和混合输入；两边必须是相同包类型。
先完整复核两边内容，再按相对路径比较规范字节，列出新增、移除、内容变化和相同
文件，以及前后字节数和 SHA256。ZIP 压缩方式不同但文件字节相同，会报告内容相同。
默认输出可读摘要和变化文件，`--json` 返回全部排序条目、计数及两侧完整复核说明。
该命令不修改源文件或创建调用方目录，ZIP 临时解码使用自有临时目录。
文件差异不表示财务事实或历史发布版本变化；既有财务指标 `compare` 入口保持原样。
验证仍依赖兼容固定基线，不证明真实性、历史可得性或研究资格。

## 统一离线研究入口（`ashare-research research`）

既有离线工作流与完整研究档案通过同一个顶层入口暴露，参数原样转发给各自工具的 `main(argv)`：
`report` → `value_research_bundle`、`facts` → `pit_fact_explorer`、`metrics` →
`pit_metric_replay`、`demo` → `synthetic_demo`：

```powershell
ashare-research research --help
ashare-research research report
ashare-research research report --json
ashare-research research facts --as-of 2024-03-31 --compare-with 2025-03-31 `
  --concept net_profit_attributable_to_parent --period-end 2023-12-31
ashare-research research metrics --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023
ashare-research research metrics --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 `
  --output tmp/m2-unified-research-entry
ashare-research research demo --json
ashare-research research session --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 `
  --output tmp/m2-research-session
ashare-research research session --verify tmp/m2-research-session
```

- 入口自身不加载配置、不初始化日志或数据服务，也不联网；真实分派发生在旧全局参数解析
  之前，因此 `ashare-research --config x research report` 与
  `ashare-research research --config x report` 都以退出码 2 拒绝，而不是静默忽略。
- 子命令帮助（如 `ashare-research research facts --help`）、参数校验、渲染、输出路径保护
  与错误码全部由既有工具负责：`report` 已知失败退出码 1，`facts`/`metrics` 已知失败退出码
  2，未知子命令退出码 2；本入口不复制任何解析器或报告计算。
- 离线与来源限制与各工具一致：`report` 只汇编九个固定基线报告（混合日期历史汇编，不是
  统一 PIT 查询）；`facts`/`metrics` 只读取仓库内固定快照
  `tests/fixtures/stage2g/canonical_fact_snapshot_v1`（`601857.SH`、33 条事实、只有
  `consolidated` 口径，未来事实永不入选）；`demo` 只运行固定的虚构 24 行合成示例。
  四个子命令都不获取新数据、不写默认数据库，也不产生评分、排名、建议或研究结论。

## 一次生成完整研究档案

`research session` 将价值报告、历史事实查询与指标重放组合为一个新目录，共 24 个文件。
`index.md` 是阅读入口，链接到 `value/` 的固定报告与九个原始附件、`facts/` 的时点事实和
对比、`metrics/` 的既有指标重放。`snapshot/` 保留四个字节不变的规范快照文件，根清单记录
23 个文件的长度与 SHA256，各子工具清单也保留。使用相同参数会生成相同文件字节。

导出需显式提供 `--as-of` 和 `--output NEW_DIR`，可选 `--compare-with`、重复 `--year`、
重复 `--metric` 和 `--scope`；这些指标选择沿用原有七个指标。事实部分保留该口径全部
可用事实，年度或指标筛选只作用于指标部分。已存在的目录、文件或符号链接会被拒绝；
输入或来源校验失败不创建输出目录，写盘阶段的 IO 失败可能留下本工具已经创建的部分输出。

`--verify DIR` 不接受查询参数。它从档案清单读取并验证查询条件，使用已安装的兼容固定
仓库基线和指标定义重新生成整份档案，逐字节比较全部文件和完整清单；因此仅修改报告后
重算清单校验和仍会失败。复核拒绝缺失、额外文件和符号链接，移动档案目录后仍可复核。
它证明固定基线下的完整性与可复现性，不提供数字签名或历史发布时间证明。

价值部分仍是混合日期历史汇编，不能当作统一时点结论；事实和指标才按查询日期分别选择。
快照仍只有中石油 33 条事实，66 个原始父记录缺失；留存的可用日期未重新证明。指标重放
不是已发布的历史指标版本，现金自由流仍为代理指标，ROE 沿用既有年度平均权益约定。
档案不补齐上述证据缺口，也不新增数据采集、评分、建议或真实研究执行。

## 已复核档案的研究速览

```powershell
ashare-research research review --session tmp/m2-research-session
ashare-research research review --session tmp/m2-research-session --json
ashare-research research review --session tmp/m2-research-session --output tmp/m2-research-review
ashare-research research session --verify tmp/m2-research-review/session
```

`review` 先复核完整档案，再整理各时点的年度指标表、原有重述对比状态和缺失角色年度。
小数文本、单位、状态、输入事实 ID、引擎结果 ID 和输入日期上界全部原样保留，不舍入、
不换算百分数、不产生新公式或研究结论。Markdown 默认输出，`--json` 与 `--output` 互斥。
导出目录包含 `review.md`、`review.json`、完整不变的 `session/` 及外层完整性清单，共27文件；
速览相对链接指向随附证据，移动目录后嵌套档案仍可按原命令复核。外层清单仅为文件完整性
目录，不提供新的真实性证明。已有路径拒绝覆盖，输入损坏不创建最终输出目录；写盘失败
可能保留工具已创建的部分输出。默认终端输出只列证据文件名，完整可点击证据使用导出模式。
价值汇编的混合日期、历史发布未证明、33事实/66缺失父记录等边界继续保留。

## 指标输入的证据缺口台账

```powershell
ashare-research research audit --session tmp/m2-research-session
ashare-research research audit --session tmp/m2-research-session --json
ashare-research research audit --session tmp/m2-research-session --output tmp/m2-evidence-audit
ashare-research research session --verify tmp/m2-evidence-audit/session
```

`audit` 先复核完整档案，再把指标输入按“查询日期 + 事实 ID”汇总，列出每条事实被哪些
指标、年度和输入角色引用。JSON保留原始小数值、来源字段、上下文、父记录ID和指标结果ID；
Markdown集中显示缺失来源字段、未解决父记录与受影响指标。不同日期的引用分开保留，
相同日期的重复引用不会重复计数；缺失角色单独列出原有预期年度、概念及缺失原因。
计数区分按时点事实行、跨时点唯一事实ID与所用事实涉及的唯一未解决父记录ID，不能把
所选指标的局部统计当作整个规范快照的覆盖率。空口径有缺失角色，不表示证据齐全。

台账只描述已留存证据缺口，不判断财务质量、研究就绪或生产资格；缺失来源字段不等于
来源不存在，缺失父记录不等于事实数值错误。`--json`与`--output`互斥；导出27文件，包含
完整不变的嵌套档案及相对证据链接，外层清单仅为完整性目录。已有路径拒绝覆盖，损坏输入
不创建输出目录；写盘阶段失败可能留下本工具已创建的部分输出。历史发布/可得性缺口保留。

## 两份已复核研究档案的对比

```powershell
ashare-research research compare --left tmp/m2-research-session --right tmp/m2-research-session --right-view compare_with
ashare-research research compare --left tmp/session-a --right tmp/session-b --json
ashare-research research compare --left tmp/m2-research-session --right tmp/m2-research-session --right-view compare_with --output tmp/m2-session-compare
ashare-research research session --verify tmp/m2-session-compare/left
ashare-research research session --verify tmp/m2-session-compare/right
```

`compare` 先完整复核两份档案，按指标ID与年度对齐选定视图。`--left-view`与`--right-view`
默认`as_of`，可明确选择已请求的`compare_with`；缺少该视图或不同合并口径会拒绝比较。
日期可以正向、逆向或相同；两份档案可以选不同年度/指标，但新增/移除选择独立列出，
不当作财务事实新增/消失。共同选择沿用既有指标比较规则，区分状态、原值、输入变化与
相同；不计算差额、百分比或收益，也不推断变化原因。页面展示两边完整选择条件，JSON
保留完整原始结果、输入小数值、缺失角色、来源字段和未留存父记录。

`--json`与`--output`互斥；导出51文件，包括`compare.md/json`、两份完整不变的24文件
档案`left/`与`right/`及外层完整性清单。相对证据链接随目录移动；嵌套档案仍用原验证命令。
外层清单只为文件目录，未提供新的签名或真实性证明。已有路径拒绝覆盖，输入损坏不创建
最终输出目录；写盘失败可能留下工具已创建的部分输出。固定基线、混合日期汇编、缺失父
记录与历史发布/可得性限制继续保留；缺失不是零，同日相同不是历史发布证明。

速览、证据台账和档案对比复用完整验证时已经生成并逐字节核对的规范字节，减少重复构建：
速览/台账每份档案构建一次，对比左右各一次。报告与导出文件保持原样；每次调用仍重新
验证全部档案，不按路径缓存，也不会在验证后重新打开可变的留存文件。Python接口
`research_session.load_verified_session(directory)`返回验证元数据和本次已验证的规范字节；
原`verify_session(directory)`继续只返回相同元数据。返回字典属于调用者，各次调用独立。

## 完整研究导出包的统一复核

```powershell
ashare-research research verify --package tmp/m2-research-review
ashare-research research verify --package tmp/m2-evidence-audit
ashare-research research verify --package tmp/m2-session-compare-reused --json
```

`verify` 从根清单识别五种既有包：价值汇编、完整档案、速览、证据台账和档案对比。
速览/台账/对比包会重新生成外层报告，连同完整嵌套证据和根清单逐字节比较；因此即使
修改报告后重新填写哈希，也不能通过。它还拒绝缺失/多余文件或目录、符号链接、未知
类型及无效选择器；清单中记录的任意路径不会被用于读取文件。移动完整目录后仍可复核。

命令不修改输入包，不缓存结果；重建只使用工具自己的临时目录。成功输出类型、文件数、
清单摘要和验证边界；`--json`保留请求/对比视图等完整元数据。失败退出码2，错误已净化，
stdout保持为空。原清单本身仍只是完整性目录，本命令另行证明整个包与兼容的已安装
固定基线/代码一致；不证明签名、真实性、历史发布/可得性或研究资格，也不补齐证据缺口。

## M4 合成演示 CLI（离线、固定样例）

不写任何调用代码即可跑通五个已冻结合成阶段；命令固定使用一个明确虚构的 24 行日频示例：

```powershell
python -m ashare_research.synthetic_demo
python -m ashare_research.synthetic_demo --json
```

默认输出可读摘要：模式、行数与观测数、已完成阶段、`pipeline_digest`，以及执行器逐字的
`SYNTHETIC_TEST_ONLY` 解释边界。`--json` 原样写出既有 `serialize_pipeline_result` 的规范
序列化字节（排序键、紧凑 JSON、恰一个结尾换行）。

命令只有 `--json` 与帮助参数：没有输入、配置、种子、provider、数据库、输出路径或注册表
参数；模块自身不访问文件、网络、数据库或环境，固定配置显式关闭 bootstrap 且稳健性注册表
为空，也不绑定任何 M4-B 注册记录。解析错误退出码 2；已知校验失败只输出净化后的错误码
（退出码 1），不输出结果、原始值或 traceback。合成演示只是软件演示：跑通合成链不等于真实
研究授权，也不构成统计显著、经济有效、可交易或任何 A 股机制结论。

## M2 离线研究包（固定来源汇编、离线、无新计算）

把中石油（`601857.SH`）已冻结的九个基线报告汇编为一份可读 Markdown 与规范 JSON，
并可导出带源附件与校验清单的离线包：

```powershell
python -m ashare_research.tools.value_research_bundle
python -m ashare_research.tools.value_research_bundle --json
python -m ashare_research.tools.value_research_bundle --output tmp/m2-research-bundle
python -m ashare_research.tools.value_research_bundle --verify tmp/m2-research-bundle
```

- 默认输出中文 Markdown（来源日期、价值画像、PIT 财务状态时间线、TTM/MRQ 估值分位、
  非生产影子维度、PE 暂缓决定、风险观测、全部 18 条缺口、非生产边界，附原报告叙事）；
  `--json` 输出规范 JSON。
- `--output NEW_DIR` 只写入**新目录**：`report.md`、`report.json`、
  `sources/reports/<九个原始报告>`、`manifest.json`。源附件是原报告的逐字字节副本；
  已存在的路径（含符号链接）一律拒绝，导出前先完成全部读取与渲染。
- `--verify DIR` 只依据包内保留的源附件重新渲染并逐字节比对报告与清单，
  不信任清单里记录的哈希，也不依赖当前仓库中的报告文件。
- 这是**混合日期的历史汇编**：原始日期与十进制原样保留，日期字段分别按来源列示，
  既不是统一 as-of 时点的 PIT 查询，也不是研究刷新。没有总体评分、排名、资格判定或建议，
  不产生任何新指标；源哈希只证明附件完整性。
- 已知失败（缺来源、哈希不符、输出已存在、包被篡改等）退出码 1，只向 stderr 输出净化后的
  错误码，stdout 为空；本工具不联网、不读数据库、不读凭据、不修改任何既有报告。

## M2 指定时点财务事实浏览器（离线、固定快照）

按指定 as-of 日期选择**最新可得**财务事实，并可对比两个时点的版本/重述差异：

```powershell
python -m ashare_research.tools.pit_fact_explorer --as-of 2024-03-31
python -m ashare_research.tools.pit_fact_explorer --as-of 2024-03-31 --json
python -m ashare_research.tools.pit_fact_explorer --as-of 2024-03-31 --compare-with 2025-03-31 `
  --concept net_profit_attributable_to_parent --period-end 2023-12-31
python -m ashare_research.tools.pit_fact_explorer --as-of 2024-03-31 --compare-with 2025-03-31 `
  --concept net_profit_attributable_to_parent --period-end 2023-12-31 --output tmp/m2-pit-fact-comparison
```

- 输入只有仓库内已提交的固定规范快照 `tests/fixtures/stage2g/canonical_fact_snapshot_v1`
  （33 条事实、5 个概念、`601857.SH`，四个来源文件 SHA256 固定 pin）。不读调用方数据库、
  不联网、不获取新数据、不修改默认数据库或任何既有文件。
- `--as-of` 必填（`YYYY-MM-DD`）；`--compare-with` 可选且不得早于 `--as-of`；`--concept`
  可重复（未知概念一律拒绝）；`--period-end` 与 `--scope consolidated|parent_company` 可选。
  默认输出中文 Markdown，`--json` 输出规范 JSON，二者与 `--output NEW_DIR` 互斥。
- 选择完全走公开 PIT 门禁（`validate_snapshot` / `build_temp_fact_db` 在工具自有的临时
  目录中重建临时 DuckDB，清理前先关闭连接，再用 `FactRepository` /
  `AsOfQuery.get_latest_available`）：`available_at` 非空且 `<= as-of`、verification 通过、
  `eligible_for_metrics`，未来事实永不进入选择，也不会静默默认为今天。
- 金额一律按选中的 `fact_id` 从快照还原原始 `value_decimal` 精确十进制字符串；比较使用
  `Decimal` 数值相等，不经过引擎 DOUBLE，也不做任何浮点财务算术。对比状态区分
  新增/移除/数值变更（重述）/版本变更（值未变）/未变，并给出前后 `fact_id`。
- 报告如实给出请求、四个来源摘要、PIT 选择表、两时点对比表与来源追踪（原始单位/日期、
  上下文、lineage、父事实 ID）。输出稳定、不含运行时刻或当前日期。
- `--output NEW_DIR` 只写入**新目录**：`report.md`、`report.json`、`manifest.json`。
  全部读取、校验与渲染都在创建输出根之前完成；输出根用排他 `mkdir` 认领，已存在路径
  （含符号链接与普通文件）一律拒绝且保持原样。`manifest.json` 记录渲染文件哈希、
  四个来源摘要与被选中的请求/事实 ID。
- 已知失败（来源缺失/摘要不符、快照契约不符、非法日期、非法口径、未知概念、
  `--compare-with` 早于 `--as-of`、输出已存在、写入失败）退出码 **2**，只向 stderr 输出
  净化后的稳定错误码，stdout 为空；不产生新指标、评分、排名、资格或研究阶段结论。

### 来源与证据限制

- 快照只保留 33 条已对账事实及其直接 lineage；lineage 里的 66 个 `parent_fact_ids`
  **全部不在快照内**，公司/交易所原始披露证据无法在本工具内复原。工具对每个父事实显式
  标记"未解决"，不伪造完整原始证据，也不声称重新证明了原始可得性。
- 两个查询时点分别追踪各自选中事实的父事实；父事实只有在快照内保留、且在对应时点
  通过公开 PIT 门禁时才算解决，未来父事实保持未解决。JSON 同时保留 `selections`
  和 `compare_selections`，以及原始事实级来源字段、缺失的 URL/摘要/页码/表名。
- 上下文是期间级元数据，其中披露日期和文档不一定对应当前重述版本，不能替代事实级来源。
- `available_at` 取自固定快照本身，工具只按门禁使用它、不重新验证该日期；`created_at` /
  `recorded_at` 是本地存储元数据（本快照为 2026 年），**不是可得性证据**。
- 快照是规范导出/读取模型（"canonical export/read model; not a new source of truth"），
  不是新的真值来源；本工具不做数据获取、来源准入或默认数据库读写。
- 导出清单供核对文件字节与来源摘要；未附原始披露文件。晚期磁盘写入失败可能留下
  工具自己创建的部分目录；工具会报错并保留现场，不删除用户目录。
- 该快照只有 `601857.SH`、5 个概念，且只有 `consolidated` 口径；`--scope parent_company`
  会如实返回空结果，不回退到合并口径或更晚时点。

## M2 既有指标 PIT 重放（离线、内存、不发布）

用仓库中**既有已批准**的七个指标定义与既有内存引擎，在两个查询时点各自独立通过公开 PIT
门禁的规范事实上重放年度指标，给出输入角色追踪与两时点对比：

```powershell
python -m ashare_research.tools.pit_metric_replay --as-of 2024-03-31
python -m ashare_research.tools.pit_metric_replay --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --json
python -m ashare_research.tools.pit_metric_replay --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-pit-metric-replay
python -m pytest -q tests/test_pit_metric_replay.py
```

- 七个指标全部来自既有注册表，没有新公式：`MetricDefinitionRegistry` 4 个
  （`revenue_yoy`、`net_profit_attributable_to_parent_yoy`、`operating_cash_flow_yoy`、
  `operating_cash_flow_to_attributable_net_profit`）、`CashFlowMetricDefinitionRegistry` 2 个
  （`cash_based_free_cash_flow_proxy`、`cash_paid_for_fixed_assets_to_revenue`）、
  `CapitalReturnMetricDefinitionRegistry` 1 个
  （`return_on_average_equity_attributable_to_parent`）；`metric_id` 是既有引擎身份，
  不是新版本准入。
- `--as-of` 必填；`--compare-with` 可选且不得早于 `--as-of`；`--year 2021..2025` 与
  `--metric`（仅上述七个）可重复；`--scope consolidated|parent_company`；默认 Markdown，
  `--json` 与 `--output NEW_DIR` 互斥。默认年度 2021–2025、默认全部七个指标，结果确定性排序，
  不含运行时刻或隐式今天。
- 事实选择完全走公开 PIT 门禁（`available_at` 非空且 `<= as-of`、verification 通过、
  `eligible_for_metrics`），金额按选中 `fact_id` 还原 `value_decimal` 为 `Decimal`；
  指标只在内存中经既有 `MetricEngine.compute` 重放，不写 MetricRepository 或任何数据库，
  不联网、不读调用方数据库、不修改既有文件。
- **缺失保持缺失**：缺失角色按角色/概念/年度逐条给出 `missing_roles` 与
  `missing_fiscal_years`；2021 年三个同比指标的 FY2020 期初缺失记为
  `insufficient_history`，其 `input_available_at_bound` 仍是已知输入可得性上界
  `2022-04-01`；最早可得日 `2022-04-01` 之前没有任何输入时上界为 `null`；
  `--scope parent_company` 如实返回空选择与 missing_input，不回退到合并口径或更晚时点；
  未来事实永不进入选择。
- **这不是发布**：`created_at` 只收到固定标记 `offline-replay-not-a-publication-time`；
  `revision_review_status` 恒为 `offline_replay_unreviewed`；`result_version=1` 表示本读取模型，
  不是已存储历史指标版本；`input_available_at_bound` 是输入可得性上界，**不是**指标发布时间。
  七个指标都不评分、不排名、不给建议；现金口径自由现金流代理只是**现金代理**，
  ROE 沿用既有年度平均归母权益约定，二者都不是估值、TTM 或 ROIC 结论。
- **保留快照缺口**：输入只有 `tests/fixtures/stage2g/canonical_fact_snapshot_v1`
  （33 条事实、5 个概念、`601857.SH`、只有 `consolidated` 口径）；lineage 的 66 个
  `parent_fact_ids` 全部不在快照内，公司/交易所原始披露证据无法复原；`available_at` 取自
  固定快照本身，不重新证明原始可得性；`created_at`/`recorded_at` 是本地存储元数据，
  不是可得性证据；期间上下文日期不一定对应当前重述版本。
- `--output NEW_DIR` 只写入**新目录**的 `report.md`、`report.json`、`manifest.json`
  （清单含渲染文件哈希、四个来源摘要、选择集与对比状态）。工具在自有的临时目录内重建临时
  DuckDB 并在清理前关闭连接，不写默认数据库；读取、校验与渲染全部完成后才用排他 `mkdir`
  认领输出根，已存在的文件/目录/符号链接一律拒绝且保持原样。晚期磁盘写入失败可能留下工具
  自己创建的部分目录：工具报错并保留现场，不删除用户目录。
- 已知失败（来源缺失/摘要不符、快照契约不符、非法日期/对比顺序/年度/指标/口径、输出已存在、
  写入失败）退出码 **2**，只向 stderr 输出净化后的稳定错误码，stdout 为空。

## 数据获取与离线复现

步骤 1–5 写入本地数据，其中 2–5 访问外部数据源。步骤 6 查询已有本地数据。
步骤 7 的胶囊构建/比较和步骤 8 的 test-capsule 模式使用固定测试输入，不需要默认数据库或外部行情。
真实验收命令另需显式的数据库、行情或 PDF 缓存；缺失时失败，不回退到合成数据。

### 1. 初始化

```powershell
ashare-research init-db
```

### 2. 获取股票基础信息

```powershell
ashare-research fetch-stock-basic --provider baostock
```

### 3. 获取交易日历

```powershell
ashare-research fetch-calendar --start 2026-01-01 --end 2026-07-27
```

### 4. 获取个股日线

```powershell
ashare-research fetch-stock-daily 601857.SH --start 2026-05-01 --end 2026-07-27 --provider baostock --adjustment none -v
```

### 5. 获取指数日线

```powershell
ashare-research fetch-index-daily 000001 --start 2026-05-01 --end 2026-07-27 --provider akshare
```

### 6. 查看已保存数据

```powershell
ashare-research inspect stock-daily 601857.SH --show-data
```

### 7. Stage 2G.2 可复现测试

普通测试不依赖 `output/`、`data/research.duckdb`、外部行情缓存或网络：

```powershell
python -m ashare_research.tools.stage2g_reproducibility verify-contracts
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output tmp/stage2g2-local/capsule-a
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output tmp/stage2g2-local/capsule-b
python -m ashare_research.tools.stage2g_reproducibility compare-capsules --left tmp/stage2g2-local/capsule-a --right tmp/stage2g2-local/capsule-b
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir tmp/stage2g2-local/capsule-a --output tmp/stage2g2-local/run-a --run-id stage2g2_local_ab
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir tmp/stage2g2-local/capsule-b --output tmp/stage2g2-local/run-b --run-id stage2g2_local_ab
python -m ashare_research.tools.stage2g_reproducibility compare-runs --left tmp/stage2g2-local/run-a/stage2g2_local_ab --right tmp/stage2g2-local/run-b/stage2g2_local_ab
pytest -q
ruff check src/ tests/
```

### 8. Stage 2H 风险否决证据切片

正式评估只读取提交的证据/事件/有界搜索台账，默认离线、PIT-aware、不可写默认数据库；官方 PDF 获取必须显式指定外部内容寻址缓存：

```powershell
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice verify-contracts
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice acquisition-preflight `
  --official-cache-root <official-pdf-cache> `
  --output tmp/stage2h-preflight.json
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice run-offline-formal `
  --output tmp/stage2h-run `
  --run-id petrochina_stage2h `
  --official-cache-root <official-pdf-cache>
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice run-test-capsule `
  --output tmp/stage2h-test `
  --run-id stage2h_test_capsule
pytest -q tests/test_stage2h_risk_veto.py
pytest -q tests/test_stage2h1r_historical_completeness.py
```

Stage 2H.1R 的当前风险状态唯一 canonical 路径是
`reports/petrochina_value_profile.json:current_risk_veto_profile`，固定输出
8 个 `risk_evaluation_slot_v1`。`observations` 可以少于 8，但 slot 不会消失；
没有 PIT-visible input 的 slot 保持 `missing_evidence`。完整风险档案见
[canonical risk-veto profile](reports/petrochina_risk_veto_profile_2021_2026.md)。
旧的 `governance_risk`、`audit_risk` 和 `related_party_risk` 只在
`legacy_risk_veto_checks` 中保留，且 `current=false`、`do_not_use_for_current_profile=true`；
消费者不得把它们当作当前结论。

Stage 2H 的历史范围停在风险证据状态与否决资格；该阶段记录不代表当前整个主线的进度。

测试胶囊中的 Fact 是由 canonical Fact 仓库导出的有界 read model；行情是固定算法生成的
`synthetic_test_only` CSV。它们只用于显式 `test_capsule` 模式，不是 PetroChina 真实输入，
不会成为真实报告的 fallback。

真实本地验收必须显式提供 canonical DB 与外部行情缓存根目录：

```powershell
python -m ashare_research.tools.stage2g_reproducibility verify-real-inputs `
  --fact-db <canonical-db> `
  --market-cache-root <external-market-cache> `
  --output <preflight.json>
python -m ashare_research.tools.stage2g_reproducibility run-real `
  --fact-db <canonical-db> `
  --market-cache-root <external-market-cache> `
  --output <run-root> --run-id stage2g2_real_local
```

真实 provider 数据与 PDF 不随仓库重新分发；缺失或 hash 不匹配时失败并报告
`missing_external_research_input`，不会回退到本地小 Parquet 或测试胶囊。详见
[Stage 2G.2 reproduction guide](docs/stage2g_reproduction_guide.md)。

---

## 数据目录

```text
data/
├── research.duckdb          # DuckDB 元数据
├── raw/                     # 原始下载数据（不提交 Git）
│   ├── baostock/
│   └── akshare/
└── parquet/                 # 标准化后数据（不提交 Git）
    ├── stock_daily/
    ├── index_daily/
    ├── stock_basic/
    └── trade_calendar/
```

---

## 数据源

| 数据源 | 用途 | 状态 |
|--------|------|------|
| [Baostock](http://baostock.com) | 股票基本信息、交易日历、个股日线 | ✅ 已接入 |
| [AKShare](https://akshare.akfamily.xyz) | 指数日线、备用个股数据 | ✅ 已接入 |

### 数据源可能失效的风险

Baostock 和 AKShare 均为免费公开接口，可能因上游变更而暂时或永久不可用。
本项目设计为**数据源可替换**，通过统一接口适配不同的数据提供方。

---

## 数据字段与单位

### 个股日线 (stock_daily)

| 字段 | 说明 | 单位 |
|------|------|------|
| symbol | 股票代码 | `600000.SH` 格式 |
| trade_date | 交易日 | `YYYY-MM-DD` |
| open | 开盘价 | 元（人民币） |
| high | 最高价 | 元 |
| low | 最低价 | 元 |
| close | 收盘价 | 元 |
| pre_close | 前收盘价 | 元 |
| volume | 成交量 | 股 |
| amount | 成交额 | 元（人民币） |
| turnover_rate | 换手率 | % |
| is_trading | 是否交易 | 布尔值 |
| adjustment | 复权方式 | `none`/`qfq`/`hfq` |
| source | 数据来源 | `baostock`/`akshare` |
| fetched_at | 抓取时间 | ISO datetime |

### 指数日线 (index_daily)

| 字段 | 说明 | 单位 |
|------|------|------|
| symbol | 指数代码 | 如 `000001`（上证指数） |
| trade_date | 交易日 | `YYYY-MM-DD` |
| open/high/low/close | OHLC | 点位 |
| volume | 成交量 | 手 |
| amount | 成交额 | 元（人民币） |

### 股票代码格式

- **内部统一格式**：`600000.SH` / `000001.SZ`
- **Baostock 格式**：`sh.600000` / `sz.000001`
- **纯数字推断**：6/9 开头 → SH，0/3/2 开头 → SZ

---

## 复权说明

- `none`：不复权（默认），价格与历史实际成交价一致
- `qfq`：前复权，以最新价为基准向前调整历史价格
- `hfq`：后复权，以上市首日为基准向后调整价格

默认保存不复权数据。需要复权数据时，请在参数中明确指定 `--adjustment qfq`。

---

## 质量检查

每次数据抓取自动运行以下检查：

- 必需字段完整性
- 日期可解析性
- 主键唯一性（symbol + trade_date + adjustment）
- OHLC 逻辑一致性（high >= open, high >= close, low <= open, low <= close）
- 价格和成交量非负
- 日期排序
- 数据来源不为空

检查结果记录在 DuckDB `data_quality_results` 表中。

---

## 运行测试

```powershell
# 全部测试（Mock，不依赖网络）
pytest -q

# 带覆盖率
pytest --cov=ashare_research --cov-report=term-missing

# 代码检查
ruff check src/ tests/
```

---

## 项目结构

以下模块目录位于 `src/ashare_research/`：

| 目录 | 职责 |
| --- | --- |
| `providers`, `services`, `storage`, `quality` | 数据获取、编排、存储和质量检查 |
| `facts`, `validation`, `reconciliation`, `lineage` | PIT 事实、版本校验、协调和溯源 |
| `metrics`, `pit_valuation`, `risk_veto`, `scoring` | 指标、估值时间线、风险证据与受限评分实验 |
| `mechanism` | 已冻结 M3 方法和 M4-A.1 合同编译 |
| `tools` | 阶段命令行工具；运行前查阅对应合同 |

仓库根目录的 `tests`、`reports`、`acceptance` 保存测试和研究验收证据；
`agent/goals`、`agent/record` 保存任务契约与记录；`docs` 保存方法说明、复现指南与阶段历史。
当前能力以本页为准；历史记录不自动授权新阶段。

## 路线图

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| Milestone 1: 免费数据底座 | 数据获取与存储 | 已实现 |
| Milestone 2: 价值评估 MVP | 中石油 PIT 切片 | CONDITIONALLY CLOSED；评分附加项条件关闭 |
| Milestone 3: 机制验证 MVP | 日频机制验证 | CONDITIONALLY CLOSED；daily mechanism not established；holdout primary inconclusive |
| Milestone 4: Generic Mechanism Research Engine + Theory / Hypothesis Registry | 通用机制研究契约与理论/假设注册 | IN PROGRESS; Stage4P COMPLETE; M4-A.1 CANONICAL ON MAIN; M4-A.2 DESIGN ON MAIN; M4-A.2I COMPILE-ONLY IMPLEMENTED; M4-A.2D SYNTHETIC DATASET ADAPTER IMPLEMENTED; M4-A.2M ANALYSIS MATRIX IMPLEMENTED; M4-A.2E BOUNDED EXECUTION IMPLEMENTED ON SYNTHETIC FIXTURES ONLY; M4-A.2P SYNTHETIC END-TO-END ORCHESTRATION IMPLEMENTED AS A SYNTHETIC-ONLY IN-MEMORY COMPOSED ENTRY; real-data executor NOT STARTED; M4-B DESIGN FROZEN; M4-B MINIMUM METADATA REGISTRY IMPLEMENTED FOR SYNTHETIC/SCHEMA VALIDATION ONLY; real registry dataset NOT AUTHORIZED; real-research M4-B NOT STARTED; real hypothesis execution NOT AUTHORIZED |
| Milestone 5: 分钟级研究 | 按需验证 | 未开始、未授权 |
| Milestone 6: 本地 Web 界面 | 研究工作台 | 未开始、未授权 |

## 许可

A software license has not yet been selected. The repository is currently public for review and research discussion; no additional reuse rights are granted unless a license is added later.
