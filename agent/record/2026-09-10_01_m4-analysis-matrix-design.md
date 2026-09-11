# 工作记录：M4 synthetic analysis matrix 设计（第 1 轮交付 + 第 2、3 轮修复）

- 状态：`completed`（第 3 轮精确修复完成，等待 Codex 重新独立验收）
- 日期：2026-09-10（第 1 轮交付）；2026-09-11（第 2 轮与第 3 轮修复）
- 工作树：`D:/量化分析-m4-matrix-design`
- 分支：`codex/m4-analysis-matrix-design`
- 起始 HEAD：`b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`（未提交，交付后 HEAD 不变）
- 任务契约：[D:/量化分析/agent/goals/2026-09-10_ds_matrix_design_closeout.md](../../../量化分析/agent/goals/2026-09-10_ds_matrix_design_closeout.md)（工作树外）
- 既有 Goal：[agent/goals/2026-09-10_m4_analysis_matrix_design.md](../goals/2026-09-10_m4_analysis_matrix_design.md)（未跟踪，保留不覆盖；各轮均未改）
- 设计规范：[docs/m4_analysis_matrix_design_v1.md](../../docs/m4_analysis_matrix_design_v1.md)
- 验收场景：[docs/m4_analysis_matrix_acceptance_cases_v1.md](../../docs/m4_analysis_matrix_acceptance_cases_v1.md)
- 验收文档：[acceptance/2026-09-10_m4_analysis_matrix_design.md](../../acceptance/2026-09-10_m4_analysis_matrix_design.md)
- 第 2 轮审查输入：Codex 独立审查 verdict `CHANGES_REQUIRED`，5 项 findings
  （P1 factual / P1 governance / P1 API coherence / P2 evidence / P2 scope），见第 4.6 节
- 第 3 轮审查输入：Codex 第 2 轮独立审查 verdict `CHANGES_REQUIRED`，3 项 findings
  （2×P1 + 1×P2），见第 4.7 节

## 1. 任务目标

第 1 轮：承接被中断的 synthetic analysis matrix 设计交付，完成契约要求的四份授权 Markdown：
设计规范、验收场景、工作记录、验收文档。**不实现矩阵产品代码，不执行统计研究。**

第 2 轮：按 Codex `CHANGES_REQUIRED` 的 5 项 findings 修复上述四份文档（不改既有 Goal），
消除与真实 `compiler.py`/`synthetic.py` 矛盾的说法，重新冻结 materialize/validate API 与
验收案例，然后重跑契约的精确验证命令并如实记录结果。仍然不实现产品代码、不执行统计研究。

第 3 轮（最后一轮精确修复）：只修 Codex 第 2 轮审查的 3 项 findings——(1) 删除"`source_series_role`
不唯一/与 `term_role` 非一一对应"这一与真实计划不符的断言，改为准确理由（`term_role` 是列语义
与投影规则的权威标识；`source_series_role` 只表达输入来源，无法说明该列取常量 `1`、直接取
`values` 还是取 `condition_indicator`）；(2) 修正 `MatrixQualityV1` 与真实 `QualityReportV1`
的矛盾（真实 `QualityReportV1` 无 `status`；`status` 属于 `DatasetPreparationV1` 顶层字段），
写明 `status` 显式继承 `preparation.status`、其余七字段逐字段复制 `preparation.quality` 并说明
为何把顶层 `status` 纳入矩阵 `quality` 块；(3) 不再把 `source_role` 称为"展示用"，改为
"审计/来源元数据（进入规范载荷与摘要、须与计划一致、不参与取值分派）"。同步修正设计、案例、
记录、验收文档；随后按契约只运行一次精确 pytest，并如实记录真实退出码。

## 2. 范围与非目标

**范围内**：四份指定 Markdown；只读复算既有真实实现；执行契约指定的回归命令并记录退出码；
删除仅由上一轮创建的三个临时探针文件。

第 2 轮范围内：修订同四份 Markdown（含本记录）；按 findings 重新冻结公开 API 与验收案例；
只读核对真实 `planning/compiler.py::_terms`、`datasets/synthetic.py`、`tests/test_m4_stage4a2i_analysis_plan.py`；
重跑契约精确验证命令并如实记录真实退出码；复核工作树最终文件状态。

第 3 轮范围内：只修订同四份 Markdown 中与 3 项 findings 相关的文字——§3.2/§4.2/§4.4/§6.3/
§6.5/§10 的分派理由与质量继承表述、AC-15、记录与验收文档的同步；静态核对
`datasets/synthetic.py` 中 `QualityReportV1`/`DatasetPreparationV1` 的真实字段；只读确认
`ordered_terms` 上 `term_role → source_series_role` 的实际取值；按契约只运行一次精确 pytest
并如实记录退出码；复核文档、Git 与保护基线状态。

**非目标（明确不做）**：不修改源码、测试、README、依赖、工作流、历史设计、冻结产物或保护哈希；
不打开数据库连接、不查询数据库内容、不获取真实行情、不调用 provider 或统计模型；
不执行 holdout；不进入 M4-B；不切换/清理其他工作树；不应用或删除 stash；
不递归委派；不 `git add`/`commit`/`push`/`merge`。

## 3. 接手时实际状态核查（2026-09-10）

实际执行的只读检查与结果：

```text
git rev-parse HEAD        -> b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef（与契约预期一致，无漂移）
git branch --show-current -> codex/m4-analysis-matrix-design
git status --short        -> 6 个未跟踪项：
                             .matrix_design_probe.py / probe2 / probe3（上一轮临时探针）
                             agent/goals/2026-09-10_m4_analysis_matrix_design.md（既有 Goal）
                             docs/m4_analysis_matrix_design_v1.md（上一轮草稿）
                             （+ 本次新增的 docs/m4_analysis_matrix_acceptance_cases_v1.md）
```

结论：分支与 HEAD 与契约声明一致；上一轮中断只留下**一份草稿 + 三个临时探针**；
其余两份授权文档（验收场景、工作记录）与验收文档缺失；没有提交，也没有退出码记录。

### 3.1 第 2 轮接手时实际状态（2026-09-11，只读检查）

