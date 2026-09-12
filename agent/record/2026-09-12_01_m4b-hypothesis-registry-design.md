# 工作记录：M4-B 理论/假设注册表设计（design-only）

## 基本信息

- 日期：2026-09-12
- Agent：DeepSeek Harness（executor；reviewer = Codex）
- 当前分支：`codex/m4b-hypothesis-registry-design`
- 基线（= 当前 HEAD）：`0de39577f164c095c4bf4f9c3b742fbbee50745d`（Codex 的 Goal 契约提交）
- 任务来源：`agent/goals/2026-09-12_m4b_hypothesis_registry_design.md`（Codex 所有，已在基线提交）
- 对应模块：机制验证（M4-B Theory / Hypothesis Registry；**仅设计**）
- 状态：`blocked`——设计与验收内容已按本会话实测独立验证完成；Goal 要求的范围化本地提交被
  sandbox 拒绝（见"验证"#21、"结果"与"遗留问题"）
- 会话说明：本记录最初由**上一个 DSH 会话**创建，该会话意外中断，留下了两份设计文档、`README.md`
  改动、本记录的草稿（含大量"待回填"与未经验证的完成声明），且**没有**创建验收文档。
  本会话（接续会话）独立重跑了全部 Goal 验证命令、用只读审计脚本核对设计与验收场景的一致性，
  发现并修正了草稿中的数值/引用不一致与两处"实现期再定"的二选一错误码，并按实测重写了本记录。
  **本记录中一切结论以本会话实跑证据为准；草稿中无法复核的历史声明一律标注为不可复核。**

## 任务目标

按已冻结的 Stage4P M4-B 前置合同
（`reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json`，
`status=FROZEN_PREFLIGHT_ONLY`、`implementation_status=NOT_STARTED`、
`real_registry_dataset_authorized=false`、`not_implementation=true`），冻结 M4-B 最小切片的
**可实现设计**与**验收场景**：来源可追溯的候选元数据、规范身份、严格校验与 fail-closed 状态机。
本任务只交付设计与文档，**不实现** registry、不创建真实候选数据集、不获取文献、不授权真实假设执行。

## 范围

白名单（Goal "Allowed scope" 路径 1–8）：

1. `agent/goals/2026-09-12_m4b_hypothesis_registry_design.md`（Codex 契约，**未改**）
2. `docs/m4b_hypothesis_registry_design_v1.md`（新增，规范设计；本会话修正 7 处）
3. `docs/m4b_hypothesis_registry_acceptance_cases_v1.md`（新增，规范验收场景；本会话修正 3 处）
4. `agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md`（本文件，本会话重写）
5. `acceptance/2026-09-12_m4b_hypothesis_registry_design.md`（新增，本会话创建）
6. `README.md`（仅同步因本次设计冻结而过时的当前能力/路线图/授权措辞）
7. `tests/test_project_entry.py`（**仅在必须同步硬编码 README 状态时**；本次未改）
8. `tests/test_m4_stage4p_governance.py`（**仅在必须同步规范 README 状态时**；本次未改）

## 非目标

不修改 `src/**`、`reports/**`、`config/**`、`data/**`、`events/**`、依赖、工作流、北极星文档、
既有 M4 设计/验收文档、fixture 或白名单外任何测试；不新增 `knowledge/`、
`src/ashare_research/m4` 或顶层 `src/ashare_research/mechanism/*.py`；不实现 M4-B、不采集真实候选、
不下载论文或教材内容、不构建真实注册数据集、不扫描异常、不排序回测、不自动提升候选、
不调用 provider、不读取数据库内容或真实行情、不接触 holdout、不运行统计执行；
不弱化或删除测试；不推送、不开 PR、不合并、不进入实现、不递归委派。

## 开始前状态（本会话实测，2026-09-12）

- `git status --porcelain -uall`：` M README.md`；三个白名单未跟踪文件
  （`docs/m4b_hypothesis_registry_design_v1.md`、
  `docs/m4b_hypothesis_registry_acceptance_cases_v1.md`、
  `agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md`）；
  `acceptance/2026-09-12_m4b_hypothesis_registry_design.md` **不存在**（草稿记录了它"已编写"，
  与工作树不符；本会话已创建）。
- `git rev-parse --abbrev-ref HEAD`：`codex/m4b-hypothesis-registry-design`。
- `git rev-parse HEAD`：`0de39577f164c095c4bf4f9c3b742fbbee50745d`（= Goal 契约提交；
  相对 `origin/main` ahead 1）。
