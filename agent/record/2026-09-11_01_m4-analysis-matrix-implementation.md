# 工作记录：M4 synthetic analysis matrix 实现（第 1 轮交付）

- 状态：`completed`（DeepSeek Harness 完成实现与首轮验证；Codex 已独立审查并在非 Harness
  ACL 环境复跑得到 `80 passed`、`270 passed` 与 ruff 通过，随后创建限定范围的本地提交）
- 日期：2026-09-11
- 工作树：`D:/量化分析-m4-matrix-implementation`
- 分支：`codex/m4-analysis-matrix-implementation`
- 起始 HEAD：`125247d7401a3563c73a1b7ef31fa9a9587699d6`（Goal 契约提交；其父为设计收尾
  `8a3b6a5d83d13aa9db71a0191f18b60af195b628`）；最终实现提交由 Codex 在独立审查后创建，
  其精确哈希见最终证据包与 `git log`
- Goal 契约：[agent/goals/2026-09-11_m4_analysis_matrix_implementation.md](../goals/2026-09-11_m4_analysis_matrix_implementation.md)（`125247d` 已提交，未修改）
- 规范输入：[docs/m4_analysis_matrix_design_v1.md](../../docs/m4_analysis_matrix_design_v1.md)、
  [docs/m4_analysis_matrix_acceptance_cases_v1.md](../../docs/m4_analysis_matrix_acceptance_cases_v1.md)（均未修改）
- 验收文档：[acceptance/2026-09-11_m4_analysis_matrix_implementation.md](../../acceptance/2026-09-11_m4_analysis_matrix_implementation.md)
- 实现交付：`src/ashare_research/mechanism/planning/matrix.py`（新增，520 行）、
  `tests/test_m4_analysis_matrix.py`（新增，1213 行）

## 1. 任务目标

按已 PASS 的设计实现 M4 synthetic analysis matrix 的**纯确定性准备模块**：从既有
`DatasetPreparationV1`、冻结合同、确定性计划与原始绑定输入，产出经校验的不可变矩阵；
实现四个公开入口、规范序列化与自摘要、稳定失败语义；先复现负例再实现正例；跑完 Goal
指定的全部精确命令并逐项记录退出码；最后创建**只含四个允许路径**的本地提交，不推送、
不合并、不执行统计。最终 verdict 由 Codex 独立审查给出。

## 2. 范围与非目标

**范围内**：Goal 允许的五个路径中的实现与记录四类——
`src/ashare_research/mechanism/planning/matrix.py`、`tests/test_m4_analysis_matrix.py`、
本工作记录、验收文档；以及读取既有真实源码/测试、只读探针复算、执行 Goal 精确命令、
创建本地提交。

**非目标（明确不做）**：不修改 Goal 契约、两份设计文档、任何 `__init__.py`、既有源码、既有测试、
README、依赖、工作流、历史文档、schema、冻结产物或保护哈希；不连接数据库、不读数据库内容、
不访问 provider 或真实行情、不执行回归/rank/bootstrap/robustness/evidence/holdout；不进入 M4-B；
不递归委派；不推送、不开 PR、不合并 PR #11；不动其它工作树、stash、ignored 运行数据。

## 3. 接手时基线核查（只读，实际执行）

```text
git status --short --branch         -> ## codex/m4-analysis-matrix-implementation（干净，无未跟踪项）
git rev-parse HEAD                  -> 125247d7401a3563c73a1b7ef31fa9a9587699d6（= Goal 契约提交，无漂移）
git log --oneline -3                -> 125247d docs: define M4 matrix implementation goal
                                       8a3b6a5 docs: define M4 synthetic analysis matrix
                                       b0c8faf docs: record synthetic adapter PR delivery scope and validation
git rev-parse origin/main           -> bab24f981fef9336b84280544ce709702b9df116（= 契约声明）
git rev-parse refs/stash            -> cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f（= 保护值）
git stash list                      -> 仅原有 stash@{0}（"…protect pre-existing Stage 1B.4 record edit…"）
git worktree list --porcelain       -> 13 个工作树；原 M2 worktree HEAD
                                       3679b1bac7a1634c6452784a4d8f6d139966f222（= 保护值）
Get-FileHash -Algorithm SHA256      -> 4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6
  'D:/量化分析/data/research.duckdb'   （= 保护值；仅哈希，未连接、未读取内容）
git ls-remote origin                -> 退出码 128，无法连接 github.com:443（网络不可达）
python                              -> D:/量化分析-m4a2i/.venv/Scripts/python.exe，Python 3.13.9
ruff                                -> 0.13.2
```

结论：分支、HEAD、Goal 提交、保护 stash/DB 哈希、13 个工作树均与契约一致，无基线漂移。
远端 git ref 无法刷新（见 §7）。

## 4. 实际执行的工作

### 4.1 只读读取的文件