```text
git rev-parse HEAD        -> b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef（无漂移）
git branch --show-current -> codex/m4-analysis-matrix-design
git status --short        -> 5 个未跟踪项：既有 Goal + 四份授权文档（无其它未跟踪项）
.matrix_design_probe*.py  -> 不存在（第 1 轮已删除）
.tmp_matrix_design_verify -> 不存在（Codex 在精确校验路径后已删除，见 7.1）
.tmpv4 / .tmpv5 / .tmpv6 / .tmp_local_verify -> 既有 ignored 运行/缓存目录，保留未动
```

结论：接手状态就是"既有 Goal + 四份授权文档"，没有第 1 轮遗留的临时目录需要用户清理；
HEAD、分支、保护项均未漂移。

## 4. 实际执行的工作

### 4.1 读取的既有文件（只读）

- `D:/量化分析/AGENTS.md`
- `D:/量化分析/agent/goals/2026-09-10_ds_matrix_design_closeout.md`
- `agent/goals/2026-09-10_m4_analysis_matrix_design.md`
- `docs/m4_analysis_matrix_design_v1.md`（上一轮草稿）
- `.matrix_design_probe.py` / `.matrix_design_probe2.py` / `.matrix_design_probe3.py`（上一轮探针）
- `src/ashare_research/mechanism/datasets/synthetic.py`（适配器真实实现）
- `src/ashare_research/mechanism/datasets/__init__.py`（导出面）
- `src/ashare_research/mechanism/planning/compiler.py`（计划编译器真实实现，含 `_terms`）
- `src/ashare_research/mechanism/planning/__init__.py`
- `src/ashare_research/mechanism/model_digest.py`（`canonical_digest` 真实实现）
- `agent/record/README.md`、`acceptance/2026-09-07_m4_dataset_adapter_design.md`（格式参照）

### 4.2 对既有草稿的审计发现（关键）

对 `docs/m4_analysis_matrix_design_v1.md` 逐节核对真实实现后，发现并修正了下列问题：

| # | 问题 | 性质 | 处置 |
| --- | --- | --- | --- |
| 1 | 第 7 节全部 `matrix_digest` 是用**与第 4.3/6.3 节声明不一致**的临时载荷算出的（探针用了 `column_roles`/`row_count`/`column_count`/`cells`，而冻结形状是 `columns`/`rows`/`quality` 嵌套对象） | 设计自相矛盾，会使实现者算出与文档不同的摘要 | 新增第 6.5 节冻结规范字典精确形状；第 7 节全部 `matrix_digest` 与字节哈希按冻结形状实测重算；新增第 6.6 节诚实记录差异 |
| 2 | 第 4.3 节类型定义没有 `status` 字段，但第 4.4 节不变量 8 写 `status == "READY_MATRIX"` | 引用不存在的字段，且引入未定义状态名 | 不变量 8 改为 `quality.status`；第 10 节明确本设计**不新增** `READY_MATRIX` 状态 |
| 3 | `MatrixQualityV1.reason_counts` 写成 `tuple[tuple[str,int],...]`，但规范字典中必须是 JSON 对象 | 表示差异未说明 | 保留 dataclass 类型并补注"规范字典中转 JSON 对象，是唯一表示差异" |
| 4 | 第 2.4 节未说明 `failure_disposition` 的来源，也未说明 `coverage_numerator == len(complete_rows)`、`complete_rows` 元素形状 | 实现者可能猜错 | 补齐 7 条适配器质量语义，含 `failure_disposition` 来自 `contract.evidence_rule` |
| 5 | 未实测验证"字典键顺序不影响身份""跨目录身份不变"两条 | 设计要求写在文档里但没有证据 | 新增第 7.11 节实测，两条均成立（`canonical_digest` 内部 `sort_keys=True`） |
| 6 | 未实测"重哈希过的原始输入"篡改路径 | 只测了 preparation 篡改，缺输入侧 | 新增第 7.8 节第二组实测（改值 + 重算 `input_digest`/`evidence_digest`），`validate_dataset` 抛 `IDENTITY_CONFLICT` |
| 7 | 第 7.3 节 `GT` 指示列与第 2.3 节篡改后指示列**经复算确认正确**（`GT` 阈值 0 → 全 0；篡改后 (1,1,0)→(0,0,1)） | 无问题，确认 | 保留 |
| 8 | 第 7.10 节未记录 `"0"` 是**唯一**合法零表示 | 规范边界不完整 | 补齐 `"0"` 合法、`-0`/`0.0`/`0.0100`/`1E-2` 非法，并给出 `_dec` 代码 |

**结论：上一轮草稿不可直接交付**——第 1 项会让实现者复现出不同摘要。本轮已修正并全部实测复算。

### 4.3 复算方式（只读探针，未落盘）

全部数值通过**标准输入管道**交给解释器执行，**没有在工作树写入任何探针文件**：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$py | & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -
```

复算口径：`sys.path` 加入 `src` 与 `tests`；使用既有 fixture
`tests/test_m4_stage4a1_typed_contract._document()/_compiled()`；合同、计划、输入、输出
全部走既有真实函数；矩阵投影按设计第 3、6.5 节规则**独立重算**（不调用任何矩阵实现，
因为矩阵实现不存在）。

### 4.4 复算覆盖（实际测量项）

```text
基础 fixture：contract/plan/input/domain/dataset digest、serialize_dataset 字节哈希、
              status、n/N、gate、missingness、reason_counts、role_order、complete_rows、
              ordered_terms、transform_plan.condition、validate_dataset 通过
矩阵投影：   columns(position/term_role/coefficient_role/source_role)、response_role、
              rows(trade_date/cells)、matrix_digest、serialize_matrix 字节哈希
条件边界：   阈值 "0" 与 "-0.0100" × LT/LTE/GT/GTE，各 4 组共 8 组指示列与三摘要
列映射：     无 controls（3 列）、2 controls、3 controls（6 列）、控制顺序反转
质量：       缺口 5 种角色/位置、PIT_UNPROVEN、PIT_NOT_AVAILABLE、value=null、
              FAIL_CLOSED×{0.99,0.66}、RETAIN×{0.66,0.67}、精确有理数门槛复算