- `git rev-parse origin/main`：`1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd`（PR #13 合并点）。
- live GitHub `main`（`gh api .../branches/main`）：同一 SHA；`gh pr list --state open` = `[]`。
- `git worktree list --porcelain`：**16** 个 worktree（含本工作树），全部保留、未清理。
  （草稿写"15 个"，与实测不符，已更正。）
- `git stash list`：仅既有 `stash@{0}`
  `On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4 record edit before Stage 1C`；
  `refs/stash` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`。
- 保护 M2 HEAD：`git -C 'D:/量化分析' rev-parse HEAD` =
  `3679b1bac7a1634c6452784a4d8f6d139966f222`。
- DB SHA256：`Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` =
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`
  （**仅计算文件哈希，未打开数据库**）。
- `Test-Path src/ashare_research/m4` = `False`；`Test-Path knowledge` = `False`。
- 既有 mechanism 子包实测：`datasets/`、`execution/`、`planning/`（另有 `__pycache__/`）；
  `registry/` **不存在**。
- 解释器：`D:/量化分析-m4a2i/.venv/Scripts/python.exe`（Goal 指定的共享已验证解释器）。
- 本会话新测环境限制（用于独立归因，不是草稿声明的照抄）：sandbox 拒绝对 `0o700` 目录做
  `os.scandir` 枚举——在**工作树内**用 `tempfile.mkdtemp` 创建目录并 `chmod 0o700` 后，
  `os.scandir` 同样抛 `PermissionError: [WinError 5]`；而会话临时根目录本身可枚举。
  pytest 的 `tmp_path` basetemp 以 `0o700` 创建，因此上游 M4 回归组出现 3 个 setup 阶段 error
  （实测 `252 passed, 3 errors`，exit 1），详见"验证"#3。
- 已知环境限制（本次实测）：sandbox 拒绝写入链接 git 元数据目录
  `D:/量化分析/.git/worktrees/量化分析-m4b-registry-design/`（`UnauthorizedAccessException`），
  因此 `git add` 无法创建 `index.lock`，范围化本地提交被阻塞。

## 实施计划（按本会话实际执行顺序）

1. 读完整 Goal 契约（160 行），核对分支/HEAD/worktree/stash/`origin/main`/live GitHub/保护 DB
   哈希/M2 HEAD/冻结前置合同，全部以实测为准。
2. 只读复核将复用/引用的既有真实接口：`canonical_digest`、序列化约定、`_IDENTIFIER_RE`、
   `RESTRICTED_RESEARCH_OUTPUT_KEYS`、`FORBIDDEN_KEYS`、`MatrixError`/`AdapterError`/`ExecutionError`、
   `EvidenceDirection`、`FrozenJSON*`/`canonical_decimal`。
3. 用只读审计脚本机械核对两份设计文档：合同引文、26 键、22 身份承载字段、12 状态顺序、
   20 条合法边、禁止键超集、13 个公开入口、AC 索引/正文一致性、Markdown 卫生与相对链接。
4. 修正草稿中的真实缺陷（见"决策记录"与"实际操作"）。
5. 逐条独立执行 Goal 的全部验证命令，记录真实退出码与输出。
6. 创建 `acceptance/2026-09-12_m4b_hypothesis_registry_design.md`，写入实测结果与阻塞条件。
7. 按实测重写本记录的结果/验证/Git 状态。
8. 尝试范围化暂存与本地提交；被拒绝则保持未提交并报告确切阻塞。

## 决策记录

1. **决策：记录在 19 个冻结最小字段之上新增 5 个字段，再加 2 个派生摘要字段，共 26 键。**
   新增为 `source_version`、`source_notes`（对应合同 `required_identity` 的 "version"、"notes"）、
   记录级 `schema_version`、`hypothesis_version`、`state_history`；`identity_digest`、
   `record_digest` 为派生字段。原因：合同 `literature_provenance.required_identity` 要求
   `["source identity","citation","version","source type","notes"]`，其中 version 与 notes 在
   `minimum_fields` 中没有对应字段。替代方案（把 version/notes 折进
   `citation_or_source_identity`）会让"版本未知"与"引用未知"不可区分，未采用。
   本会话更正了草稿的算术表述（曾写作"19 + 3"、"19 + 5 → 26"，与 §4.2 的 26 行表不符）。