- `D:/量化分析/AGENTS.md`；`agent/goals/2026-09-11_m4_analysis_matrix_implementation.md`
- `docs/m4_analysis_matrix_design_v1.md`（1084 行，全文含 §6.5 冻结载荷与 §7 全部实测值）
- `docs/m4_analysis_matrix_acceptance_cases_v1.md`（641 行，AC-01…AC-15 + AC-08b）
- `src/ashare_research/mechanism/datasets/synthetic.py`（适配器真实实现：`_shape`/`_dec`/
  `_coverage_ge`/`materialize_analysis_dataset`/`serialize_dataset`/`validate_dataset`）
- `src/ashare_research/mechanism/datasets/__init__.py`（既有导出面，不改）
- `src/ashare_research/mechanism/planning/compiler.py`（`_terms`、`validate_analysis_plan`）
- `src/ashare_research/mechanism/planning/__init__.py`（既有导出面，不改）
- `src/ashare_research/mechanism/model_digest.py`（`canonical_digest` 真实实现）
- `src/ashare_research/mechanism/hypothesis_config.py`（`canonical_decimal` 语义）
- `tests/test_m4_stage4a1_typed_contract.py`（`_document()`/`_compiled()` fixture）
- `tests/test_m4_synthetic_dataset_adapter.py`（`_inputs`/`_bound`/`_quality`/`_refresh`/`_rehash_output`）
- `tests/conftest.py`、`pyproject.toml`（pytest/ruff 配置）
- `agent/record/README.md`、`agent/record/2026-09-10_01_m4-analysis-matrix-design.md`、
  `acceptance/2026-09-10_m4_analysis_matrix_design.md`（格式与历史证据参照）

### 4.2 实现前的负例复现（未实现状态，真实执行）

按验收场景文档 §7 的要求，**先确认门禁真的拒绝**。全部通过标准输入管道只读执行，
未在工作树写入任何探针文件：

```text
import ashare_research.mechanism.planning.matrix
    -> ModuleNotFoundError: No module named 'ashare_research.mechanism.planning.matrix'
       （实现前矩阵 API 确实不存在）

AC-08 指示列全部取反 + 重算 dataset_digest 的自洽篡改体：
    tampered.dataset_digest = 721584843f0f10448b0e1aecc28cc30a52018844be4c5852923c0acdab57b79f
    serialize_dataset(tampered)                        -> 接受（内部自洽，无异常）
    validate_dataset(tampered, contract, plan, data)   -> AdapterError IDENTITY_CONFLICT
    （确认：只跑 serializer 会放行，只有四参数入口能拒绝；矩阵入口必须调用它）

AC-09 原始输入重哈希篡改（FACTOR@2020-01-03 改 "-0.05" 并重算证据与 input_digest）：
    rehashed.input_digest   = e877c147b58b53ee3283e87bcce49592470643c161e7a675af1e06a51943b464
    rehashed.dataset_digest = 2788e8ec06d370a3020b99fecbdcb4d7cb30d7568dbea33d0f22a63a063a7aea
    validate_dataset(rehashed, contract, plan, 原始 data) -> AdapterError IDENTITY_CONFLICT

AC-10 嵌套合同修改（robustness trim "0.0100"→"0.0200"）：
    nested.contract_digest = f4c193cbbc9a32e9bc7d17bf9ba494c7702fc46acd3c723102d025e8084eed9f
    nested.plan_digest     = 8833ed844a7f50d9665945b7d18c07d2e1d72bde97b13cf8aeefcad24e2cc677
    materialize_analysis_dataset(nested, base_plan, base_inputs) -> AdapterError CONTRACT_PLAN_MISMATCH
    validate_dataset(base_prep, other_contract, base_plan, data) -> AdapterError CONTRACT_PLAN_MISMATCH

AC-14 上游码（实现前实测，供实现后对比）：
    mode=REAL -> UNSUPPORTED_MODE ; input_digest 全 0 -> INPUT_DIGEST_MISMATCH ;
    重复 observation -> DUPLICATE_OBSERVATION ; evidence_digest 全 0 -> EVIDENCE_DIGEST_MISMATCH ;
    域外日期 2023-01-03 -> OUT_OF_DOMAIN ; 另一合同 + 基础计划 -> CONTRACT_PLAN_MISMATCH

AC-07 拒绝态（gate/missingness 组合）：0.99/FAIL_CLOSED、0.66/FAIL_CLOSED、
    0.67/RETAIN_IN_DENOMINATOR 三种均 status=REJECTED_QUALITY、n/N=2/3、complete_rows=()；
    且 validate_dataset(rejected, ...) 本身**不抛错**（质量拒绝 ≠ 来源不一致）

AC-13 规范十进制：接受 "0"/"0.01"/"1"/"-0.01"；拒绝 "-0"/"0.0"/"0.0100"/"1E-2"（INVALID_VALUE）

基础 fixture 独立重算（不调用任何矩阵实现，按设计 §3/§6.5 规则自行投影）：
    contract_digest = ee450d1f… ; plan_digest = 45a24617… ; input_digest = c1f6c3d7…
    domain_digest   = b78882e4… ; dataset_digest = c3410933…
    independent matrix_digest          = a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
    independent serialize sha256       = 70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa
    （与设计 §7.2 实测值逐位相同 → 冻结载荷口径确认无误，之后才写实现）
```

