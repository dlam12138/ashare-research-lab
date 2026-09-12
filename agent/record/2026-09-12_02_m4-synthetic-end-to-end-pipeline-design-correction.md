# 工作记录：M4 合成端到端流水线设计更正

## 基本信息

- 日期：2026-09-12
- Agent：DeepSeek Harness（`headless`；按 Goal 授权使用**只读**有界子代理，无递归派工）
- 当前分支：`codex/m4-synthetic-pipeline-design-correction`
- 开始提交：`d69ba05fb35fb076f7f10e1e84c29bc1e9cff0a2`（Codex 的 Goal 契约提交）
- 基线 `origin/main`：`d3fcb1967e9e7f6d3caac3e3f08ea874646f3098`（PR #16 合并点）
- 任务来源：`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`
- 对应模块：工程治理（设计规范更正；是个股价值评估 / 市场机制验证的支撑能力，不新增任何研究能力）

## 任务目标

实现评审（保全分支 `codex/m4-synthetic-pipeline-implementation`，成果提交
`8a71fb9ba80701099be7c5df6e0c81ac13233ebb`）暴露了冻结的 M4 合成端到端流水线设计中的
**事实性错误与内部矛盾**。本次任务**只做设计更正**：把两份规范文件里与实测不符或自相矛盾的
陈述改成可核验的事实，不新增、不放宽任何能力、API、错误码、阶段、验证阶段或授权边界。

七项必改：

1. §11.3 的成功调用次数上界（原 ≤6 / ≤8）改为实测值 `build_analysis_plan <= 12`、
   `materialize_analysis_dataset <= 11`、`_execute <= 3`，并解释公开产出者计数为何包含验证重算；
   保留 `MAX_BOOTSTRAP_REPLICATIONS` 绝对上界。
2. 修正 J4/R11：具体合法记录必然序列化为有限字节，但上游 schema 对全体合法记录**没有**统一
   有限上界（元组基数、`state_history`、`authorization_ref`、`schema_version` 无上限）；
   不新增尺寸门、不编造总上限，保留小写十六进制往返要求。
3. 修正 G14/S0 扫描时机：S0 只能扫**入口可得投影**（可选注册表投影）；完整规范信封
   （含 contract/plan）在 V5/S7 扫描；明确既有 `FORBIDDEN_ARTIFACT_CONTENT` 载体，不新增第 15 个码。
4. 修正 §5.5 D6：组合链的稳健性参数只进入计划/信封并被 V5 捕获；有界执行产物 payload
   **不含**稳健性块；独立稳健性派遣入口有自己的既有扫描但不在本组合链上。
5. 修正 `PLAN_TERM_ROLE_MISMATCH` 的公开可达性：组合入口被 `CONTRACT_PLAN_MISMATCH` 抢先，
   只能由显式标注的内部/阶段投影探针证明；同一真实性标准应用到 AC-10、AC-12、AC-14、AC-15、AC-17。
6. 显式解决 G11 与 AC-28d 的冲突：复制次数上界**仅在 `bootstrap_plan.enabled is True` 时求值**。
7. 解决其余已记录歧义且不改变可观察能力：V4 结构失败使用既有封闭码、保留 RB4 的
   hex→sha256 映射、澄清 G14 的错误类型，并保持公开 20 符号面、14 码表、常量、schema、字段、
   签名、L1–L14、S0–S8、V1–V6、授权边界与全部上游契约不变。

## 范围

允许新增或修改（仅 5 条路径）：

1. `agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`（Codex 所有，本次未改）
2. `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`
3. `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`
4. `agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md`（本文件）
5. `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`

## 非目标

- 不修改 `src/**`、`tests/**`、README、其他 docs/acceptance/record/Goal、reports、config、
  data、events、fixture、依赖、workflow、`pyproject.toml`。
- 不实现、不修复、不放宽任何编排器行为；不把设计更正当作实现授权。
- 不新增真实数据、provider、数据库、文件系统、环境、网络、行情、文献、holdout、回测、排序、
  推荐、交易、持久化或注册表状态变更授权。
- 不修改任何上游 schema、摘要、验证器、公共导出、测试、受保护 blob、north-star gate、stash、
  数据库或其他工作树。
- 不推送、不开/合 PR、不进入下一阶段。

## 开始前状态

- 工作树：`D:/量化分析-m4-synthetic-pipeline-design-correction`；分支
  `codex/m4-synthetic-pipeline-design-correction`，HEAD `d69ba05`，领先 `origin/main` 1 个提交。