2. **决策：身份划分为 `identity_digest`（22 个身份承载字段）与 `record_digest`（含 status 与
   `state_history`）。**
   实测：26 键 − `status` − `state_history` − `identity_digest` − `record_digest` = **22**，
   与 §4.3 枚举集合逐一相等。草稿四处写作"21"，与自身枚举矛盾；本会话已更正为 22。
   原因与替代方案同前：两个摘要互不覆盖，使"改状态不改身份""改来源必改身份"可机械检出。
3. **决策：`source_notes` 属于身份承载字段（注册后不可追加）。** 备注是 provenance 的一部分；
   可变会让来源信息被静默改写。更正来源需提升 `hypothesis_version`。
4. **决策：十二状态机冻结为 20 条合法边，矩阵为唯一真源。**
   本会话机械展开 §7.2 矩阵逐格统计：**恰好 20 条**，与 §7.2 分组列举（4+3+5+1+6+1）逐边相等；
   `S9/S10/S11` 无出边；`ESTABLISHED` 唯一入边 `S8→S10`；`DEFERRED` 唯一出边 `→S4`。
   草稿称"初稿文字枚举 16 条后被发现并更正"——该历史过程**无法从当前文件复核**（无版本记录），
   本记录只保留实测结论，不把不可复核的过程声明当作证据。
5. **决策：`ESTABLISHED` 门只检查"登记完备性"，不检查统计有效性。**
   合同 `evidence_boundary` 的落点是登记项与授权身份；在 registry 内读取统计结果会直接违反
   Goal 的"机械分离"要求。已在设计 7.5 与验收 AC-08 明确"登记齐备 ≠ 已被证明 ≠ 可交易"（风险 R3）。
6. **决策：新增 `FORBIDDEN_OUTCOME_FIELD` / `FORBIDDEN_ENVIRONMENT_FIELD` 集合必须**包含**
   既有 `RESTRICTED_RESEARCH_OUTPUT_KEYS` 与 `FORBIDDEN_KEYS` 的全部成员。**
   本会话实测：`RESTRICTED_RESEARCH_OUTPUT_KEYS` 12 个成员与设计 §9.1 的"既有冻结集合"块**完全相等**；
   设计 §9.2 对 `bounded.py::FORBIDDEN_KEYS` 的 24 个成员是**超集**（无遗漏）。
7. **决策：`hypothesis_id` 规则在 registry 中独立声明同一正则字面量，而不导入既有私有
   `hypothesis_config._IDENTIFIER_RE`。**
   本会话实测既有 pattern = `^[A-Za-z0-9][A-Za-z0-9_.-]*$`，与设计声明一致；设计 §11.3 的导入白名单
   刻意排除 `hypothesis_config`（私有符号 + 避免把配置解析栈拉进纯元数据层）。漂移风险记入 R5，
   并要求实现阶段机械断言两侧 pattern 相等（验收 AC-22 第 7 项）。
8. **决策：不使用通用正则拒绝"带数字的结论性文本"。**
   设计 §9.3 只对**键**做通用机械拒绝；对自由文本做 `p=...`/`t=...` 之类正则误伤率高
   （`target_horizon`、`source_version`、`known_replications` 含年份/版次），且会制造"假安全感"。
   残余风险 R2 明确记为需人工评审，不得被描述为"已被机械阻止"。
9. **决策：本次**不改**两个条件测试文件。**
   原因：README 同步保留了 `M4-B NOT STARTED`、`real hypothesis execution NOT AUTHORIZED`、
   `没有通用研究执行器`、`holdout` 等被断言字符串；本会话实跑 #1 得 `15 passed`、#4 得
   `All checks passed!`，证明无需改动（Goal 对这两条路径的措辞是 "only if required"）。
10. **决策（本会话新增）：冻结草稿中留给"实现阶段再定"的两处二选一错误码。**
    - AC-11(11b)（同身份键、内容不同）：冻结为 `PROVENANCE_REWRITE`（V12）；同摘要的重复登记为
      `DUPLICATE_HYPOTHESIS_ID`。设计 §4.4/§8.1(V12 内部顺序)/§8.2/T5 同步写明"同一身份键只报一个码"。
    - AC-17(17e)（执行期转换 `evidence_kind` 缺失/null）：冻结为 `ILLEGAL_STATE_TRANSITION`
      （前置条件 P6–P8 未满足；不新增错误码），写入设计 §7.7。
    原因：Goal 的验收标准要求"不留下实现关键歧义"，而草稿的两处"按实现阶段冻结的单一选择"
    正是把实现关键选择留给未来，属于设计缺陷。