### 4.3 实现（`src/ashare_research/mechanism/planning/matrix.py`）

- **常量与错误族**：`MATRIX_SCHEMA_VERSION="M4_DESIGN_MATRIX_V1"`、
  `MATRIX_BUILDER_VERSION="M4_DAILY_CONDITIONAL_DESIGN_MATRIX_V1"`；
  `MatrixError(ValueError)` 携带 `.code`，只承载矩阵投影层失败；上游 `AdapterError` 原样传播。
- **冻结类型**：`MatrixColumnV1`/`MatrixRowV1`/`MatrixQualityV1`/`MatrixPreparationV1`，
  全部 `frozen=True`、嵌套 `tuple`；`_shape` 递归做严格运行时类型检查（`type(x) is int` 拒绝
  `bool`、`type(x) is tuple` 拒绝 list），失败 → `INVALID_INPUT_STRUCTURE`。
- **公开入口四个**：`materialize_design_matrix(preparation, contract, plan, bound_inputs)`、
  `matrix_to_canonical_dict(matrix)`、`serialize_matrix(matrix)`、
  `validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)`；
  `_project_validated_matrix(preparation, plan)` 保持私有且不进入 `__all__`。
- **材料化顺序**：A1 `validate_dataset(...)`（上游错误原样抛出，含上游 `IDENTITY_CONFLICT`/
  `CONTRACT_PLAN_MISMATCH` 等）→ A2 共享投影管线：①运行时结构 ②计划结构/白名单/位置连续
  ③preparation 结构（`role_order` 非空且唯一、`coverage_denominator == len(audit_rows)`、
  audit cells 顺序、complete row 宽度）④`response_role`/`FACTOR` 位序与 §3.1 断言
  ⑤质量门（`status != READY_SYNTHETIC` 或 `complete_rows` 为空 → `DATASET_NOT_READY`，不投影）
  ⑥逐行逐格投影与校验 ⑦自摘要 + 全部不变量自检。
- **列顺序**只来自 `plan.design_plan.ordered_terms`（经 `plan_to_canonical_dict` 读取），
  断言序列 `INTERCEPT, FACTOR_CONTINUOUS, role_order 中 CONTROL_*, CONDITION_INDICATOR`；
  取值只按 `term_role` 分派：截距字面量 `"1"`、因子取 `role_order` 中 `FACTOR` 位、控制项取
  同名角色位、指示列取严格 `int` 0/1 格式化为 `"0"`/`"1"`；未知 `term_role` →
  `UNSUPPORTED_TERM_ROLE`；`source_role` 只做审计元数据（取自计划 `source_series_role`，
  进入载荷与摘要，不参与分派）。
- **质量继承**：`quality.status` 取 `preparation.status`，其余七字段逐字段复制
  `preparation.quality`（`reason_counts` 排序 tuple 化），不重判、不重算；`execution_authorized`
  与 `statistics_computed` 恒为 `False`。
- **身份与序列化**：`matrix_to_canonical_dict` 返回全新 dict/list（不含 `matrix_digest`）；
  `matrix_digest = canonical_digest(payload)`；`serialize_matrix` = 规范 JSON（`ensure_ascii=False,
  sort_keys=True, separators=(",", ":")`）在载荷上补 `matrix_digest` 后加恰好一个 `\n` 的 UTF-8 字节。
- **不变对象**：矩阵不提供任何修改路径；`matrix_to_canonical_dict` 的返回值为防御性副本。
- **`validate_design_matrix` 顺序**：V1 矩阵对象结构 + 自摘要（`INVALID_INPUT_STRUCTURE` /
  `MATRIX_DIGEST_MISMATCH`）→ V2 `validate_dataset` → V3 重投影 → V4 逐字节比较，不一致 →
  `MatrixError("IDENTITY_CONFLICT")`。

### 4.4 对设计的三处口径判定（实现前明确、供 Codex 复核）

设计文档在这三处存在需要读者判定的表述，本实现的取舍与依据如下（均为**收紧门禁**，
不改变任何已实测的摘要值）：