身份：       observations 逆序、键序重排、换工作目录、from_dict 往返
篡改：       preparation 指示列取反 + 重哈希 → serializer 接受 / 四参数拒绝
             原始输入改值 + 重哈希 digest 与证据 → 四参数拒绝
嵌套：       合同内层 robustness trim 0.0100→0.0200 → 四个摘要全变 + 混用计划报错
规范十进制： 9 个取值形式的接受/拒绝判定
上游错误：   UNSUPPORTED_MODE / INPUT_DIGEST_MISMATCH / DUPLICATE_OBSERVATION /
             EVIDENCE_DIGEST_MISMATCH / OUT_OF_DOMAIN / CONTRACT_PLAN_MISMATCH
```

全部测量为真实输出，逐项写入设计文档第 7 节与验收场景文档。**未捏造任何摘要**。
探针本身未纳入交付。

### 4.5 四份产出文档

1. `docs/m4_analysis_matrix_design_v1.md`（修订既有草稿，见 4.2）
2. `docs/m4_analysis_matrix_acceptance_cases_v1.md`（新建，案例 AC-01…AC-15 + AC-08b）
3. `agent/record/2026-09-10_01_m4-analysis-matrix-design.md`（本文件）
4. `acceptance/2026-09-10_m4_analysis_matrix_design.md`（新建）

### 4.6 第 2 轮：Codex `CHANGES_REQUIRED` 的 5 项 findings 与实际修复

审查输入为 Codex 独立审查 verdict `CHANGES_REQUIRED` 与下列 findings（用户转达）。
逐项处置如下，全部改动只落在四份授权 Markdown 内，未触碰源码、测试、Goal 或保护项。

| # | 级别 | finding | 实际修复 |
| --- | --- | --- | --- |
| 1 | P1 factual | 文档多处声称 `FACTOR_CONTINUOUS` 与 `CONDITION_INDICATOR` 的 `source_series_role` 相同；真实 `_terms` 与 `tests/test_m4_stage4a2i_analysis_plan.py` 显示前者为 `"FACTOR"`、后者为 `"CONDITION_INDICATOR"`，且设计文档自身第 7 节真实输出已反证该说法 | 设计 §3.2 重写为真实绑定关系（`INTERCEPT=null`、`FACTOR_CONTINUOUS="FACTOR"`、control=自身、`CONDITION_INDICATOR`=transform 输出角色且不在 `role_order`），保留"按 `term_role` 分派"但改以"`term_role` 是列语义身份、`source_series_role` 只是来源绑定"为理由；同步修正 §7.1 注释、§4.2/§10 理由、AC-15 第 6 项、验收文档 decision 2、本记录 §8。该轮残留的"不完备/非一一对应"措辞已在第 3 轮删除（见 4.7 finding 1） |
| 2 | P1 governance | 第 1 轮公开了一个只吃 `preparation` 与 `plan` 的纯投影材料化入口，并在 AC-08 承认它可投影重哈希篡改体，形成公开绕过门禁路径 | 删除该公开签名；对外材料化入口冻结为四参数 `materialize_design_matrix(preparation, contract, plan, bound_inputs)`，顺序固定为 `validate_dataset` → 质量门 → 投影；纯投影降为私有 `_project_validated_matrix(preparation, plan)`（不导出、非 API、非验收入口）。同步改写设计 §2.1/§5.1/§8.1、AC-08/AC-01/AC-05/AC-09 |
| 3 | P1 API coherence | 需要重新冻结 materialize/validate API，使签名、验证顺序、错误行为、`REJECTED_QUALITY` 场景与验收案例互相可执行；`validate_design_matrix` 若调用 `validate_dataset` 必须拥有 `preparation` 参数；不得把不存在的拒绝态 matrix 对象当作必需输入 | 签名冻结为 `materialize_design_matrix(preparation, contract, plan, bound_inputs)` 与 `validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)`；设计 §5.2 给出 A1/A2、V1–V4 的固定顺序；§5.3 按 `MatrixError`/`AdapterError` 两族列码；上游错误原样传播、矩阵内容不一致才是 `MatrixError("IDENTITY_CONFLICT")`；AC-07 改为只断言材料化入口在 A2 抛 `DATASET_NOT_READY`，并明确拒绝态没有可构造的矩阵输入；新增 AC-08b（来源合法 + 伪造矩阵 → `MATRIX_DIGEST_MISMATCH`/`IDENTITY_CONFLICT`）与 AC-14 的两族错误表 |
| 4 | P2 evidence | 必须保留第 1 轮 harness 真实结果 187 passed + 3 setup errors / exit 1，并注明 Codex 以相同契约命令独立得到 190 passed / exit 0；不得用测试体直调等价替代 pytest 成功，删除"环境限制不影响通过"之类预判 | §5.1 重写：第 1 轮命令 1 的真实结果为 `187 passed, 2 warnings, 3 errors`、exit 1，保留为历史事实；明确该结果是本会话 harness 的实测，不作为"套件通过"的证据；Codex 独立以同一命令在同一 HEAD 得到 `190 passed`、exit 0，作为套件真实通过的权威证据；删除"环境限制，不是测试失败""测试体直调等价"等结论性表述，只保留原始观察并注明最终判定属 Codex。第 2 轮重跑命令的真实结果见 §5.3 |
| 5 | P2 scope | Codex 已在精确校验路径后删除 `.tmp_matrix_design_verify`；最终状态应仅既有 Goal + 四份授权文档，不再要求用户清理不存在的目录 | §7.1 与验收文档改为记录实际状态：该目录已不存在，无需任何用户清理；最终未跟踪项恰为 5 个（Goal + 四份文档）；`.tmpv4/.tmpv5/.tmpv6/.tmp_local_verify` 是既有 ignored 目录，保留未动 |

修复后自查（第 2 轮实际执行，见 §5.3）：全文搜索确认不再出现"两个 term 的
`source_series_role` 相同/同为"的主张，不再出现公开两参数 `materialize_design_matrix`，
四份文档关于计划 term 绑定的描述与真实 `compiler.py::_terms` 一致。

### 4.7 第 3 轮：Codex 第 2 轮独立审查 `CHANGES_REQUIRED` 的 3 项 findings 与实际修复

审查输入为 Codex 第 2 轮独立审查 verdict `CHANGES_REQUIRED` 与下列 3 项 findings（用户转达）。
本轮**只修这 3 项，不扩写**；全部改动只落在四份授权 Markdown 内，未触碰源码、测试、Goal 或
保护项，也未新增交付文件。

| # | 级别 | finding | 实际修复 |
| --- | --- | --- | --- |
| 1 | P1 factual precision | 文档已正确列出真实 `source_series_role` 值，却又称其"不具备唯一性""非一一对应"。对当前 `ordered_terms` 集合，`null`/`FACTOR`/`CONTROL_0001`/`CONTROL_0002`/`CONDITION_INDICATOR` 实际互相可区分，是一一映射；`term_role` 与 `source_series_role` 名称不相等不等于数学上的非一一映射 | 全局删除"不唯一/非一一对应/不完备"的错误断言（设计 §3.2、§4.2、§10；AC-15 第 6 项；本记录 §8）。保留按 `term_role` 分派，改以准确理由：`term_role` 是列语义与投影规则的**权威标识**；`source_series_role` 只表达输入来源，无法单独说明该列取常量 `1`、直接取 `values` 还是取 `condition_indicator` 的派生值；`INTERCEPT` 为 `null`、指示列指向不在 `role_order`/`values` 的 transform 输出，证明单靠 `role_order` 查 `source_series_role` 不足——但**不**声称当前取值发生碰撞。设计 §3.2 明确写出"当前取值两两不同、恰好一一映射，但该对应是当前角色命名的结果，不是投影契约，实现不得依赖" |
| 2 | P1 schema contradiction | 真实 `QualityReportV1` **没有** `status`；`status` 属于 `DatasetPreparationV1` 顶层字段。拟议 `MatrixQualityV1` 增加了 `status`，因此设计原"`QualityReportV1` 逐字段镜像（无增删、无重命名）"为假 | 设计 §4.2 改为：`status` **显式继承** `preparation.status`；其余七个字段逐字段复制 `preparation.quality`，不重判、不重命名。并说明为何把顶层 `status` 纳入矩阵 `quality`：矩阵规范载荷不设独立顶层 `status` 字段（§6.5 约束 3），就绪/拒绝状态必须与质量明细在唯一位置被下游读到，避免两个可能互相矛盾的状态字段；矩阵层不新增状态词表。同步修正 §4.2 dataclass 注释、§4.4 不变量 7、§6.3 摘要覆盖面、§6.5 约束 3、§10 表；AC-15 新增第 9 项继承断言；验收文档新增 decision 7 |
| 3 | P2 wording | `source_role` 字段不是纯展示，因为它进入规范载荷、摘要并须与 plan 一致 | 设计 §4.2 改称"**审计/来源元数据**"：进入规范载荷、序列化字节与 `matrix_digest`，必须与计划的 `source_series_role` 一致，属于被冻结的身份内容；**不参与单元格取值分派**。§10 表项标题同步由"展示字段"改为"审计/来源元数据"；AC-15 验证入口补充同一声明。全文不再出现"展示用/仅展示"的表述 |

第 3 轮自查（实际执行，见 §5.6）：全文搜索四份文档确认不再出现"不具备唯一性""非一一对应"
"逐字段镜像（无增删）""展示用/仅展示"等错误表述（仅保留标注为纠错记录的历史说明）；
`QualityReportV1`/`DatasetPreparationV1` 字段按真实源码静态核对，并用只读探针在真实 fixture 上
确认 `ordered_terms` 的 `term_role → source_series_role` 取值两两不同。

## 5. 实际执行的验证命令与退出码

### 5.0 第 1 轮实测命令（历史记录，保留真实值）

全部命令从 `D:/量化分析-m4-matrix-design` 执行。第 1 轮真实结果如下；命令 1 的退出码是
**1**，不粉饰为通过。第 2 轮的复跑见 §5.3，第 3 轮（本轮）的复跑见 §5.5。

| # | 命令 | 退出码 | 结果 |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | **1** | `187 passed, 2 warnings, 3 errors`（3 个 error 发生在 setup 阶段，为 `pytest-of-*` 临时目录 `PermissionError`，见 5.1） |
| 2 | 同上 + `TEMP` 指向工作树内目录 | **1** | 同样 3 个 setup error（辅助诊断） |
| 3 | 同上 + `--basetemp` 指向非 `pytest-of-*` 目录 | **1** | 3 个 error 未消失；另在 session 收尾 `cleanup_dead_symlinks` 处 `PermissionError`（辅助诊断） |
| 4 | `git diff --check` | **0** | 无空白问题 |
| 5 | `git diff --cached --check` | **0** | 无暂存问题（暂存区为空） |
| 6 | `git status --short` | **0** | 见 7（工作树状态） |
| 7 | `git rev-parse HEAD` | **0** | `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`（未提交，与起始一致） |
| 8 | `git worktree list --porcelain` | **0** | 12 个工作树，全部存在且未被本任务改动 |
| 9 | `git stash list` | **0** | 仅 `stash@{0}`（原有） |
| 10 | `git rev-parse refs/stash` | **0** | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`（**等于保护值**） |
| 11 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7…E2FCE6`（**等于保护值**，仅哈希，未读取内容） |
| 12 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` → **无法刷新远端 ref**，见 6 |
| 13 | `git rev-parse origin/main origin/codex/m4-synthetic-dataset-adapter`（本地跟踪 ref） | **0** | `bab24f98…` / `b0c8fafb…`（与基线一致） |
| 14 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222`（**等于保护值**） |
| 15 | `gh pr view 11 --json …` | **0** | `state=OPEN`、`headRefOid=b0c8fafb…`、`baseRefName=main`、`mergeable=MERGEABLE`、`mergedAt=null` |
| 16 | `gh api repos/.../commits/b0c8fafb…/check-runs` | **0** | `total_count=42`；按 conclusion 分组：**`success` × 42** |
| 17 | `gh api repos/.../commits/b0c8fafb…/status` | **0** | `pending`（该 commit 无 legacy commit status，只有 check-runs） |
| 18 | 三份文档 Markdown 审计（UTF-8/BOM/CRLF/TAB/行尾空白/末尾换行/冲突标记/围栏配平） | **0** | 三份全部 `issues=NONE` |
| 19 | 相对链接解析 | **0** | 修正后全部 OK（见 5.2） |
| 20 | 三个被 `tmp_path` 阻塞的测试体直调（真实目录替代 `tmp_path`） | **0** | 5 项断言全部 `True`（**辅助诊断**，不等价于 pytest 通过，见 5.1） |

### 5.1 第 1 轮命令 1 的真实结果与 Codex 的独立复跑（不作等价替代）

第 1 轮命令 1 的真实结果是 **`187 passed, 2 warnings, 3 errors`，exit 1**。3 个 error 发生在
pytest **setup 阶段**：

```text
PermissionError: [WinError 5] 拒绝访问:
'C:\Users\111\AppData\Local\Temp\dsh-6vjO3y\pytest-of-dlam12138'
（以及当时工作树内 .tmp_matrix_design_verify\pytest-of-dlam12138 的同名错误）
位置：_pytest/pathlib.py find_prefixed -> os.scandir(root)
```

第 1 轮做过的辅助观察（全部实际执行，如实保留，但**不构成"套件通过"的证据**）：

1. 手动在同一父目录创建目录并 `os.scandir` / `os.listdir` / `tempfile.mkdtemp` 全部成功。
2. 直接调用 pytest 内部 `find_prefixed(...)` 与 `make_numbered_dir(...)` 均 `PermissionError 5`。
3. 换 `TEMP`、换 `--basetemp` 都不能规避（命令 2、3）。
4. 直接执行这 3 个测试体（用真实目录替代 `tmp_path` 参数）时 5 项断言为 `True`（命令 20）。

**这些观察不能替代 pytest 成功。** 测试体直调绕过了 pytest 的收集、fixture 与 setup 流程，
与"该命令 exit 0"不是同一命题；第 1 轮记录里"环境限制不影响通过""测试体直调等价"一类推断
已删除，本记录不对套件是否通过自行下结论。

套件真实通过的证据来自 Codex 的独立复跑：Codex 在同一 HEAD
`b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef` 上以**完全相同的契约命令**运行，得到
**190 passed、exit 0**（无 error）。因此：

```text
第 1 轮 harness 实测 : 187 passed + 3 setup errors / exit 1   （本会话真实结果，保留）
Codex 独立实测       : 190 passed / exit 0                    （套件通过的权威证据）
```

两者相差的 3 个用例正是第 1 轮 setup 阶段被拒绝的 `tmp_path` 用例；差异归因于第 1 轮会话
沙箱拒绝 `pytest-of-*` 临时目录，但该归因由 Codex 的独立复跑支持，不是本记录自行宣告
"环境问题不影响通过"。最终判定属 Codex。

### 5.2 第 1 轮文档审计结果

第 1 轮四份交付文档的审计结果（UTF-8、无 BOM、无 CRLF、无 TAB、无行尾空白、末尾换行存在、
无冲突标记、代码围栏配平）：

```text
docs/m4_analysis_matrix_design_v1.md                     issues=NONE
docs/m4_analysis_matrix_acceptance_cases_v1.md           issues=NONE
agent/record/2026-09-10_01_m4-analysis-matrix-design.md  issues=NONE
acceptance/2026-09-10_m4_analysis_matrix_design.md       issues=NONE
missing relative links: NONE
```

全部仓库内相对链接可解析（`docs/`、`agent/`、`acceptance/` 之间互相引用）。

跨文档摘要一致性核对（同一个 `matrix_digest` 必须同时出现在设计文档与验收场景文档）：

```text
base            design=5 cases=2   OK
no-controls     design=1 cases=1   OK
reordered ctrl  design=1 cases=1   OK
three controls  design=1 cases=1   OK
2/3 retain      design=2 cases=1   OK
nested contract design=1 cases=1   OK
rehashed input  design=1 cases=1   OK
tampered        design=1 cases=1   OK
```

修正记录：首次一致性核对发现"三个控制项"案例只写在验收场景文档、"2/3 RETAIN 通过时
的矩阵身份"只写在设计文档。已分别补入设计文档第 7.12 节与验收场景文档 AC-05，
再核对全部通过。

注意：`git diff --check` **不覆盖未跟踪文件**，因此未跟踪 Markdown 的空白与链接检查
由上述独立审计完成，而不是由 `git diff --check` 覆盖。

### 5.3 第 2 轮实测命令与真实退出码（2026-09-11）

全部命令从 `D:/量化分析-m4-matrix-design` 执行；pytest 只按契约原样运行**一次**，
**没有**自造 `TEMP` 或 `--basetemp` 目录，也没有写入任何探针文件。

| # | 命令 | 退出码 | 真实结果 |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | **1** | `187 passed, 2 warnings, 3 errors in 2.83s`；3 个 error 全部是 setup 阶段 `pytest-of-dlam12138` 的 `PermissionError [WinError 5]`（与第 1 轮同类）；**不作为通过** |
| 2 | `git diff --check` | **0** | 无空白问题 |
| 3 | `git diff --cached --check` | **0** | 暂存区为空，无问题 |
| 4 | `git status --short` | **0** | 恰好 5 个未跟踪项：既有 Goal + 四份授权文档 |
| 5 | `git rev-parse HEAD` | **0** | `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`（与起始一致，未提交） |
| 6 | `git worktree list --porcelain` | **0** | 12 个工作树，全部保留 |
| 7 | `git stash list` | **0** | 仅原有 `stash@{0}` |
| 8 | `git rev-parse refs/stash` | **0** | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`（等于保护值） |
| 9 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222`（等于保护值） |
| 10 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`（等于保护值，仅哈希） |
| 11 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`——远端 git ref **仍无法刷新** |
| 12 | `git rev-parse origin/main origin/codex/m4-synthetic-dataset-adapter` | **0** | `bab24f981fef9336b84280544ce709702b9df116` / `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`（本地跟踪 ref） |
| 13 | `gh pr view 11 --json state,headRefOid,baseRefName,mergeable,mergedAt` | **0** | `OPEN` / `b0c8fafb…` / `main` / `MERGEABLE` / `mergedAt=null`（实时刷新） |
| 14 | `gh api --paginate repos/.../commits/b0c8fafb…/check-runs` | **0** | 分页取回 **42** 条，conclusion 全部 `success`（首屏 30 条是默认分页，已用 `--paginate` 取全） |
| 15 | `gh api repos/.../commits/b0c8fafb…/status` | **0** | `pending`（无 legacy commit status，只有 check-runs） |
| 16 | 五份 Markdown 审计（UTF-8/BOM/CR/TAB/行尾空白/末尾换行/冲突标记/围栏配平 + 相对链接解析） | **0** | 四份交付文档与既有 Goal 全部 `issues=NONE`，无缺失相对链接 |
| 17 | 第 2 轮自查 `rg`/`Select-String`：两参数公开签名、第 1 轮曾用的 `*_verified` 后缀临时名称、虚假碰撞主张、`source_series_role` 绑定一致性 | **0** | 见 5.4 |
| 18 | 只读标准输入探针：`_compiled()` → `build_analysis_plan` → `plan_to_canonical_dict`，打印真实 `ordered_terms`/`response_role`/requirements/condition | **0** | 真实输出与四份文档完全一致：`INTERCEPT→None`、`FACTOR_CONTINUOUS→"FACTOR"`、`CONTROL_00nn→自身`、`CONDITION_INDICATOR→"CONDITION_INDICATOR"`；`requirement_roles=[TARGET_OUTCOME,FACTOR,CONTROL_0001,CONTROL_0002]`（指示列确不在 role_order）；`threshold="-0.01"` |

第 2 轮命令 1 的诚实结论：本会话 harness **再次**得到 `187 passed + 3 setup errors`、exit 1
（同样是 `pytest-of-*` 临时目录在 setup 阶段被拒），因此本记录**不**声称套件在本 harness
通过。套件通过的权威证据仍是 Codex 在同一 HEAD 用同一命令独立得到的 `190 passed / exit 0`
（见 5.1）。第 2 轮没有做任何测试体直调，也没有用任何替代手段伪装 pytest 通过。

### 5.4 第 2 轮自查结果（针对 5 项 findings）

```text
公开的"只吃 preparation + plan"两参数材料化入口            -> 0 处（唯一公开入口为四参数版本）
已废弃的第 1 轮 `*_verified` 后缀名称                       -> 0 处
"FACTOR_CONTINUOUS 与 CONDITION_INDICATOR 的 source_series_role 相同/同为" 的主张 -> 0 处
  （仅剩两处明确标注为"第 1 轮错误声称、第 2 轮已修正"的纠错记录）