## 实际操作（本会话实测顺序）

1. 读取 Goal 契约全文并按 `CLAUDE.md` 核验真实基线（分支、HEAD、worktree 数量、stash、
   `origin/main`、live GitHub main、开放 PR、保护 DB 哈希、M2 HEAD、`Test-Path` 两项）。
2. 只读复核冻结前置合同全文（54 行）并用 `json.loads` 与设计 §2.1 引文块做深度相等比较
   ——首次比较**不相等**：引文缺少顶层 `purpose` 键；已补回，复测相等（12 个顶层键）。
3. 读取并复核两份设计文档全文（设计 1091 行、验收场景 569 行）、`README.md` diff、
   本记录草稿（259 行）与既有真实接口源码。
4. 编写并运行只读审计脚本（位于会话临时目录，不写入工作树），机械核对：
   合同引文、§4.1↔§4.2 键集（26/26 相等）、身份承载字段数（22）、§7.1 状态顺序与合同一致、
   §7.2 矩阵展开（20 条，与分组列举逐边相等）、禁止键超集关系、
   `_IDENTIFIER_RE`/`canonical_digest`/序列化/异常/`EvidenceDirection` 声明为真、
   AC 索引与正文标题集合一致（22/22）、每个 AC 小节含四要素、
   Markdown 卫生（BOM/CR/结尾换行/行尾空白/冲突标记/围栏平衡）与仓内相对链接解析。
5. 依据审计结果修正白名单路径 2–3 中的 7 类缺陷（详见验收文档"Corrections applied"）：
   合同引文补 `purpose`；21→22；§1.1 与 §2.1/§4.2/AC §0.3 的 19+5+2=26 算术；
   §5.1 S8 的可空位置指向由 §4.1 改为 §7.7；§3 补 `CITATION_MAX_LEN`/`SOURCE_VERSION_MAX_LEN`/
   `TARGET_HORIZON_MAX_LEN`；冻结 AC-11(11b) 与 AC-17(17e) 的单一错误码并同步设计 §4.4/§7.7/§8.1/§8.2/T5。
6. 逐条独立执行 Goal 的全部 21 项验证命令（含 pytest 三组、ruff、git 检查、GitHub/哈希/路径检查、
   Markdown 卫生与一致性核对），记录真实退出码与输出。
7. 为 #3 的 3 个 `tmp_path` setup error 做独立归因探针（工作树内 `0o700` 目录的 `os.scandir`
   复现同一 `PermissionError`；会话临时根目录本身可枚举）——见"验证"#3 与"遗留问题"。
8. 创建 `acceptance/2026-09-12_m4b_hypothesis_registry_design.md`，写入实测结果、修正清单、
   白名单核对、阻塞条件与偏差披露。
9. 按实测重写本记录（本文件）。
10. 尝试范围化暂存与本地提交：`git add -- <5 个白名单路径>` 与
    `git commit -m "docs: freeze M4-B hypothesis registry design and acceptance cases"` 均被拒
    （`index.lock: Permission denied`，exit 128）；一次性升级重试被拒
    （无审批通道）。未尝试任何绕过；文件保持未提交，`index.lock` 无残留。

## 数据与方法说明

本任务**不涉及**数据研究：没有访问数据库内容、provider、真实行情、holdout 或任何真实候选；
没有下载或采集文献/教材内容；没有计算任何系数、区间、p 值、秩或处置。
唯一与数据相关的操作是对 `D:/量化分析/data/research.duckdb` 计算**文件** SHA256（只读哈希，
未打开数据库、未查询任何表）。设计文档中的示例全部是 `SYNTHETIC_EXAMPLE_*` 示意文本，
摘要位置一律为 `<64 hex>` 占位符（不得写死数值，否则文档会变成伪证据）。

## 验证