| # | 设计表述 | 本实现取舍 | 依据 |
| --- | --- | --- | --- |
| 1 | §6.3 写 "`payload` 是 `matrix_to_canonical_dict(matrix)` **删除** `matrix_digest` 自身后的字典"，暗示规范字典含 `matrix_digest`；§6.5 冻结字典清单**不含** `matrix_digest`，且约束 5 写 "`matrix_digest` 只出现在 `serialize_matrix` 的输出中" | `matrix_to_canonical_dict` **不含** `matrix_digest`；`serialize_matrix` 在其上补入后再序列化 | 采用 §6.5 冻结清单与约束 5 的字面口径；两种口径下 `matrix_digest`（对去掉自身的载荷计算）与 `serialize_matrix` 字节均与 §7.2 实测值逐位一致（已复算验证），因此该取舍不影响任何已冻结身份值 |
| 2 | §5.2 M1 写 "结构不满足 → `INVALID_INPUT_STRUCTURE`，自摘要与自身载荷不符 → `MATRIX_DIGEST_MISMATCH`"；§5.3 表把 "列序列不等第 3.1 节断言" 归到 `PLAN_TERM_ROLE_MISMATCH` | `validate_design_matrix` 的 **M1**（矩阵对象）对全部 1–9 条不变量违规一律抛 `INVALID_INPUT_STRUCTURE`，仅不变量 10 抛 `MATRIX_DIGEST_MISMATCH`；`PLAN_TERM_ROLE_MISMATCH` / `UNSUPPORTED_TERM_ROLE` 只出现在**投影管线**第 2/4 步（读计划时） | 以 §5.2 对 M1 的专门句子为准；两族都是 `MatrixError`，未放宽任何门禁（伪造矩阵仍被拒，只是错误码按阶段划分更明确） |
| 3 | §4.4 标题 "不变量（构造即校验，非法即拒绝）"，但 §5.2 管线第 7 步只要求自摘要自洽 | `_project_validated_matrix` 在算出自摘要后，对成品再跑一次完整不变量自检（第 7 步），确保材料化**永远不可能**返回违反 1–9 条不变量的对象 | 落实 §4.4 标题语义；自检只在真实合法输入上通过（80 个产品用例覆盖），不改变任何摘要值 |

补充说明（不作为偏差，只作事实澄清）：M1 只有 `matrix` 一个输入，因此不变量 7 中
"`coverage_denominator == len(preparation.audit_rows)`" 无法在 M1 内单独判定；该等式在投影
管线第 3 步对 `preparation` 检查，而 `validate_design_matrix` 的 V4 逐字节比较是最终门禁。

### 4.5 产品测试（`tests/test_m4_analysis_matrix.py`，33 个测试函数 / 80 个用例）

全部断言调用**真实实现**（矩阵模块 + 真实 adapter/compiler + 真实 `canonical_digest`），
fixture 复用既有 `_document()`/`_compiled()`/`_inputs()`/`_bound()`/`_quality()`/`_refresh()`；
**没有**复制生产投影算法做镜像 oracle（矩阵字面值全部来自
`materialize_design_matrix` 的返回值，而不是测试里另算一遍）。用例与设计 AC 的对应：

```text
AC-01 无 controls（3 列 + dataset/matrix digest）           test_no_control_plan_projects_exactly_three_columns
AC-02 三个 controls（6 列 + digest + 行值）                test_three_controls_grow_the_matrix_to_six_columns
AC-03 控制注册顺序反转（行值相同、身份不同）                 test_reversed_control_registration_order_changes_identity_not_rows
AC-04 阈值 "0" 四算子（plan_digest + 指示列 + matrix_digest） test_condition_operator_boundaries_are_exact_at_zero（4 参数）
AC-04 阈值 "-0.0100"→"-0.01" 四算子边界                    test_condition_threshold_is_normalized_without_float_tolerance（4 参数）
AC-05 五处缺行（分母不变、身份两两不同、行数=2）             test_missing_rows_keep_the_denominator_and_a_distinct_identity（5 参数）
AC-05 gate 0.66 通过 / 0.67 拒绝（精确有理数比较）           test_exact_gate_comparison_separates_0_66_from_0_67
AC-06 PIT_UNPROVEN / PIT_NOT_AVAILABLE                    test_pit_invisible_rows_are_reasoned_and_identity_bearing（2 参数）
AC-07 拒绝态四子案例（无对象、无部分矩阵）                  test_rejected_quality_never_returns_a_partial_matrix（4 参数）
AC-08 自洽篡改：serializer 接受 / 四参数拒绝                test_self_consistent_source_tamper_is_rejected_before_projection
AC-08b 伪造矩阵且未重算摘要（V1 MATRIX_DIGEST_MISMATCH）     test_forged_matrix_without_digest_refresh_fails_the_structure_stage
AC-08b 伪造矩阵且重算摘要（V4 IDENTITY_CONFLICT）            test_rehashed_forged_matrix_fails_the_reprojection_stage
AC-09 重哈希原始输入（上游 IDENTITY_CONFLICT）              test_rehashed_bound_inputs_are_rejected_by_the_source_gate
AC-10 嵌套合同修改（身份全变、单元格不变、混用报错）          test_nested_contract_change_moves_identity_but_not_cells
AC-11 观测逆序 + from_dict 往返                            test_observation_permutation_and_roundtrip_preserve_identity
AC-12 键序重排 + 换工作目录（同一身份）                     test_key_order_and_working_directory_do_not_change_identity
AC-13 规范十进制接受/拒绝、单元格不重格式化、布尔/越界指示值   4 个测试函数（14 参数）
AC-14 六个上游码原样传播 + 两族错误类型区分                  test_upstream_adapter_errors_propagate_unchanged（6 参数）
AC-14 顺序：来源错误先于质量门、V1 先于 V2、V2 先于 V4        test_validation_order_prefers_source_errors_over_the_quality_gate
AC-15 行列不变量/response_role/quality 继承/恒 False/不可变/   test_base_matrix_exact_shape_identity_and_serialized_bytes,
      防御性副本/19 种伪造结构/公开面/无统计依赖导入            test_canonical_payload_is_exactly_the_frozen_shape,
                                                          test_rows_columns_and_response_role_invariants,
                                                          test_quality_block_inherits_preparation_facts_without_rejudgement,
                                                          test_no_success_state_carries_execution_authorization,
                                                          test_matrix_is_frozen_and_the_canonical_dict_is_a_defensive_copy,
                                                          test_structurally_forged_matrices_are_rejected_as_invalid（19 参数）,
                                                          test_module_exposes_only_the_frozen_public_surface,
                                                          test_module_imports_no_statistics_database_or_provider_dependency
```