- 工作区干净（`git status --short --branch` 只有分支行）。
- stash：`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`（既有，未触碰）。
- Git 目录在工作区之外：`D:/量化分析/.git/worktrees/量化分析-m4-synthetic-pipeline-design-correction`
  （`workspace-write` 沙箱可能拒绝写 index；见"遗留问题"）。
- 实现证据不在本分支：编排器源码/测试/记录只在
  `codex/m4-synthetic-pipeline-implementation`（`8a71fb9`），因此全部以 `git show <ref>:<path>`
  只读方式核对，未 checkout、未改动工作树。
- Python 环境：`D:/量化分析-m4a2i/.venv/Scripts/python.exe`（3.13.9，numpy 2.5.3）。

## 实施计划

1. 只读核对基线与受保护对象（分支、HEAD、origin/main、stash、工作树列表、冻结 blob、数据库哈希）。
2. 通读两份规范文件与 Goal；用只读子代理独立测量调用拓扑、注册表序列化上界、验收可达性。
3. 用真实源码/实现测试逐条复核七项更正的事实依据（不做"相信报告"的结论）。
4. 只改两份规范文件中的事实性/矛盾陈述；不新增条款编号族、不改常量与错误码集合。
5. 创建本记录与配套验收证据文件。
6. 运行 Goal 要求的全部验证命令并记录实际退出码与通过数。
7. 以显式路径暂存创建 scoped 文档/证据提交；若沙箱拒绝则如实上报，不用替代 index/GIT_DIR 绕过。
8. 由独立的对抗性只读子代理复核最终差异，再给出唯一结论。

## 决策记录

1. **决策：把"实测值"写进 §11.3，而不是保留 ≤6/≤8 或放宽表述为"不适用"。**
   - 依据（实测，来自保全分支的测试断言）：`build_analysis_plan = 12`（适配器内引用 11 + 编排器 S2
     直调 1）、`materialize_analysis_dataset = 11`（适配器内引用 10 + 编排器 S4 直调 1）、
     `_execute = 3`（S6 + `validate_execution_artifact` V3 + `validate_pipeline_result` V2 内 V3）、
     `execute_bounded_analysis` 入口 = 1。
   - 替代方案：保留原上界并标注"实现超出"（会让规范自相矛盾）；或删除该表（会丢掉 Goal 第 6 条
     的 "bounded resource behavior" 依据）。均未采用。
   - 风险：这三项是拓扑常量；若未来上游验证链变化，必须重新实测（已在 R2 记录）。
2. **决策：J4/R11 只声明"逐记录有限、但对全体合法记录无一致有限上界"，且明确禁止新增尺寸门。**
   - 依据：`records.py` 的 `known_*` 元组只约束元素长度不约束基数；`state_history` 只有下界且
     状态机含 `NOT_TESTED ⇄ DEFERRED` 合法环；`authorization_ref` 只做标识符正则、`schema_version`
     不与常量比对。子代理实测：40,004 条 history → 5,870,359 字节仍被完整解析。
   - 替代方案：把实现测试里的 `RECORD_BYTES_HEX_BOUNDED_CEILING = 200000` 提升为设计保证（会把
     测试局部骨架上界伪装成 schema 保证）。未采用。
3. **决策：S0 扫描面收窄为"入口可得投影"，contract/plan 交给 V5。**
   - 依据：S0 早于 S1/S2，contract/plan 尚不存在；实现只在 S0 扫注册表投影，并在 V5 扫整信封。
   - 替代方案：把 contract/plan 的编译提前到 S0（会改变首错归属与步骤序）。未采用。
4. **决策：D6 按"计划/信封 + V5"重写，并明确执行产物不含稳健性块。**
   - 依据：`_execution_payload` 字段清单不含 robustness；`plan.robustness_plan.entries` 逐字承载
     合同参数；`_robustness_payload` 才含 `parameters`。
5. **决策：把 `PLAN_TERM_ROLE_MISMATCH` 从"组合入口可达"移到"仅内部投影探针可达"，并如实
   标注 `CONTRACT_PLAN_MISMATCH` 的可达面（组合入口不可达、信封层与阶段级可达）。**
   - 依据：`validate_design_matrix` 先 `_validated_matrix_payload`、再 `validate_dataset`
     （重编译比对 → `CONTRACT_PLAN_MISMATCH`）、最后才 `_project_validated_matrix`
     （唯一抛 `PLAN_TERM_ROLE_MISMATCH` 的私有助手；其 docstring 自述"not an entry point"）。
