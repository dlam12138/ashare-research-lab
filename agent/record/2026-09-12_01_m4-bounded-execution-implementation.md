# 工作记录：M4 有界执行（synthetic-only bounded execution）实现

## 基本信息

- 日期：2026-09-12
- Agent：DeepSeek Harness（executor；reviewer = Codex）
- 当前分支：`codex/m4-bounded-execution-implementation`
- 开始提交：`070a26ad967016580d56f046d73c52f3d41010e9`
- 任务来源：`agent/goals/2026-09-12_m4_bounded_execution_implementation.md`（Codex 所有，已在基线提交）
- 对应模块：机制验证（M4-A.2E 有界执行；仅合成 fixture）

## 任务目标

按已冻结的
[有界执行与证据处置设计 v1](../../docs/m4_bounded_execution_and_evidence_design_v1.md)
与
[验收场景 v1](../../docs/m4_bounded_execution_acceptance_cases_v1.md)，
在 `src/ashare_research/mechanism/execution/` 新增 allow-list 执行包，实现 8 个公开入口、
不可变/确定性产物、X1–X16 / R0–R9 / V1–V4 冻结顺序与 AC-01..AC-19，且只在合成 fixture 上
计算系数、bootstrap 区间与证据处置。不触碰任何上游 schema、planning/datasets、顶层
mechanism 文件、依赖、工作流或保护测试。

## 范围

白名单（Goal 第 "Allowed scope" 节）：

1. `agent/goals/2026-09-12_m4_bounded_execution_implementation.md`（Codex 契约，未改）
2. `src/ashare_research/mechanism/execution/__init__.py`（新增）
3. `src/ashare_research/mechanism/execution/bounded.py`（新增）
4. `tests/test_m4_bounded_execution.py`（新增）
5. `README.md`（仅同步过时能力/路线图/授权措辞）
6. `tests/test_project_entry.py`（仅同步过时能力断言，保留全部保护性断言）
7. `tests/test_m4_stage4p_governance.py`（仅同步过时 README 状态断言，保留冻结聚合与北极星门）
8. `agent/record/2026-09-12_01_m4-bounded-execution-implementation.md`（本文件）
9. `acceptance/2026-09-12_m4_bounded_execution_implementation.md`（新增）

## 非目标

真实数据、provider、数据库内容、holdout、M4-B、生产执行、交易结论、A 股机制结论；不修改
既有 schema / 摘要算法 / planning / datasets / 顶层 mechanism / 依赖 / 工作流 / 保护测试；
不推送、不开 PR、不合并、不做破坏性 Git 清理、不进入下一阶段；未递归委派。

## 开始前状态