测试设计说明（诚实记录，避免误读）：

1. 本文件**不请求 `tmp_path`**：AC-12 的"跨目录身份"用 `monkeypatch.chdir` 切到
   `src/ashare_research` 复算，因此不受本 harness 的 `pytest-of-*` 沙箱拒绝影响。这是绕开
   受限设施，不是弱化断言（同一身份在真实换目录后仍被逐字节比较）。
2. AC-08b 需要构造"自洽的伪造矩阵"，测试用既有 idiom
   `replace(matrix, matrix_digest=canonical_digest(matrix_to_canonical_dict(matrix)))`
   （与既有适配器测试的 `_rehash_output` 同构）；所有**关于合法矩阵**的期望值都来自真实实现输出。
3. 矩阵层自身的"非规范十进制/严格 int"守卫通过 `serialize_matrix` / 伪造矩阵用例覆盖
   （公开入口）；上游侧篡改在 A1 就被 `AdapterError` 拦下，测试断言错误**类型**为
   `AdapterError`（不冒充矩阵错误）。
4. 未调用私有 `_project_validated_matrix` 作为任何验收入口（设计 §5.1/§8.1、验收场景 §0.2）。

### 4.6 实现后复算：设计第 7 节全部实测值逐项一致

在真实实现上重跑设计/验收文档中的全部期望值（只读探针，标准输入，不落盘）：

```text
基础：matrix_digest a3c40269… ✓ ; sha256(serialize_matrix) 70d9926e… ✓ ; 3 行 5 列字面值 ✓
AC-01 无 controls        : dataset e0e52d46… ✓ ; matrix f6df25c4… ✓ ; 3 列 ✓
AC-02 三 controls        : dataset 4c060328… ✓ ; matrix 13c18306… ✓ ; 6 列 ✓
AC-03 控制顺序反转        : input 4a863864… / dataset d4cddef0… / matrix 48f8a5b3… ✓ ; 行值与基础相同 ✓
AC-04 阈值 0 四算子       : plan 44207cc2/798955e8/f4030af6/f32b071c ✓ ;
                          matrix 6b7687e3/a862e23b/7b170345/7fbfcf8f ✓ ; 指示列 (1,1,0)/(1,1,1)/(0,0,0)/(0,0,1) ✓
AC-04 阈值 -0.01 四算子   : matrix 9d0c1f09/a3c40269/e228c48e/7a093d21 ✓ ; 指示列 (1,0,0)/(1,1,0)/(0,0,1)/(0,1,1) ✓
AC-05 五处缺行            : dataset aff29dfd/f85b4a37/e684cab7/38b5d6cc/8303d7e0 ✓ ;
                          matrix 09a1af5f/6e46e2a0/d995c832/3c3b4158/5734473d ✓ ; 均 2 行、分母 3 ✓
                          第二行确为 2020-01-06（被拒日期整行消失，不补行不补零）✓
AC-05 gate 0.67 拒绝      : dataset d1d287f7… ✓ ; 材料化抛 MatrixError DATASET_NOT_READY ✓
AC-06 PIT                 : dataset 5cc29781/09dea69c ✓ ; matrix 52298a8c/fce3d11e ✓ ; reasons 各 1 ✓
AC-07 7a/7b/7d 拒绝        : DATASET_NOT_READY、无对象、complete_rows=() ✓
AC-07 7c (value=null)     : dataset c75953b9… ✓ ; DATASET_NOT_READY ✓ ; reasons {"MISSING_VALUE":1} ✓
AC-10 嵌套合同            : dataset dfa395bb… ✓ ; matrix b75877ee… ✓ ; 行值与基础相同 ✓ ; 混用 CONTRACT_PLAN_MISMATCH ✓
AC-11 逆序/往返           : input_digest、matrix_digest、字节全部相等 ✓
AC-12 键序/换目录         : 键序重排后 canonical_digest 不变 ✓ ; 换 cwd 后 dataset/matrix 与字节相等 ✓ ;
                          序列化字节中无 "D:"/"worktree"/"hostname"，恰好一个结尾 \n，无 \u 转义 ✓
```