6. **决策：G11 增加 `enabled is True` 条件。**
   - 依据：AC-28d 明文"上界门不适用"；R17 的理由是重采样工作量；实现按 `enabled is True` 求值。
7. **决策：V4 结构失败（`pipeline_state` / `stages_completed`）映射到既有封闭码
   `PIPELINE_DIGEST_MISMATCH`，绑定失败用 `PIPELINE_REGISTRY_RECORD_INVALID` /
   `PIPELINE_REGISTRY_IDENTITY_MISMATCH`；G14 的载体明确为既有
   `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")`。**
   - 依据：实现 `_check_metadata` / `_check_registry_binding` / `_check_forbidden_content`；
     两者都复用既有类型与既有码，因此不新增第 15 个编排器码。
8. **决策：修正 AC-27 的白名单路径计数 6 → 7。**
   - 依据：设计 §12.3 与实现 Goal 的 Allowed scope 都列举 7 条路径（pipeline 两个源文件、
     一个测试文件、README、实现 Goal、实现记录、实现验收）。这是同一类"与仓库证据不符"的
     事实性陈述，且属于 Goal 要求的"内部交叉引用一致性"。
9. **决策：只读子代理用于四类独立测量（拓扑、schema 上界、验收可达性、最终对抗性复核），
   全部禁止写文件、禁止 Git 变更、禁止递归派工。**
   - 替代方案：全部由主代理自证（独立性不足）。未采用。
   - 风险：子代理结论仍由主代理逐条对照源码复核，不单独采信。

## 实际操作

1. 读取并核对：`AGENTS.md`、`agent/agent.md`、`agent/record/README.md`、Goal 契约、两份规范文件全文。
2. 只读核对基线：`git status --short --branch`、`git rev-parse HEAD origin/main refs/stash`、
   `git log`、`git worktree list --porcelain`、`git diff --name-status origin/main...<impl 分支>`。
3. 读取实现证据（只读 `git show`）：`mechanism/pipeline/orchestrator.py`、
   `tests/test_m4_synthetic_pipeline_orchestrator.py`、
   `agent/record/2026-09-12_01_m4-synthetic-end-to-end-pipeline-implementation.md`。
4. 读取既有上游源码核对事实：`planning/compiler.py`、`planning/matrix.py`、`datasets/synthetic.py`、
   `execution/bounded.py`、`registry/records.py`、`registry/states.py`、`hypothesis_config.py`。
5. 派发 3 个只读子代理（拓扑测量、schema/bounds 审计、验收可达性审计），并逐条对照源码复核其结论。
6. 修改 `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`：
   - 头部状态段加入"2026-09-12 设计更正"清单与"公开面/常量/错误码未变"声明；
   - §4.4 `J4` 重写（无一致有限上界、不新增尺寸门）；
   - §5.5 `D6` 重写（计划/信封 + V5；执行产物不含稳健性块；派遣入口独立扫描且不在链上）；
   - §6.1 `S0` 行注明"入口可得投影"；§6.2 `P3` 补实测总计数；
   - §7.1 `G11` 增加 `enabled is True` 条件；`G14` 行明确两个求值点与既有 `ExecutionError` 载体；
     S0 扫描面段落重写（删除不可实现的 contract/plan 扫描）；
   - §8.3 `PIPELINE_REPLICATIONS_EXCEED_LIMIT` 行同步；§8.4 `S5` 行加可达面指引；
   - §8.5 重写入口级分类：`CONTRACT_PLAN_MISMATCH` 与 `PLAN_TERM_ROLE_MISMATCH` 移入 §8.5.2 并
     说明真实可达面；
   - §9.5 `V3`/`V4`/`V5` 补失败码映射；§10.3 绑定失败码与 RB4 映射说明；
   - §11.3 三项上界改为实测值与依据，并解释计数含验证重算；`§11.3.1 R17.2` 增加启用条件；
   - §14 `R2`/`R11`/`R17`/`R19` 重写。