全部命令在本工作树 `D:/量化分析-m4b-registry-design` 执行，
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`，
解释器 `D:/量化分析-m4a2i/.venv/Scripts/python.exe`，并加 `-p no:cacheprovider` 禁用 pytest 缓存。
每条命令独立执行，退出码与关键输出如下（真实实测，未隐藏失败）。

| # | 命令 | 退出码 | 真实结果 |
| --- | --- | --- | --- |
| 1 | `pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 0 | `15 passed in 0.12s` |
| 2 | `pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py` | 0 | `49 passed in 62.51s (0:01:02)` |
| 3 | `pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | 1 | `252 passed, 3 errors in 13.22s`；3 个 error 均为 `tmp_path` fixture setup 的 `PermissionError: [WinError 5]`（会话临时基目录 `...\dsh-WpZARg\pytest-of-dlam12138`），无断言失败；受影响用例：`test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance`、`test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence`、`test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags` |
| 4 | `ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 0 | `All checks passed!` |
| 5 | `git diff --check` | 0 | 无输出 |
| 6 | `git diff --cached --check` | 0 | 无输出（索引为空） |
| 7 | `git status --short --branch` | 0 | `## codex/m4b-hypothesis-registry-design...origin/main [ahead 1]`、` M README.md`、3 个白名单 `??` 文件；另有一条 `.dsh-probe` 权限告警（见"遗留问题"） |
| 8 | `git rev-parse HEAD origin/main refs/stash` | 0 | `0de39577f164c095c4bf4f9c3b742fbbee50745d` / `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd` / `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` |
| 9 | `git worktree list --porcelain` | 0 | 16 个 worktree，全部保留 |
| 10 | `git stash list` | 0 | 仅既有 `stash@{0}` |
| 11 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | 0 | `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd`（live） |
| 12 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | 0 | `[]` |
| 13 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | n/a（cmdlet，无错误） | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` |
| 14 | `git -C 'D:/量化分析' rev-parse HEAD` | 0 | `3679b1bac7a1634c6452784a4d8f6d139966f222` |
| 15 | `git diff --name-only HEAD -- src reports config data events` | 0 | 空输出 |
| 16 | `Test-Path src/ashare_research/m4` | n/a | `False` |
| 17 | `Test-Path knowledge` | n/a | `False` |
| 18 | Markdown 卫生审计（BOM/CR/结尾换行/行尾空白/冲突标记/围栏平衡） | 0 | 设计、验收场景、README、本记录、验收文档均 `issues= NONE` |
| 19 | 仓内相对 Markdown 链接解析 | 0 | 全部解析成功（含设计/验收场景 → 验收文档的相对链接） |
| 20 | AC 索引 ↔ 正文一致性（`### AC-nn` 与索引表） | 0 | 索引 22、正文 22、ID 集合相等、无重复、无孤儿；每个 AC 小节含输入/预期/阶段/授权解释四要素 |
| 21 | `git add -- <5 个白名单路径>`（最终完整路径集） | 128 | `fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4b-registry-design/index.lock': Permission denied` |
| 22 | `git commit -m "docs: freeze M4-B hypothesis registry design and acceptance cases"` | 128 | 同一 `index.lock: Permission denied`；失败后 `index.lock` 不存在（无残留） |

最终状态复跑（写入本记录与验收文档之后、`README.md`/`src`/`reports`/测试均未再改动）：

```text
#1  15 passed in 0.11s                      (exit 0)
#2  49 passed in 69.34s                     (exit 0)
#3  252 passed, 3 errors in 18.94s          (exit 1，同样 3 个 tmp_path setup error)
#4  All checks passed!                      (exit 0)
```

补充证据（非 Goal 命令，只读/一次性探针）：
- `json.loads` 深度比较：设计 §2.1 引文块与
  `reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json` **相等**（修正后）。
- 矩阵展开：§7.2 矩阵 `✅` 逐格统计 = 20 条，与分组列举逐边相等；`S9/S10/S11` 无出边。
- 集合包含：`RESTRICTED_RESEARCH_OUTPUT_KEYS`（12）与设计 §9.1 既有集合块相等；
  `FORBIDDEN_KEYS`（24）是 §9.2 的子集。
- 环境归因探针：工作树内 `0o700` 目录 `os.scandir` → `PermissionError [WinError 5]`；
  会话临时根目录 `os.scandir` → 正常列出 `['pytest-of-dlam12138']`。
- 链接 git 目录写入探针：`.dsh_write_probe` → `UnauthorizedAccessException`（DENIED）；
  `git add` 失败后 `index.lock` **不存在**（无残留）。

## 结果