- `git status --short`：干净（无输出）。
- `git branch --show-current`：`codex/m4-bounded-execution-implementation`。
- `git rev-parse HEAD`：`070a26ad967016580d56f046d73c52f3d41010e9`（= Goal 声明基线）。
- `main` / `origin/main`：`f34adcb17c9995392690a1df6bb5a10ee102eb09`（Goal 声明一致）。
- `git worktree list`：15 个 worktree（含本工作树），全部保留、未切换、未清理。
- `git stash list`：仅有既有 `stash@{0}`（`On feat/m2-value-assessment-mvp: ...`）。
- 保护 M2 HEAD：`D:/量化分析` = `3679b1bac7a1634c6452784a4d8f6d139966f222`。
- DB SHA256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`（仅哈希，未打开数据库）。
- 解释器：`D:/量化分析-m4a2i/.venv/Scripts/python.exe`（Python 3.13.9，numpy 2.5.3，ruff 0.13.2）。
- 已知环境问题：sandbox 拒绝枚举 `0o700` 目录，pytest 的 `tmp_path`/`--basetemp` 均以
  `mode=0o700` 创建目录，因此上游 M4 回归组出现 3 个 setup 阶段 error（基线实测
  `252 passed, 3 errors`，exit 1）。

## 实施计划

1. 复现负例基线（上游回归组 + 已知 tmp_path 问题，含显式 `--basetemp` 对照）。
2. 新增执行包：常量、`ExecutionError`、冻结产物 dataclass、X1–X16 / R0–R9 / V1–V4、
   8 个公开入口。
3. 新增 `tests/test_m4_bounded_execution.py`：先负例（X2/X3/X4/X7/X8/签名层）再正例
   （AC-01/AC-08/AC-10/AC-12/AC-14/AC-15/AC-18/AC-19），只断言结构与不变量，不写死数值期望。
4. 同步 README 与两处允许测试的过时措辞，保留全部保护性断言。
5. 执行 Goal 中全部验证命令并记录真实退出码。
6. 写 acceptance 文档，更新本记录，显式路径 `git add` 后创建范围化本地提交。

## 决策记录

1. **决策：执行层自带递归 shape 检查（X1），不只检查顶层类型。**
   原因：冻结顺序要求 X1 先于 X2，且必须拒绝可变容器/布尔陷阱；复用既有 `_shape` 语义但自行实现，
   因为 `FrozenJSONObject` 的 `Any` 值域需要冻结 JSON 校验分支。
   替代方案：直接调用既有模块的私有 `_check_type`。未采用原因：跨模块依赖私有函数，且无法覆盖
   `BoundDatasetInputsV1`/`FrozenMechanismContract` 的完整形状。
   风险：形状检查失败一律映射为 `INVALID_INPUT_STRUCTURE`，与设计一致，无额外风险。
2. **决策：bootstrap 的允许列表门只放在 X11。**
   原因：初版把 method/RNG/replications 门写进“读取计划声明”的辅助函数，那会让 X11 门早于
   X8–X10 触发，违反冻结顺序（例如秩不足应先在 X8 命中 `SINGULAR_DESIGN`）。
   替代方案：保留早门并调整顺序断言。未采用原因：会改变冻结的首错语义。
   风险：无（读取仍只做结构校验，语义门集中在 X11）。
3. **决策：注册稳健性参数从**冻结**计划对象读取（`plan.robustness_plan` 的 `FrozenJSONObject`），
   而不是从 `plan_to_canonical_dict` 的解冻副本读取。**
   原因：设计 10.2 要求产物逐字、不可变地转发既有 `FrozenJSONObject`；解冻副本是普通 dict，
   直接放进产物会改变类型并违反“完整转发/不可变”语义。
   替代方案：用解冻 dict 再重新冻结。未采用原因：重新冻结不是“逐字转发”，且会掩盖上游类型异常。
   风险：需要在 R7/R8 里对齐解冻视图与冻结视图的 ID 顺序；实现里两条路径都来自同一计划对象，
   并以冻结视图为准。
4. **决策：`_check_descriptives` 只校验角色唯一性，不校验字母序。**
   原因：条件描述统计的八个角色是**固定语义顺序**（CONDITION_COUNT、ORDINARY_COUNT、…），
   不是字母序；初版误用 `sorted(roles)`，被 AC-01 立刻捕获。角色集合与顺序的精确校验在 X14 完成。
   风险：无。
5. **决策：V1 不重新推导 evidence 处置表，只校验词表成员与内部一致性。**
   原因：AC-04 要求“改 disposition 且重算摘要”的伪造产物在 V4 命中 `IDENTITY_CONFLICT`；
   若 V1 重算处置表，就会提前以 `INVALID_INPUT_STRUCTURE` 拒绝，改变冻结阶段语义。
   替代方案：V1 全面重算。未采用原因：与 AC-04 的 V4 期望冲突。
   风险：处置表正确性由 X15 的执行路径与 AC-10 端到端用例保证。
6. **决策：`method_configuration.artifact_schema_version` 在两种产物里都保持
   `M4_BOUNDED_EXECUTION_ARTIFACT_V1`，产物级 schema 版本由顶层字段区分。**
   原因：设计 10.1 对被复用的 `MethodConfigurationV1` 字段注释即为该常量。
   风险：派遣产物的方法配置不显示自己的 schema 名；已在 acceptance 文档记为解释项。
7. **决策：派遣产物的 `method_configuration.block_length` 记为 `None`。**
   原因：该字段定义为“实际使用的块长”，派遣不执行重采样，写理论值会把“未执行”谎报为“已执行”。
   风险：与主产物同名字段不同，已在 acceptance 文档记为解释项。

## 实际操作

1. 读取 `D:/量化分析/AGENTS.md`、`agent/agent.md`、Goal 契约、两份冻结设计文档，并独立核验
   branch/HEAD/main/origin/main/worktrees/stash/DB SHA256（见“开始前状态”）。
2. 读取将复用的既有接口：`mechanism/planning/matrix.py`、`planning/compiler.py`、
   `datasets/synthetic.py`、`hypothesis_config.py`、`model_digest.py`、`contract_compiler.py`，
   以及三份既有 fixture 测试、`tests/conftest.py`、`README.md`、`pyproject.toml`。
3. 基线验证：上游 M4 回归组实测 `252 passed, 3 errors`，exit 1（3 个 error 均为已知
   `tmp_path` `WinError 5` setup 失败）。
4. 沙箱诊断（只读探针）：`os.mkdir(path, 0o700)` 后 `os.scandir` 与 `rmdir` 均被拒绝；
   `0o777/0o755/0o750` 正常；`--basetemp=tmp/pytest-basetemp`（先由 PowerShell 以默认权限创建）
   仍失败，因为 pytest 会用 `mode=0o700` 重建 basetemp 与编号子目录
   （`_pytest/tmpdir.py:139,141,158`、`_pytest/pathlib.py:224`）。未改任何测试。
5. 新增 `src/ashare_research/mechanism/execution/bounded.py`（约 2000 行）与
   `execution/__init__.py`（8 入口 + 常量 + 冻结 dataclass + `ExecutionError`）。
6. 新增 `tests/test_m4_bounded_execution.py`（49 个用例）：负例先行（X2 来源篡改、矩阵伪造、
   X8 秩门、X7 数值门、R7 派遣门、签名层 holdout），再正例（AC-01 结构、AC-08 端点与序号、
   AC-10 处置表、AC-12 派遣、AC-14/15 不变性与字节复现、AC-16 嵌套变异、AC-17 来源与禁止内容、
   AC-18 两层身份、AC-19 严格复制/禁用/不降级）。
7. 同步 `README.md`（能力表 M4-A.2E 行、路线图 Milestone 4、授权措辞、新增接口小节）、
   `tests/test_project_entry.py`（能力断言）、`tests/test_m4_stage4p_governance.py`
   （路线图状态断言一处）。
8. 逐条执行 Goal 验证命令并记录真实退出码（见下）。
9. 写 `acceptance/2026-09-12_m4_bounded_execution_implementation.md`，更新本记录。
10. 尝试显式路径 `git add` + 范围化本地提交：`git add` 被沙箱拒绝（git 目录在工作区之外），
    一次性升级重试被拒且无审批通道；未使用任何绕过手段（见“阻塞条件”）。

## 数据与方法说明

- 数据来源：全部为合成 fixture，无 provider、无网络、无数据库、无真实行情、无 holdout。
- 合成 fixture：基础 fixture 沿用既有 `_document()`/`_compiled()` 与 `_inputs()`/`_bound()`；
  正例在**同一合同语义**下改用 24 个合成交易日（2020-01-02..2020-01-25，开发期内），
  2 个控制项（k=5），因子取值按奇偶分别落在阈值两侧（`LTE -0.0100`），控制项为
  0.005·(i+1) 与 0.002·(i²+1)，从而列满秩且任意重采样窗口同时包含 0/1 指示值。
- 响应表按用途构造：`noisy`（真实残差，用于 bootstrap 端点与复现性）、`positive`/`negative`
  （精确线性 DGP，主效应恰为 ±0.02）、`zero`（响应恒为 0，lstsq 返回精确 0.0 系数与端点）、
  `tiny`（1e-12 正效应，用于检验无容差比较）。
- 未使用任何既有 M3 模块、`statsmodels` 或 `pandas`；估计器为 `numpy.linalg.lstsq`，
  RNG 为 `numpy.random.PCG64`，随机性只来自计划冻结的 `seed`。
- 数值期望仅限冻结契约算术（块长、区间序号、次序统计量端点）与处置词；
  没有对系数大小做任何期望断言。

## 验证

（真实命令与退出码；`$env:PYTHONPATH = src`，解释器 `D:/量化分析-m4a2i/.venv/Scripts/python.exe`）

| # | 命令 | 退出码 | 结果 |
| --- | --- | --- | --- |
| 1 | `pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py` | 0 | `49 passed` |
| 2 | `pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 0 | `15 passed` |
| 3 | `pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | 1 | `252 passed, 3 errors`（与实现前基线逐字相同；3 个 error 为已知 sandbox `tmp_path` `0o700` 拒绝） |
| 4 | `ruff check src/ashare_research/mechanism/execution tests/test_m4_bounded_execution.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 0 | `All checks passed!` |
| 5 | `git diff --check` / `git diff --cached --check` | 0 / 0 | 均干净 |
| 6 | `git status --short --branch` | 0 | 仅白名单路径（3 modified + 4 untracked 条目） |
| 7 | `git rev-parse HEAD origin/main refs/stash` | 0 | `070a26a…`（HEAD 未变，提交被阻塞） / `f34adcb…` / `cb568ef…` |
| 8 | `git worktree list --porcelain` | 0 | 15 个 worktree，全部保留 |
| 9 | `git stash list` | 0 | 仅既有 `stash@{0}` |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | 0 | `f34adcb17c9995392690a1df6bb5a10ee102eb09`（live） |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | 0 | `[]` |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | 0 | `4A71D3C7…E2FCE6` = 保护值（仅哈希） |
| 13 | `git -C D:/量化分析 rev-parse HEAD` | 0 | `3679b1bac7a1634c6452784a4d8f6d139966f222` = 保护值 |
| 14 | 显式 `--basetemp=tmp/pytest-basetemp` 复现第 3 条 | 1 | `252 passed, 3 errors`——显式 basetemp **不能**规避，原因见沙箱诊断 |
| 15 | 变更路径白名单 + 禁止导入 + Markdown（UTF-8/BOM/CR/TAB/行尾空白/结尾换行/冲突标记）与仓库相对链接审计 | 0 | 白名单相符；`bounded.py` 无禁止导入/IO；7 个 Markdown 文件 `issues=NONE`，链接 0 缺失 |