7. 修改 `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`：
   - 头部状态段加入更正说明；§1 索引表的验证阶段列按入口分类更新（AC-10/11/12/14/15/17/22/28）；
   - §1.2 可达性分类表重写为五类（组合入口 / 信封层 / 阶段级探针 / 内部投影探针 / 静态证明），
     并列出各案例与"上游对象不可提交"的结构性结论；
   - AC-10 改为 `STAGE_LEVEL_PROBE` 并说明组合入口不可表达；
   - AC-12 增加"入口"列：AC-12b 改为组合入口的陈旧摘要路径，删除不可表达的适配器分支；
   - AC-14 增加显式探针入口与可达性说明；AC-15 验证阶段表述精确化；
   - AC-17 表格增加"可达入口"列：AC-17a 改为组合入口、AC-17e 改为内部投影探针并双断言
     （内部探针 → `PLAN_TERM_ROLE_MISMATCH`；公开验证器 → `CONTRACT_PLAN_MISMATCH`）、
     AC-17f 明确在组合链外；
   - AC-22d 改为组合入口 / V5 信封层，并拆分"派遣入口自有扫描"（AC-17f）；
   - AC-25 增加"无总尺寸上限、无尺寸门"断言；
   - AC-28 明确 G11 仅在 `enabled=true` 时求值；AC-27 白名单计数 6 → 7；
   - AC-30 入口列表更新；§10 验收顺序第 4/5/7 项与 §11 边界声明同步。
8. 创建本记录与 `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`。
9. 运行 Goal 要求的验证命令（结果见"验证"节）。
10. 尝试以显式路径暂存创建 scoped 提交：`git add -- <4 条显式路径>` 被沙箱拒绝
    （`index.lock: Permission denied`）；按规则以 `danger-full-access` 重试同一条命令一次，
    平台回复审批通道不可用。**未产生提交**（结果见"最终Git状态"与"遗留问题"）。
11. 派发第 4 个只读子代理做对抗性最终复核（试图证伪七项更正、查找残留矛盾与越界改动）。

## 数据与方法说明

本次任务不涉及数据研究：未读取行情、未访问 provider/数据库、未采集文献、未使用 holdout、
未产生任何统计量。全部"实测"证据来自两类只读来源：

- 本工作树内的既有上游源码（`src/ashare_research/mechanism/**`）的逐行阅读；
- 保全分支 `codex/m4-synthetic-pipeline-implementation`（`8a71fb9`）的编排器源码、测试与记录的
  `git show` 只读阅读——该分支的实测计数由实现阶段的 monkeypatch 计数测试断言，本次未重跑
  （编排器不在本分支，按 Goal 禁止把实现带入本任务）。

## 验证

全部命令在本工作树执行；环境 `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`，
`$py = 'D:/量化分析-m4a2i/.venv/Scripts/python.exe'`（Python 3.13.9，numpy 2.5.3）。

| # | 命令 | 退出码 | 实际结果 |
| --- | --- | --- | --- |
| 1 | `& $py -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 0 | `15 passed in 0.14s` |
| 2 | `& $py -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py` | **1** | `185 passed, 2 errors`（三次运行一致：`80.56s` / `32.22s` / `28.70s`）；两个 error 均为 `tmp_path` 用例在 setup/cleanup 抛 `PermissionError: [WinError 5]`（沙箱拒绝目录枚举），见"遗留问题" |
| 3 | `& $py -m ruff check src tests` | 0 | `All checks passed!` |
| 4 | `git diff --check` | 0 | 无输出 |
| 5 | `git diff --cached --check` | 0 | 无输出 |
| 6 | `git status --short --branch` | 0 | 见"最终Git状态" |
| 7 | `git rev-parse HEAD origin/main refs/stash` | 0 | `d69ba05…` / `d3fcb196…` / `cb568ef…`（与 Goal 记录一致） |
| 8 | `git worktree list --porcelain` | 0 | 20 个 worktree 与任务开始时一致；主工作树 `D:/量化分析` 仍为 `3679b1ba…`；实现保全工作树仍为 `8a71fb9…` |
| 9 | `git stash list` | 0 | 仅既有 `stash@{0}`（Stage 1B.4 保护项），未新增/未改动 |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | 0 | `d3fcb1967e9e7f6d3caac3e3f08ea874646f3098`（= `origin/main`） |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | 0 | `[]` |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | 0 | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`（未变） |
| 13 | `git -C 'D:/量化分析' rev-parse HEAD` | 0 | `3679b1bac7a1634c6452784a4d8f6d139966f222`（未变） |
| 14 | `git diff --name-only origin/main...HEAD` | 0 | 仅 Goal 文件（HEAD 即 Goal 提交） |
| 15 | `git diff --name-only origin/main -- src tests reports config data events .github pyproject.toml README.md` | 0 | 空（受保护路径零改动） |
| 16 | `git hash-object docs/m4_bounded_execution_and_evidence_design_v1.md docs/m4b_hypothesis_registry_design_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json` | 0 | `9617f643…` / `6d9c2920…` / `dfd41eaa…`（与 Goal 一致） |