所有实测值均为真实输出；**未捏造任何摘要**。

## 5. 实际执行的验证命令与真实退出码

全部命令从 `D:/量化分析-m4-matrix-implementation` 执行，`PYTHONPATH` 按要求设为
`(Join-Path (Get-Location) 'src')`。命令 1、2 按 Goal 原样运行，未自造 `TEMP`/`--basetemp`，
未直调测试体，未用任何替代手段伪装通过。

| # | 命令 | 退出码 | 真实结果 |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q tests/test_m4_analysis_matrix.py` | **0** | 首次运行 `80 passed, 1 warning in 4.51s`；仅在文档编辑后重跑一次确认最终状态 `80 passed, 1 warning in 4.56s`（计数一致，代码文件未变）；唯一 warning 是 `.pytest_cache\v\cache\nodeids` 的 `PytestCacheWarning`（沙箱 `WinError 5`，与测试无关） |
| 2 | `python -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | **1** | 首次运行 `267 passed, 2 warnings, 3 errors in 14.86s`；最终状态重跑 `267 passed, 2 warnings, 3 errors in 7.47s`（计数一致）；3 个 error 全部是 setup 阶段 `tmp_path` 沙箱拒绝（见 §5.1），**不作为通过** |
| 3 | `python -m ruff check src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` | **0** | 无空白问题 |
| 5 | `git diff --cached --check` | **0** | 暂存区为空，无问题 |
| 6 | `git status --short --branch` | **0** | `## codex/m4-analysis-matrix-implementation` + 恰好两个未跟踪新文件（`matrix.py`、`test_m4_analysis_matrix.py`） |
| 7 | `git rev-parse HEAD origin/main refs/stash` | **0** | `125247d7…`（Goal 提交，未提交实现时）/ `bab24f98…` / `cb568efd…`（后两者等于契约与保护值） |
| 8 | `git worktree list --porcelain` | **0** | 13 个工作树条目，全部保留；原 M2 HEAD `3679b1ba…` 等于保护值 |
| 9 | `git stash list` | **0** | 仅原有 `stash@{0}` |
| 10 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `Failed to connect to github.com port 443` / `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`——远端 git ref **无法刷新**（见 §7） |
| 11 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **成功（cmdlet 不设置 `$LASTEXITCODE`）** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = 保护值（仅哈希，未连接数据库、未读内容） |
| 12 | `gh pr view 11 --json number,state,headRefOid,mergeable,url` | **0** | `{"state":"OPEN","headRefOid":"b0c8fafb…","mergeable":"MERGEABLE","number":11}` ——实时刷新，仍开放未合并 |
| 13 | `gh pr checks 11` | **0** | **42 条 check，全部 `pass`**（与契约声明的 42 成功一致，无新失败、无回归） |
| 14 | `git add <四个允许路径>`（Goal 要求的提交步骤） | **128** | `fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation/index.lock': Permission denied`——沙箱拒绝写入父仓库 `.git`，见 §6 |
| 15 | `git commit -m "feat: materialize immutable M4 design matrices from validated plans"` | **128** | 同一 `index.lock` 拒绝；未创建提交，HEAD 仍为 `125247d7…`，四个文件保持未跟踪 |

补充（开发过程与基线证据，非 Goal 命令）：命令 1 之前在同一环境跑过基线回归
`187 passed, 2 warnings, 3 errors in 2.87s`、退出码 1（当时工作树**尚未做任何修改**）；
开发中另跑过 `ruff`（0）与带 `-p no:cacheprovider` 的 pytest（0）。这些不作为 Goal 结论，
只用于归因。

### 5.1 命令 2 的真实结果与归因（保留真实失败证据，不粉饰）

```text
267 passed, 2 warnings, 3 errors in 14.86s      exit code 1
ERROR tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance
ERROR tests/test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence
ERROR tests/test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags

单测复现（-p no:cacheprovider）：
E  PermissionError: [WinError 5] 拒绝访问:
   'C:\Users\111\AppData\Local\Temp\dsh-bjpYza\pytest-of-dlam12138'
   at _pytest/pathlib.py:175 find_prefixed -> os.scandir(root)      （setup 阶段，测试体未执行）
```

归因证据（不是自我宣告）：

1. 同一命令在**本次任何修改之前**的基线上就是 `187 passed + 3 errors`、退出码 1，
   即 3 个 error 早于本次实现存在（187 + 新增 80 = 267，差额完全由新增用例解释）。
2. 3 个 error 全部发生在 pytest **setup** 阶段，位于 pytest 自身的 `tmp_path` 设施
   （`find_prefixed`/`os.scandir`），与矩阵实现无调用关系；本会话 `TEMP`/`TMP` 被指向
   `C:\Users\111\AppData\Local\Temp\dsh-bjpYza`（harness 沙箱临时区），其下
   `pytest-of-*` 被拒绝访问。
3. 未做任何"自造 TEMP/`--basetemp`"尝试，也未直调这 3 个测试体冒充通过；本轮新增测试
   不请求 `tmp_path`，因此新增部分在本 harness 内可完整运行（80/80 通过）。