`git diff --check`、`git status` 等最终状态以提交后记录为准（见“最终Git状态”）。
第 3 条命令**不**声称通过；3 个 error 逐字保留在 acceptance 文档中。

## 结果

- 已完成：8 个公开入口、X1–X16 / R0–R9 / V1–V4、冻结常量与错误码、两种不可变产物与规范序列化、
  两层身份与禁止内容门、AC-01..AC-19 覆盖（49 个非跳过用例）、README 与两处允许测试的同步、
  record/acceptance 文档。
- 未完成：契约要求的范围化本地提交（沙箱拒绝写 `D:/量化分析/.git`，升级重试无审批通道）；
  这是唯一未满足项。
- 与原计划的差异：AC-05c/5d、AC-06a–6d、AC-11c、部分 X5/X6/X14 门在合法来源链下由上游
  校验先拒绝，属设计预期的 defense-in-depth；验收改用“上游拒绝 + 结构/顺序断言”，
  未伪造命中（详见 acceptance“Deviations”）。
- 是否可用：实现可用（仅合成 fixture）；合成就绪不等于任何真实研究授权。
- 条件通过：无。

## 遗留问题

1. 设计 10.5 要求“两个产物都携带 `interpretation_boundary`”，但 10.1/10.2 的冻结字段表没有
   给派遣产物任何可承载字段；实现按冻结字段表处理（主产物承载字面量，派遣产物以
   `provenance.provenance_class` 标识合成来源），已作为设计措辞不一致上报，未擅自新增字段。