补充验证（脚本/正则，均在本工作树执行）：

- Markdown 链接解析：设计 8 个链接、验收 1 个链接，未解析数 0。
- 内部交叉引用：设计 41 个"第 X 节"引用全部解析；验收 25 个引用在设计/验收两份文档中全部解析。
- 编码卫生：四份文件 CR=0、冲突标记=0、行尾空白=0、末尾换行=true、无 BOM。
- 结构计数不变：§4.4 `__all__` = 20 符号；§8.3 = 14 码；§6.1 `S0`–`S8` = 9 行；
  §6.2 `P1`–`P7` = 7 项；§9.1 `L1`–`L14` = 14 行；§9.5 `V1`–`V6` = 6 行；§7.1 `G1`–`G14` = 14 行；
  §4.4/§8.3 与基线（HEAD 版本）逐项相等；§3 常量块与基线逐字节相等。
- 验收案例完整性：30 个 `### AC-` 小节、30 个索引行、无孤儿编号。
- Markdown 表格列数一致（四份文件均 0 处不一致）。
- 白名单核对：`git status` 仅显示 2 个规范文件被修改 + 2 个证据文件为新增（外加一个沙箱创建的
  不可读空目录 `.dsh-pytest-tmp/`，见"遗留问题"）。

### 对抗性最终复核（第 4 个只读子代理）

复核结论：七项更正全部有据、未授权面零改动、既有验收义务未被删除或放宽；报出 4 处真实缺陷，
**均在提交前修复**：

- D1（中）：验收 §1.2 把 `INPUT_DIGEST_MISMATCH` 与适配器 `IDENTITY_CONFLICT` 误列为"组合入口
  不可达"（实测 `synthetic.py:552`、`:537/:549` 表明二者可由 `bound_inputs` 在 S4 触发）→ 已重写，
  并新增"不得过度归类"段。
- D2（低）：AC-12b 的门禁归属应为 G9（改 `config` 同时改变 `contract_digest`）→ 已更正（G9/G10 同码）。
- D3（低）：验收头部"不新增…验收义务"与自身 diff 不符（新增 AC-25 第 7 条、AC-22d 双路径、
  AC-28 关键断言第 4 条）→ 已改为"不删除、不放宽既有义务，并新增与更正直接对应的断言"。
- D4（低）：设计 §6.3 "不是 acceptance 入口"与新增的 `INTERNAL_PROJECTION_PROBE` 冲突 →
  §6.3 已补唯一例外，并重申**编排器**仍不得调用私有助手。
- 非缺陷提示（已处理）：删除证据文件中的"（执行后回填）"占位；设计头部变更清单扩为完整节列表。

## 结果

**已完成**（内容层面）：

1. 七项必改全部落地于两份规范文件，且每项都有既有源码或保全分支实测证据支撑（详见
   `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md` 第 1 节）。
2. 公开 20 符号面、14 码封闭表、常量、schema、字段、签名、`L1`–`L14`、`S0`–`S8`、`V1`–`V6`、
   `G1`–`G14`、`P1`–`P7`、授权矩阵与全部上游契约未变（结构性计数已验证）。
3. 受保护 blob、数据库哈希、stash、其他工作树、主工作树 HEAD、live main 与开放 PR 状态均已核对，
   与任务开始时一致。
4. 新增本记录与配套验收证据文件。

**未完成**：

- **未能创建 scoped 提交**（硬阻塞，环境性，见"遗留问题"第 1 条）。因此变更目前仅存在于工作区，
  由 Codex 在宿主环境按显式路径暂存并提交。
- Goal 第 2 条 pytest 命令在本沙箱内以 1 退出（2 个 `tmp_path` error），需宿主环境重跑。

**与原计划的差异**：原计划第 7 步（创建 scoped 提交）未能执行；其余步骤按计划完成。
另额外修正了四处同类的内部不一致：AC-27 白名单计数 6→7、AC-29d 引用的失败路径必须是组合入口，
以及对抗性复核报出的 D1（`INPUT_DIGEST_MISMATCH`/适配器 `IDENTITY_CONFLICT` 误列为不可达）、
D2（AC-12b 门禁归属 G9）与 D3/D4（两处措辞与自身内容冲突）。