- 交付物齐备且经本会话独立验证：设计（16 节，覆盖 Goal 的 10 项必需设计行为）、验收场景
  （AC-01..AC-22，每例含输入/预期结果或稳定错误码/验证阶段/授权解释）、`README.md` 同步
  （保留 `M4-B NOT STARTED`、`real hypothesis execution NOT AUTHORIZED` 等语义）、本记录、验收文档。
- 独立审计发现并修正 7 类真实缺陷（合同引文缺 `purpose`；21↔22 身份字段数；三处 19+5+2=26
  算术；S8 的错误指向；冻结常量表缺 3 个长度常量；AC-11(11b) 与 AC-17(17e) 的二选一错误码）。
  修正均在白名单路径 2–3 内，未触碰 `src/**`、`reports/**` 或任何保护性断言。
- Goal 的 21 项验证命令全部执行并记录真实退出码：19 项 exit 0；#3 为 exit 1（3 个
  `tmp_path` setup error，已独立归因为 sandbox 的 `0o700` 枚举限制，非测试失败）；
  #21/#22 为 exit 128（沙箱阻塞暂存与提交）。
- **唯一未满足的 Goal 要求是"范围化本地提交"**：`git add` 无法创建 `index.lock`，
  升级重试无审批通道；按用户指示保持全部文件**未提交**并报告确切阻塞。
- 未 push、未开 PR、未合并、未进入实现阶段。M4-B 仍为 `NOT_STARTED`，真实假设执行仍未授权。

## 遗留问题

1. **交付提交缺失（阻塞项）**：见"验证"#21/#22 与验收文档"Blocking condition"。
   解除命令（需在可写 `D:/量化分析/.git` 的宿主 shell 执行，例如 Codex）：

   ```powershell
   cd D:/量化分析-m4b-registry-design
   git add -- README.md `
       docs/m4b_hypothesis_registry_design_v1.md `
       docs/m4b_hypothesis_registry_acceptance_cases_v1.md `
       agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md `
       acceptance/2026-09-12_m4b_hypothesis_registry_design.md
   git diff --cached --check
   git commit -m "docs: freeze M4-B hypothesis registry design and acceptance cases"
   git status --short --branch
   git rev-parse HEAD origin/main refs/stash
   ```

2. **本会话引入的工作树残留**：为独立归因 #3，本会话在工作树内创建了
   `.dsh-probe/tmp39hvuzdy`（空目录、未跟踪、未被 `.gitignore` 覆盖）。sandbox 拒绝枚举与删除该
   `0o700` 目录（`Remove-Item`/`rd /s /q` 均 access denied；升级重试无审批通道），因此无法自行清理。
   该目录不含文件、不进入任何提交，仅在 `git status` 中产生
   `warning: could not open directory '.dsh-probe/tmp39hvuzdy/': Permission denied`。
   清理命令（需完全权限 shell）：`Remove-Item -Recurse -Force 'D:/量化分析-m4b-registry-design/.dsh-probe'`。
   此为必须披露的真实偏差，不做隐藏。
3. **上游 M4 回归组的 3 个 `tmp_path` setup error** 在本 sandbox 中不可消除；本记录不声称该组
   全绿。此前 M4-A.2E 记录报告过同一失败模式（宿主端 Codex 复现为 `255 passed`），但本会话
   **未**在宿主端复现，故只记录本沙箱实测。
4. **不可复核的历史声明已作废**：草稿中"转换矩阵初稿 16 条后更正为 20 条"的过程声明、
   以及"验收文档已编写""验证全部完成"等完成声明，均无本会话证据支撑；已按实测重写，
   仅保留可复核结论（矩阵实测 20 条）。
5. 设计阶段残余风险 R1–R8 仍未决（禁止来源词表未冻结、自由文本结论无法机械阻止、
   `ESTABLISHED` 门只做登记完备性、矩阵/边集合需实现期机器核对、正则漂移、规模上限语义、
   持久化格式未冻结），属实现评审项。

## 下一步建议

1. 由 Codex 在可写共享 Git 元数据的宿主 shell 中执行上述解除命令，创建范围化本地提交，
   并独立复核分支/HEAD/diff/changed+untracked 文件/worktree/stash/DB 哈希/live remote。
2. Codex 复核时请特别确认：本会话修正的 7 类缺陷是否与冻结前置合同一致；AC-11(11b) 与
   AC-17(17e) 的单一错误码冻结是否可接受；`.dsh-probe` 残留的清理。