2. 设计 8.4 “该词不出现在 `DISPOSITIONS` 里”仅对 `FAIL` 精确成立（`INCONCLUSIVE` 同时是
   质量失败词与处置词）；实现按“载体分离”处理并记录。
3. sandbox 的 `0o700` 目录拒绝会让上游 3 个 `tmp_path` 用例在 setup 阶段失败；这是环境限制，
   需要更宽权限的 runner 才能变绿，未修改任何测试。
4. 字节复现只在同一 `numeric_runtime`（numpy 2.5.3）下声明；跨 BLAS/numpy 版本差异通过产物中的
   `numeric_runtime` 可检测但不可阻止。

## 下一步建议

由 Codex 独立验收：核对真实 branch/HEAD、提交与 diff、全部变更与未跟踪文件、测试证据、
worktree/stash、保护基线与数据库哈希、live 远端状态、Goal 合规性与验收证据。合入、推送、
开 PR 与 M4-B/真实数据执行均需用户另行明确授权。

## 最终文件变更

```text
src/ashare_research/mechanism/execution/__init__.py                          新增
src/ashare_research/mechanism/execution/bounded.py                           新增
tests/test_m4_bounded_execution.py                                           新增（49 用例）
README.md                                                                    同步（能力表/路线图/授权/新接口小节）
tests/test_project_entry.py                                                  同步（能力断言）
tests/test_m4_stage4p_governance.py                                          同步（路线图状态断言一处）
agent/record/2026-09-12_01_m4-bounded-execution-implementation.md            新增（本文件）
acceptance/2026-09-12_m4_bounded_execution_implementation.md                 新增
```