**当前是否可用**：两份规范文件内容自洽、可审阅；实现阶段必须等待 Codex 的独立复核与提交。

**条件通过项**：第 2 条测试命令的 2 个 `tmp_path` 用例为条件通过（环境限制，需宿主重跑）。

## 遗留问题

1. **Git 索引不可写（硬阻塞）**：本工作树的 Git 目录在工作区之外
   （`D:/量化分析/.git/worktrees/量化分析-m4-synthetic-pipeline-design-correction`）。
   实测 `git add -- <4 条显式路径>` → `fatal: Unable to create '…/index.lock': Permission denied`
   （退出码 128）。按规则以 `danger-full-access` 重试同一条命令一次，平台回复
   "requires approval, but no approval channel is available"——审批通道不可用，失败关闭。
   Goal 明确禁止用替代 index / 替代 `GIT_DIR` / 重建仓库绕过，因此**未创建任何提交**，
   HEAD 仍为 `d69ba05`。由 Codex 在宿主环境按 Goal 白名单路径暂存并提交。
2. **沙箱内 2 个 `tmp_path` 测试 error**：`test_cwd_and_from_dict_order_invariance` 与
   `test_ac12_and_13_canonical_bytes_are_order_and_cwd_independent` 在 setup/cleanup 阶段抛
   `PermissionError: [WinError 5]`。isolated 重跑（含 `--basetemp` 指向工作区内目录）同样 error，
   证明是沙箱目录枚举/清理限制；**未计为通过**，需 Codex 在宿主环境重跑。
3. **残留空目录 `.dsh-pytest-tmp/`**：上述补充重跑创建，沙箱同时拒绝 `Remove-Item`
   （`Access to the path … is denied`）。该目录为空、不被 Git 跟踪（`git status` 仅提示无法打开），
   不会进入提交；建议 Codex 在宿主环境删除。
4. **未在本会话重跑实现测试**：编排器不在本分支；12/11/3 等实测值来自保全分支的源码与测试断言
   （只读 `git show`），未重新执行那 40 个实现测试。
5. **`PIPELINE_INTERNAL_SOURCE_UNMAPPED` 的可触发点仍未被独立证实**（设计 R1 保留原兜底语义）。
6. 子代理并发审计的时点差异：可达性审计子代理在其报告中按冻结基线行号给出结论，其中若干
   "残留不一致"（AC-17a 标注、AC-22d 归属、§8.4 的 S5 行）已在本次编辑中修正；其
   "`CONTRACT_PLAN_MISMATCH` 亦可在信封层命中"的意见已采纳并写入设计 §8.5.2。

## 下一步建议

只与当前项目核心目标相关的下一步：由 Codex 在宿主环境（1）重跑第 2 条 pytest 命令与 40 个实现
测试，（2）按白名单显式路径提交本次文档/证据变更，（3）独立复核实际 Git 证据后给出最终裁决。
在独立 `PASS` 之前不得推送、开 PR、合并或恢复实现阶段。

## 最终文件变更

新增：

- `agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md`（本文件）
- `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`

修改：

- `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`
- `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`

未改：`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`（Codex 所有，
本次无需改动）、`src/**`、`tests/**`、`README.md`、其他 docs/acceptance/record、reports、config、
data、events、fixture、依赖、workflow、`pyproject.toml`。

## 最终Git状态

- 当前分支：`codex/m4-synthetic-pipeline-design-correction`
- 当前提交：`d69ba05fb35fb076f7f10e1e84c29bc1e9cff0a2`（**未产生新提交**；原因见"遗留问题"第 1 条）
- 未提交修改：`M docs/m4_synthetic_end_to_end_pipeline_design_v1.md`、
  `M docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`、
  `?? acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`、
  `?? agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md`
  （外加不可读的空目录 `.dsh-pytest-tmp/`，Git 不跟踪）
- 是否创建提交或 Tag：**否**（沙箱拒绝写 Git index；升级审批不可用）
- 是否执行推送：**否**（Goal 明确禁止；本次也未创建 PR、未合并、未进入实现/下一阶段）

## 状态

`conditional_pass`（内容层面全部完成并已自验，且经独立对抗性复核确认七项更正有据、未越界；
因沙箱不能创建 scoped 提交且 2 个 `tmp_path` 用例需宿主重跑，最终提交与验收由 Codex 在宿主
环境完成；复核期间文档仍在修正，宿主提交时以实际字节为准）。