四份文档中 source_series_role 的绑定描述                     -> 与 compiler.py::_terms 一致：
   INTERCEPT=null / FACTOR_CONTINUOUS="FACTOR" / CONTROL_00nn=自身 / CONDITION_INDICATOR="CONDITION_INDICATOR"
   （由第 5.3 节命令 18 的只读探针在真实 fixture 上运行确认，不只是静态阅读源码）
role_order 成员关系                                          -> 与 datasets/synthetic.py 的 ROLES 一致：
   ("TARGET_OUTCOME","FACTOR", CONTROL_0001...)；CONDITION_INDICATOR 不是 role_order 成员
   （命令 18 实测 requirement_roles=[TARGET_OUTCOME,FACTOR,CONTROL_0001,CONTROL_0002]）
公开材料化入口                                               -> 只有四参数版本；纯投影 _project_validated_matrix 为私有
```

### 5.5 第 3 轮实测命令与真实退出码（2026-09-11）

全部命令从 `D:/量化分析-m4-matrix-design` 执行。契约规定的 pytest 只运行**一次**，
**没有**自造 `TEMP` 或 `--basetemp`，没有写入任何探针文件，也没有做测试体直调；其余命令
均为只读。

| # | 命令 | 退出码 | 真实结果 |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | **1** | `187 passed, 2 warnings, 3 errors in 2.70s`；3 个 error 全部是 setup 阶段 `C:\Users\111\AppData\Local\Temp\dsh-CxqUfP\pytest-of-dlam12138` 的 `PermissionError [WinError 5]`，对应 `test_cwd_and_from_dict_order_invariance`、`test_semantic_ab_equivalence_and_cwd_independence`、`test_yaml_loader_requires_mapping_and_rejects_object_tags`；2 个 warning 是 `.pytest_cache\v\cache\{nodeids,lastfailed}` 的 `PytestCacheWarning`（同为 `WinError 5`）；**不作为通过** |
| 2 | `git diff --check` | **0** | 无空白问题 |
| 3 | `git diff --cached --check` | **0** | 暂存区为空，无问题 |
| 4 | `git status --short` | **0** | 恰好 5 个未跟踪项：既有 Goal + 四份授权文档 |
| 5 | `git rev-parse HEAD` | **0** | `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`（与起始一致，未提交） |
| 6 | `git worktree list --porcelain` | **0** | 12 个 worktree 条目，全部保留 |
| 7 | `git stash list` | **0** | 仅原有 `stash@{0}` |
| 8 | `git rev-parse refs/stash` | **0** | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`（等于保护值） |
| 9 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222`（等于保护值） |
| 10 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`（等于保护值，仅哈希，未读取内容） |
| 11 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`——远端 git ref **未刷新** |
| 12 | `git rev-parse origin/main origin/codex/m4-synthetic-dataset-adapter` | **0** | `bab24f98…` / `b0c8fafb…`（本地跟踪 ref，缓存值） |
| 13 | `gh pr view 11 --json state,headRefOid,baseRefName,mergeable,mergedAt` | **1** | `Post "https://api.github.com/graphql": EOF`——GitHub API 在本轮**不可达**，PR 状态**未刷新** |
| 14 | `gh api --paginate .../commits/b0c8fafb…/check-runs` 与 `gh api .../status` | **1** | 两者均 `EOF`，check-runs **未重新读取** |
| 15 | 复测 `gh pr view 11` 与 `gh api rate_limit`（可达性确认） | **1** | 两者仍 `EOF`，确认不是一次性解析错误，而是 API 不可达 |
| 16 | 四份交付文档 + 既有 Goal 的 Markdown 审计（UTF-8/BOM/CR/TAB/行尾空白/末尾换行/冲突标记/围栏配平 + 相对链接解析） | **0** | 五份全部 `OK`，`MISSING_RELATIVE_LINKS=NONE` |
| 17 | 第 3 轮全文短语扫描（禁止出现的唯一性/非一一对应断言、"逐字段镜像（无增删）""展示用/仅展示"） | **0** | 设计、验收场景、验收文档：0 处命中；本记录中仅存在于明确标注的"finding 与修复"纠错表格内 |
| 18 | 静态核对 `datasets/synthetic.py` 真实 schema | **0** | `QualityReportV1` 恰好 7 个字段且**无** `status`；`DatasetPreparationV1` **有**顶层 `status`；故"7 个复制字段 + 继承 `status`"是准确表述 |
| 19 | 只读标准输入探针（不落盘）：真实 fixture → `build_analysis_plan` → `plan_to_canonical_dict`，并对 `compiler.py::_terms` 取 0/2/3 个 control | **0** | 真实绑定为 `INTERCEPT→None`、`FACTOR_CONTINUOUS→"FACTOR"`、`CONTROL_00nn→自身`、`CONDITION_INDICATOR→"CONDITION_INDICATOR"`；0/2/3 个 control 三种情况下 `term_role` 取值两两不同、`source_series_role` 取值两两不同、映射单射均为 `True` |

第 3 轮命令 1 的诚实结论：本会话 harness **再次**得到 `187 passed + 3 setup errors`、exit 1
（同样是 `pytest-of-*` 临时目录在 setup 阶段被拒），本记录**不**声称套件在本 harness 通过；
套件通过的权威证据仍是 Codex 在同一 HEAD 用同一命令独立得到的 `190 passed / exit 0`（见 5.1）。
第 3 轮没有做任何测试体直调，也没有用任何替代手段伪装 pytest 通过。与第 2 轮不同，本轮
GitHub API 不可达，因此 PR #11 与 check-runs 数值仍是第 2 轮的实测值，**不**声称本轮重新核验。

### 5.6 第 3 轮自查结果（针对 3 项 findings）

```text
"不具备唯一性 / 非一一对应 / 唯一性与完备性 / 不完备" 错误断言
    -> 设计、验收场景、验收文档 0 处；本记录仅存于标注为纠错记录的 finding/修复表格