未修改：任何 `planning/**`、`datasets/**`、顶层 `mechanism/*.py`、`reports/**`、北极星文档、
依赖、工作流、配置、既有 schema/摘要算法、其它测试、数据库与 stash。

## 最终Git状态

- 当前分支：`codex/m4-bounded-execution-implementation`
- 基线提交（= 当前 HEAD）：`070a26ad967016580d56f046d73c52f3d41010e9`
- 交付提交：**未能创建**（见“阻塞条件”）。全部白名单路径以已验证的工作树改动存在。
- 是否创建提交或 Tag：否（`git add` 被沙箱拒绝；升级重试被拒且无审批通道）
- 是否执行推送：否（未推送、未开 PR、未合并、未进入下一阶段）

## 阻塞条件（唯一未满足项）

Goal 的 “Commit and push requirements” 要求 Harness 以显式路径暂存创建范围化本地提交。
验证后执行的确切命令被拒绝：

```text
$ git add -- src/ashare_research/mechanism/execution/__init__.py \
    src/ashare_research/mechanism/execution/bounded.py tests/test_m4_bounded_execution.py \
    README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py \
    agent/record/2026-09-12_01_m4-bounded-execution-implementation.md \
    acceptance/2026-09-12_m4_bounded_execution_implementation.md
fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-executor-implementation/index.lock': Permission denied
[exit code: 128]
```

实测权限探针：

```text
D:/量化分析/.git/worktrees/量化分析-m4-executor-implementation/.dsh_write_probe -> DENIED (UnauthorizedAccessException)
D:/量化分析/.git/.dsh_write_probe                                              -> DENIED (UnauthorizedAccessException)
D:/量化分析-m4-executor-implementation/.dsh_write_probe                       -> WRITABLE
index.lock（失败后）                                                            -> 不存在（无残留）
```

同一命令的一次性升级重试被拒绝：`sandbox escalation to "danger-full-access" requires approval,
but no approval channel is available`。按运行时规则该拒绝为最终结果，因此**未尝试任何绕过**：
没有备用 `GIT_INDEX_FILE`、没有备用 git-dir、没有重建仓库、没有路径别名、没有 `git add -A`。
`git commit --only <paths>` 也通过标准 CLI 尝试过一次，对 5 个未跟踪路径不可行（尚未被 git 知晓），
属同一被阻塞的暂存步骤。

结论：内容验收标准全部满足，唯一未满足项是契约要求的本地提交；因此 Harness 侧结论为
`BLOCKED`，`HEAD` 仍为基线 `070a26ad967016580d56f046d73c52f3d41010e9`。
解除命令（需在可写 `D:/量化分析/.git` 的 shell 中由 Codex 执行）：

```powershell
cd D:/量化分析-m4-executor-implementation
git add -- src/ashare_research/mechanism/execution/__init__.py `
    src/ashare_research/mechanism/execution/bounded.py `
    tests/test_m4_bounded_execution.py `
    README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py `
    agent/record/2026-09-12_01_m4-bounded-execution-implementation.md `
    acceptance/2026-09-12_m4_bounded_execution_implementation.md
git diff --cached --check
git commit -m "feat: implement synthetic-only M4 bounded execution (M4-A.2E)"
git status --short --branch
git rev-parse HEAD origin/main refs/stash
```

## Codex 独立复核与解除

Harness 结束后，Codex 在可写共享 Git 元数据的宿主 shell 中独立检查真实分支、HEAD、全部
changed/untracked 路径、实现与测试 diff、worktree、stash、数据库哈希及 live remote。Codex
实际重跑得到：新增实现测试 `49 passed`，入口/治理测试 `15 passed`，上游 M4 回归
`255 passed`；ruff 与 diff 检查通过。Harness 的三个 `tmp_path` setup error 在宿主环境没有
复现，因此确认为工具沙箱环境限制。

Codex 对设计 10.5 与 10.1/10.2 的冲突采用冻结字段表及 AC-18f 作为控制要求：派遣产物不得
新增 `evidence` 或 float 统计块，也不擅自增加 schema 字段；其解释边界由进入摘要的
`SYNTHETIC_TEST_ONLY` provenance 及三个严格状态位承载。该解释不授权真实数据、holdout 或
M4-B。Codex 仅显式暂存本 Goal 白名单路径并创建范围化本地提交；提交哈希在提交完成后的
外部证据包报告。Harness 的 `BLOCKED` 仅作为历史工具状态保留，Codex 最终 verdict 为
`PASS`。未 push、未开 PR、未合并、未启动下一阶段。