3. 未获明确授权前：不实现 registry、不创建真实候选、不采集文献、不推送/开 PR/合并、
   不进入 M4-B 实现或下一阶段。

## 最终文件变更

```text
docs/m4b_hypothesis_registry_design_v1.md                         新增（本会话修正 7 处）
docs/m4b_hypothesis_registry_acceptance_cases_v1.md               新增（本会话修正 3 处）
agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md      新增（本会话按实测重写）
acceptance/2026-09-12_m4b_hypothesis_registry_design.md           新增（本会话创建）
README.md                                                         修改（能力表 M4-B 行、授权段落、路线图与一行 intro）
.                                                                 残留空目录 .dsh-probe/tmp39hvuzdy（未跟踪、不在提交内，见遗留问题 2）
```

未修改：`agent/goals/2026-09-12_m4b_hypothesis_registry_design.md`、`tests/test_project_entry.py`、
`tests/test_m4_stage4p_governance.py`、任何 `src/**`、`reports/**`、`config/**`、`data/**`、
`events/**`、依赖、工作流、北极星文档、既有 M4 设计与验收文档、fixture、其它测试、数据库与 stash。

## 最终Git状态

- 当前分支：`codex/m4b-hypothesis-registry-design`
- 基线提交（= 当前 HEAD，未变）：`0de39577f164c095c4bf4f9c3b742fbbee50745d`
- 相对 `origin/main`：ahead 1（仅 Codex 的 Goal 契约提交）
- 交付提交：**未能创建**（`git add` 与 `git commit` 均 → `index.lock: Permission denied`，exit 128；
  升级重试被拒：无审批通道）。全部白名单路径以已验证的工作树改动存在。
- 索引：空（`git diff --cached --check` 无输出，无 `index.lock` 残留）
- 是否执行推送：否（未推送、未开 PR、未合并、未进入下一阶段）

## 记录诚实性说明（ordering disclosure 与中断会话披露）

1. 按 `CLAUDE.md` / `agent/agent.md` 的 record-first 规则，本记录本应在修改项目文件**之前**创建。
   上一个会话的实际顺序是：先只读复核基线与既有接口 → 编写两份规范文档 → 写本记录 →
   同步 `README.md`，但**在完成验证与验收文档之前意外中断**。本会话的顺序是：
   核实基线并与草稿对账 → 独立审计 → 修正缺陷 → 跑完验证 → 写验收文档 → 重写本记录。
   两次都**未**严格满足 record-first 的时序，这是真实的流程偏差，在此显式披露。
2. 草稿中未经验证的完成声明（"验收文档已编写""验证完成""与矩阵 16→20 的更正过程"等）
   已按本会话实测证据重写或删除；本记录只写入**本会话实际执行过**的命令与观察到的输出，
   计划、推测与实测结果分别标注。
3. 本会话自身引入的偏差（`.dsh-probe` 残留空目录、无法完成的提交）同样在"遗留问题"中
   逐条披露，未隐藏、未绕过、未通过弱化任何测试或断言来换取通过结果。

## Codex reviewer addendum

Codex 在宿主 shell 中独立复核了实际分支、HEAD、工作树 diff、未跟踪文件、保护状态与 live
remote，并重新执行了同一组测试：入口/治理 `15 passed in 0.10s`，有界执行
`49 passed in 59.93s`，五个上游 M4 回归文件 `255 passed in 8.36s`，ruff
`All checks passed!`。因此 Harness 的 `252 passed, 3 errors` 被确认是其 `tmp_path` 环境限制，
宿主结果全绿。

Codex 还确认：交付仅含 `README.md` 与四个新增设计/验收/记录文件；`src reports config data
events tests` 零 diff；`git diff --check` 通过；保护 DB 哈希、原始 M2 HEAD、stash 与
`origin/main@1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd` 均未变化。`.dsh-probe` 已被验证仅含
一个空目录；应用命令策略仍拒绝精确递归删除，故它保持未跟踪且不进入 Git 文件集。

Codex 内容评审结论为 `PASS`，并在本附录写入后由宿主 shell 创建范围化交付提交；提交哈希
只能在提交完成后的外部证据包中报告。本阶段仍停止在设计冻结，不 push、不开 PR、不合并、
不实现 registry，也不授权真实候选、文献采集、真实数据、provider、数据库、holdout 或真实
假设执行。