4. 最终判定属 Codex；本记录只报告真实退出码与原始错误，不声称套件通过。

### 5.2 交付文件

```text
src/ashare_research/mechanism/planning/matrix.py   新增 520 行（四个公开入口 + 私有投影 + 冻结类型）
tests/test_m4_analysis_matrix.py                   新增 1213 行（33 个测试函数 / 80 个用例）
agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md   本文件
acceptance/2026-09-11_m4_analysis_matrix_implementation.md        验收文档
```

未修改任何既有文件（`git status --short` 只有上述两个源码/测试新文件为未跟踪；
`__init__.py`、设计文档、既有测试、README、依赖、工作流均未触碰）。

由于本地提交被沙箱阻塞（§6），这里给出两个**代码交付文件**的 SHA256，便于 Codex 独立核对
"待提交内容"与本次验证的运行对象完全一致（两份 Markdown 会随后续修复再变，故不在此自引用哈希）：

```text
src/ashare_research/mechanism/planning/matrix.py   AC00BEC482692E50A70D387CAE57264727634A3C79C5E50867DDE3B0A38C130D
tests/test_m4_analysis_matrix.py                   2BB380E5486C0EDB13D19FF9136982C562BC27FF891E403AE8828746B16C308E
```

## 6. 本地提交：本会话无法创建（沙箱策略阻塞，真实失败证据）

Goal 要求"创建一个只含四个允许路径的本地提交"。实际执行结果：

```text
git add src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py \
        agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md \
        acceptance/2026-09-11_m4_analysis_matrix_implementation.md
    -> fatal: Unable to create
       'D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation/index.lock': Permission denied
    -> 退出码 128

git commit -m "feat: materialize immutable M4 design matrices from validated plans"
    -> fatal: Unable to create
       'D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation/index.lock': Permission denied
    -> 退出码 128

（尝试顺序与 Goal 语义一致：先 add 后 commit；两次都因同一原因失败，未产生任何部分状态）
```

原因与证据（实际执行）：

1. 本会话文件沙箱策略为 workspace-write：只允许修改会话工作区
   `D:\量化分析-m4-matrix-implementation` 下的文件；而该工作树是 **linked worktree**，
   `.git` 是指针文件（`gitdir: D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation`），
   index、对象库与 `refs/heads/*` 全在父仓库 `D:/量化分析/.git` 中，属工作区之外。
2. 诊断探针（实际执行）：向 `D:/量化分析/.git/dsh_probe_write.tmp` 写入被拒
   （`UnauthorizedAccessException: Access to the path … is denied`），而向会话工作区内写入成功。
   该目录下**没有**残留 `index.lock`（`Test-Path` 对 worktree 与 common 两处均为 `False`），
   因此不是陈旧锁文件问题。
3. 按沙箱规则升级重试同一命令（`sandbox_permissions: danger-full-access` + 理由）被拒绝：
   `Error: sandbox escalation to "danger-full-access" requires approval, but no approval channel
   is available`。审批通道不可用，因此该拒绝是终局；**没有**用任何替代手段（例如自定义
   `GIT_INDEX_FILE`、在别处初始化仓库、手写 objects/refs）绕过它。
4. 失败后工作树保持干净：`git status --short --branch` 只有四个未跟踪交付文件，
   `git diff --cached --check` 退出 0（索引为空），`git rev-parse HEAD` 仍为 `125247d7…`。

因此本轮**没有**创建提交，HEAD 未前进，四个文件以未跟踪状态待提交。恢复方式（需要具备父仓库
`.git` 写权限的会话，或提供审批通道后重试）：

```powershell
cd D:/量化分析-m4-matrix-implementation
git add src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py `
        agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md `
        acceptance/2026-09-11_m4_analysis_matrix_implementation.md
git commit -m "feat: materialize immutable M4 design matrices from validated plans"
git show --stat --oneline HEAD
```

提交内容已冻结为上述四个路径；本会话未推送、未开 PR、未合并，也未改动其它工作树、stash 或
保护数据。Codex 可按 Goal 的 "Commit and push requirements" 自行创建该提交，或把这一步
判为 BLOCKED；本记录不自行给出终局 verdict。

## 7. 远端状态

- `git ls-remote origin` 两次均失败（退出码 128：先是连接 github.com:443 超时，后是
  `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`），因此**未刷新远端 git ref**；
  `origin/main = bab24f98…` 是本地跟踪 ref 的缓存值。
- `gh` CLI 可用并已实时刷新：PR #11 `OPEN`、`MERGEABLE`、head `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`、
  **42/42 checks 全部 pass**。本轮**未**创建/推送本分支的任何远端引用，也未合并任何分支。
- 本分支 `codex/m4-analysis-matrix-implementation` 只存在于本地。

## 8. 差异、偏差与风险（诚实记录）