"QualityReportV1 逐字段镜像（无增删、无重命名）"        -> 0 处（改为 status 继承 + 七字段复制）
"展示用 / 仅展示"（描述 source_role）                  -> 0 处（改为"审计/来源元数据，不参与取值分派"）
QualityReportV1 真实字段数                              -> 7，且不含 status
DatasetPreparationV1 是否含 status                      -> 是（顶层字段，位置 8）
设计 §4.2/§4.4/§6.3/§6.5/§10 的 status 表述             -> 一致：显式继承 preparation.status，不重判
AC-15 新增第 9 项                                      -> quality.status 继承 + 七字段逐字段相等
ordered_terms 上 term_role -> source_series_role        -> 0/2/3 control 均为单射，取值两两不同
    （命令 19 实测：INTERCEPT=None / FACTOR_CONTINUOUS=FACTOR / CONTROL_00nn=自身 /
      CONDITION_INDICATOR=CONDITION_INDICATOR；设计已写明该一一对应不是投影契约）
```

## 6. 远端状态（第 3 轮：git ref 与 GitHub API 均未刷新）

- 第 3 轮 `git ls-remote origin` **仍失败（退出码 128）**：`schannel:
  AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`。因此**不能**声称已刷新远端 git ref；
  本地跟踪 ref `origin/main = bab24f98…`、`origin/codex/m4-synthetic-dataset-adapter =
  b0c8fafb…` 与基线一致，但这是**本地缓存**值。
- 第 3 轮 `gh` CLI **也**不可达：`gh pr view 11`、`gh api .../check-runs`、
  `gh api .../status` 以及可达性复测 `gh api rate_limit` 全部返回 `EOF`、退出码 1。因此本轮
  **未**刷新 PR #11 状态或 check-runs；下文引用的 `OPEN` / `42 条 success` 是第 2 轮的实际
  测量值，不是本轮核验结果，本轮不把它当作新鲜证据。
- 本地 `codex/m4-analysis-matrix-design` **没有**远端分支，各轮均**不推送**。

## 7. 工作树与保护状态（第 3 轮结束时实测）

```text
HEAD                  b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef（未提交，与起始一致）
分支                  codex/m4-analysis-matrix-design（无远端对应分支，未推送）
暂存区                 空（未 git add；git diff --cached --check 退出 0）
已修改的已跟踪文件        无（git diff --check 退出 0）
未跟踪项（恰好 5 个）      agent/goals/2026-09-10_m4_analysis_matrix_design.md（既有 Goal，未改）
                        docs/m4_analysis_matrix_design_v1.md（第 1 轮草稿修订 + 第 2、3 轮修复）
                        docs/m4_analysis_matrix_acceptance_cases_v1.md（AC-01…AC-15 + AC-08b；AC-15 第 3 轮同步）
                        agent/record/2026-09-10_01_m4-analysis-matrix-design.md（本文件）
                        acceptance/2026-09-10_m4_analysis_matrix_design.md