1. **本地提交未能创建（本轮唯一未完成项）**：`git add` 与 `git commit` 均因沙箱拒绝写入父仓库
   `.git` 而退出 128，升级审批通道不可用，且未采用任何绕过手段（见 §6）。四个交付文件已按 Goal
   的路径与内容冻结在磁盘上，只需一个具备 `D:/量化分析/.git` 写权限的会话执行 §6 给出的两条
   命令即可完成提交。
2. **命令 2 退出码为 1**：原因是 3 个既有 `tmp_path` 用例在本 harness 的 setup 阶段被沙箱拒绝
   （基线同样如此，见 §5.1）。这是环境限制，不是本次实现的失败；但本记录**不**据此宣告套件通过。
3. **工作树根目录残留 `pytest-cache-files-*` 空目录**：pytest `cacheprovider` 在写
   `.pytest_cache` 失败时留在工作树根，本会话沙箱对其后续访问一律拒绝（`Get-ChildItem`/
   `Remove-Item`/`cmd rd` 均"Access is denied"），因此**无法由本会话删除**。它们是未跟踪、
   不可访问、内容为空的目录，未进入任何提交；`git status` 仅对其打印
   "could not open directory … Permission denied" 警告。建议 Codex 在沙箱外清理。
4. **设计口径判定**：§4.4 表列的三处取舍均为收紧或等价的读法，已逐一给出依据；若 Codex
   认定其中某处应按另一种读法实现，属实现评审项，可按 finding 修复（不涉及 schema 变更）。
5. **M1 的不变量 7 部分不可独立判定**：矩阵对象不含 `audit_rows`，该等式在投影管线第 3 步
   对 `preparation` 检查，最终由 V4 逐字节比较兜底（已在 §4.4 说明）。
6. **未验证项**：未在真实 CI（ubuntu）上运行新增测试；未刷新远端 git ref；未做 PR 或合并。
   新增测试只在本 harness 的 Windows/CPython 3.13.9 + ruff 0.13.2 下执行过。
7. **风险**：若 Codex 的独立复跑在同一命令上得到 `270 passed / exit 0`，说明 3 个 error 确为
   本会话沙箱所致；若仍为 3 errors，则需要 Codex 判定该环境问题是否影响验收。同样地，若由
   Codex 创建提交，应核对提交内容恰为四个允许路径。

## 9. 未完成 / 未执行事项

- **本地提交未创建**（`git add` / `git commit` 均被沙箱拒绝写入父仓库 `.git`，退出码 128；升级
  审批通道不可用），因此最终 HEAD 仍是 `125247d7…`，四个交付文件为未跟踪状态；恢复命令见 §6。
- 未执行任何统计：无回归、系数、p 值、标准误、秩、条件数、bootstrap、robustness、evidence。
- 未访问数据库内容（仅对 DB 文件做 SHA256）、provider、真实行情或 holdout。
- 未修改 `__init__.py`、两份设计文档、Goal、既有源码/测试、README、依赖、工作流。
- 未推送、未开 PR、未合并 PR #11，未进入 M4-B。
- 未创建任何"只吃 preparation"的公开入口；未把私有 `_project_validated_matrix` 当作验收入口。
- 未自行给出 PASS 判定；等待 Codex 独立审查（最多三轮修复由 Goal 规定）。

## 10. 下一步

1. 由具备 `D:/量化分析/.git` 写权限的会话（Codex 或用户）按 §6 的两条命令创建本轮的本地提交，
   或先提供审批通道后由本会话重试；提交内容必须恰为四个允许路径。
2. Codex 独立审查真实 branch/HEAD、提交与 diff、变更与未跟踪文件、测试证据、worktree/stash、
   保护基线与远端状态、Goal 合规性、验收证据，verdict 只能是 PASS / CHANGES_REQUIRED / BLOCKED。
3. 若返回 findings，本轮记录与实现按 Goal 规定最多再修复三轮。
4. 推送、PR、合并、M4-B 或任何统计执行阶段均需用户另行明确授权。

本交付**不构成**统计有效性声明、执行授权或 PR #11 合并依据。

## 11. Codex 独立审查与阻塞解除

Codex 没有采用代理的自报结论，而是直接检查真实实现、测试和四个交付路径。独立复跑结果为：

```text
python -m pytest -q tests/test_m4_analysis_matrix.py
  -> 80 passed in 5.71s；exit 0

python -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py \
  tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py \
  tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
  -> 270 passed in 14.92s；exit 0

python -m ruff check src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py
  -> All checks passed!；exit 0
```

因此 §7/§9/§10 中关于“提交未创建”与三项 `tmp_path` 错误的文字只描述 DeepSeek Harness
受限 ACL 会话的历史状态：三项错误在 Codex 环境不复现，linked-worktree 元数据写入限制也由
Codex 解除。Codex 审查确认实现符合冻结 API、验证顺序、投影规则、质量继承、不变对象、规范
摘要/序列化和稳定错误码要求，并以最终动作创建只含四个允许交付路径的本地提交。未推送、未开
PR、未合并、未进入 M4-B，也未执行任何统计。