临时/探针文件            无（第 3 轮未新建，复核确认不存在，见 7.1）
工作树数量               12（全部保留，未切换、未清理）
stash                   cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f（等于保护值，未应用未删除）
原 M2 HEAD              3679b1bac7a1634c6452784a4d8f6d139966f222（等于保护值）
DB SHA256               4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6（等于保护值）
```

即最终状态恰为契约允许的"既有 Goal + 四份授权文档"；没有其它未跟踪文件，也没有需要用户
清理的残留目录。

### 7.1 临时目录偏差已消除（第 3 轮复核）

- 第 1 轮中断时遗留的三个临时探针 `.matrix_design_probe.py`、`.matrix_design_probe2.py`、
  `.matrix_design_probe3.py`：第 1 轮已删除，第 2、3 轮复核确认**不存在**。
- 第 1 轮为诊断 `tmp_path` 错误曾在工作树内创建临时验证目录 `.tmp_matrix_design_verify/`，
  当时在沙箱内无法删除，被记录为"需在沙箱外手工清理"。**Codex 已在精确校验路径后删除该
  目录**；第 2、3 轮复核确认它**不存在**。因此最终状态**不需要任何用户清理**，也不再存在
  任何由本任务创建的临时目录或探针文件。
- 第 2 轮没有新建任何临时目录或探针文件；复算如需要只通过标准输入执行，不落盘。
- 第 3 轮同样没有新建任何临时目录或探针文件；只读复算仍通过标准输入执行，不落盘。
- `.tmpv4/`、`.tmpv5/`、`.tmpv6/`、`.tmp_local_verify/` 是早于本任务的既有 ignored
  运行/缓存目录，保留未动（`git status --short` 不显示 ignored 项，仅出现关于这些目录的
  "could not open directory" 警告）。

## 8. 设计要点（第 3 轮冻结）

- **来源验证与材料化入口绑定**：既有四参数 `validate_dataset(preparation, contract, plan,
  bound_inputs)` 是唯一来源验证入口；公开材料化入口
  `materialize_design_matrix(preparation, contract, plan, bound_inputs)` 必须先调用它，
  再检查 `READY_SYNTHETIC`，最后投影。不存在只吃 `preparation` 的公开入口；纯投影
  `_project_validated_matrix` 是私有实现细节，不是 API、不是验收入口。只信
  `dataset_digest` 或只跑 serializer 都会接受篡改体（已实测）。
- **列顺序只来自计划**：`plan.design_plan.ordered_terms`；断言序列为
  `INTERCEPT, FACTOR_CONTINUOUS, 注册顺序 CONTROL_0001…, CONDITION_INDICATOR`。
  不得复用固定 M3 列表、固定开发期或字母序。
- **取值只按 `term_role` 分派**：真实 `compiler.py::_terms` 的绑定是
  `INTERCEPT → null`、`FACTOR_CONTINUOUS → "FACTOR"`、`CONTROL_00nn → 自身`、
  `CONDITION_INDICATOR → "CONDITION_INDICATOR"`（最后一个是 transform 输出角色，不是
  `role_order` 成员；指示值在 `condition_indicator` 独立元素里，不在 `values` 中）。
  `term_role` 是列语义与投影规则的权威标识；`source_series_role` 只表达输入来源，无法单独
  说明该列取常量 `1`、直接取 `values` 还是取 `condition_indicator`，按它建表会在截距列与
  指示列上解析不出正确来源。当前 `ordered_terms` 上两者取值恰好一一对应（`null`/`FACTOR`/
  `CONTROL_0001`/`CONTROL_0002`/`CONDITION_INDICATOR` 两两不同），但该对应是当前角色命名的
  结果，不是投影契约，实现不得依赖。（第 1 轮曾错误声称两个 term 的 `source_series_role`
  相同，第 2 轮已按真实代码修正；第 2 轮残留的"不完备/非一一对应"措辞已在第 3 轮删除。）
- **质量继承而非重判**：`MatrixQualityV1.status` 显式继承 `preparation.status`（真实
  `QualityReportV1` 不含 `status`，`status` 属于 `DatasetPreparationV1` 顶层字段），其余七个
  字段逐字段复制 `preparation.quality`；矩阵层不新增状态词表。
- **`source_role` 是审计/来源元数据**：进入规范载荷、序列化与 `matrix_digest`，必须与计划
  一致；不参与单元格取值分派，但也不是"纯展示"。
- **规范十进制身份**：不以 float 为边界；`INTERCEPT` 冻结为字符串 `"1"`；指示列为
  `"0"`/`"1"`（严格 `int`）；零的唯一表示是 `"0"`。
- **`REJECTED_QUALITY` 不产出可用部分矩阵**：公开材料化入口在质量门抛
  `MatrixError("DATASET_NOT_READY")`，不返回 0 行或 2 行的"部分成功"对象；拒绝态下不存在
  可构造的矩阵输入，`validate_design_matrix` 也不接受伪造的"拒绝态矩阵"作为必需输入。
  `FAIL_CLOSED` 下降低 gate 不能绕过质量门。
- **上游错误原样传播**：`AdapterError` 不包装、不改码；只有矩阵内容与重投影不一致才抛
  `MatrixError("IDENTITY_CONFLICT")`。
- **硬隔离**：矩阵准备成功不声明满秩、可估计、显著、可交易或执行授权；不计算回归、
  bootstrap、robustness、evidence；`execution_authorized` 与 `statistics_computed`
  恒为 `False`。
- **不需 schema 变更**：如需变更任何冻结 schema，停止并报告。

## 9. 未完成 / 未执行事项

- 未实现任何矩阵产品代码（本阶段非目标）。
- 未新增或修改任何测试（契约禁止）。
- 未执行全量测试套件（契约说明纯新增设计文档不要求）。
- 未提交、未推送、未开 PR、未合并（契约要求）。
- 未访问数据库内容、provider、真实行情、holdout。
- 第 3 轮按契约只运行一次精确 pytest，真实结果见 §5.5；本轮未做任何测试体直调，也没有用
  任何替代手段伪装 pytest 通过。
- 远端 git ref 若第 3 轮仍无法刷新，则如实标注为未刷新（见 6），不伪称同步。
- 第 1 轮那 3 个 `tmp_path` 用例未能在第 1 轮 harness 的 pytest 内运行（setup 阶段被
  沙箱拒绝）；测试体直调结果只作辅助诊断，**不视为 pytest 通过**（见 5.1）。套件通过的
  权威证据是 Codex 的独立复跑 190 passed / exit 0。
- `.tmp_matrix_design_verify/` 已由 Codex 在精确校验路径后删除，不再是遗留项（见 7.1），
  无需用户清理。

## 10. 下一步（均需另行授权）

1. Codex 重新独立验收第 3 轮精确修复后的四份文档 + 既有 Goal，verdict 仅为 PASS /
   CHANGES_REQUIRED / BLOCKED。第 1、2 轮 verdict 均为 CHANGES_REQUIRED，本记录不对本轮
   修复结果自行判定通过，只报告证据。
2. 若验收通过，矩阵实现需另立 Goal 并获用户明确授权。
3. PR #11 合并、M4-B、任何统计执行阶段均需用户分别明确授权。

本设计交付**不是**实现授权，也**不是**统计有效性声明。
