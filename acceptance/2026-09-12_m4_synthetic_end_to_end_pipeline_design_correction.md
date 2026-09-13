# 验收证据：M4 合成端到端流水线设计更正

- 任务契约（Goal）：`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`
- 工作记录：`agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md`
- 分支：`codex/m4-synthetic-pipeline-design-correction`
- 起始 HEAD：`d69ba05fb35fb076f7f10e1e84c29bc1e9cff0a2`（Goal 契约提交）
- 基线 `origin/main` / live main：`d3fcb1967e9e7f6d3caac3e3f08ea874646f3098`（PR #16 合并点）
- DSH 内容成果提交：`f997b95d2e4e35345b92757b29b6c9a36018231a`（由 Codex 在宿主环境按
  4 条显式白名单路径创建；DSH 沙箱阻塞的原始证据保留在第 6 节）
- 证据等级：本次是**设计/文档更正**，不含任何编排器实现、统计执行或真实数据证据。
  全部"实测"结论来自只读源码阅读与保全分支 `codex/m4-synthetic-pipeline-implementation`
  （成果提交 `8a71fb9ba80701099be7c5df6e0c81ac13233ebb`）的源码、测试与记录；本次未重跑其测试。

---

## 1. 七项必改的落地位置与依据

### 1.1 §11.3 成功调用次数上界（Goal 第 1 项）

- 更正位置：`docs/m4_synthetic_end_to_end_pipeline_design_v1.md` §11.3 表前三行 + 表下说明；
  §6.2 `P3` 补实测指针；§14 `R2`。
- 原文（错误）：`build_analysis_plan <= 6`、`materialize_analysis_dataset <= 8`。
- 更正后（实测）：`build_analysis_plan <= 12`（编排器 S2 直调 1 + 经适配器模块内引用的链式重算 11）、
  `materialize_analysis_dataset <= 11`（编排器 S4 直调 1 + 链式重算 10）、`_execute <= 3`
  （S6 1 + `validate_execution_artifact` V3 1 + `validate_pipeline_result` V2 内 V3 1）。
- 依据（只读，来自保全分支测试断言）：
  `tests/test_m4_synthetic_pipeline_orchestrator.py` 的 `MEASURED_CALL_PROFILE`
  （`datasets_adapter=10, datasets_direct=1, plans_adapter=11, plans_direct=1, execute=3, entry=1`）
  与 `assert measured["execute"] <= 3`。
- 已解释"公开产出者计数为何包含验证重算"：计数打在公共产出者符号上（同时统计编排器直调与
  既有验证器触发的每次链式重算）；S7 `validate_pipeline_result` V2 会再跑一遍 S1–S6 验证链，
  单独贡献 +4 / +4 / +1。
- 绝对 bootstrap 复制上界 `MAX_BOOTSTRAP_REPLICATIONS = 100000` **保留**。

### 1.2 J4 / R11 序列化上界（Goal 第 2 项）

- 更正位置：§4.4 `J4`；§14 `R11`。
- 原文（错误）：`record_bytes_hex` 长度上界 = `2 × (各文本字段上限之和 + 固定键与结构开销)`，
  并要求实现评审"实测该上界"。
- 更正后：具体合法记录必然序列化为**有限**字节（`2 × len(serialize_hypothesis_record(record))`），
  但既有 M4-B schema 对全体合法记录**没有**统一有限上界：四个 `known_*` 元组基数、
  `state_history` 长度、`authorization_ref`、`schema_version` 均无上限；**不冻结**总上限、
  **不新增**尺寸门；保留 J1–J3 的小写十六进制与逐字节往返要求。
- 依据：`src/ashare_research/mechanism/registry/records.py` 的字段约束（仅元素级文本上限、
  `state_history` 只有下界）；`states.py` 的 `NOT_TESTED ⇄ DEFERRED` 合法环使 history 可无界增长。
  只读子代理实测：40,004 条 history → 5,870,359 字节仍被完整解析；`schema_version` 20,000 字符、
  `authorization_ref` 100,000 字符均被接受。
- 交叉一致：验收文档 AC-25 新增第 7 条断言（无总上限、无尺寸门、不得把骨架实测值声称为 schema 保证）。

### 1.3 G14 / S0 扫描时机（Goal 第 3 项）

- 更正位置：§6.1 `S0` 行；§7.1 `G14` 行、门禁时机段、S0 扫描面段；§9.5 `V5`。
- 原文（错误）：S0 扫描面包含 `contract_to_canonical_dict(contract)` 与
  `plan_to_canonical_dict(plan)`。S0 早于 S1/S2，这两个对象尚不存在。
- 更正后：S0 只扫**入口可得投影**（可选注册表记录投影
  `hypothesis_record_to_canonical_dict(record)`）；contract/plan/preparation/matrix/execution 的
  权威投影由 **V5 在 S7 对完整规范信封字典**一次性扫描；命中载体明确为既有
  `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")`（既有类型 + 既有码），**不新增第 15 个码**，
  也不改变 AC-16 首错归属。
- 依据：实现 `orchestrator.py` S0 段只调用注册表投影扫描；V5 段扫描
  `pipeline_result_to_canonical_dict(result)`（含 contract/plan）。

### 1.4 §5.5 D6 组合稳健性参数（Goal 第 4 项）

- 更正位置：§5.5 `D6`；验收文档 AC-22d 与"两条路径必须分开断言"段。
- 原文（错误）：稳健性参数"随计划进入**执行产物 payload** 并被 `_check_forbidden_content` 递归扫描"。
- 更正后：稳健性参数被逐字转发进 `plan.robustness_plan.entries` → 进入信封 `plan` 投影 →
  由 **V5** 在 S1–S6 完整执行之后拒绝；既有**有界执行产物 payload 不含稳健性块**，
  `execute_bounded_analysis` 在 `{"trim":"A/B"}` / `{"path":"0.0100"}` 下会成功；独立派遣入口
  `prepare_registered_robustness_dispatch` 有自己的既有扫描（`_robustness_payload` 含 `parameters`），
  但不在本组合链上（P7 / AC-23），其探针为 AC-17f。
- 依据：`execution/bounded.py` 的 `_execution_payload` 字段清单不含 robustness；`_robustness_payload`
  含 `entries[*].parameters`；`planning/compiler.py` 的 `robustness` 段逐字复制
  `source["robustness_registry"]`。

### 1.5 `PLAN_TERM_ROLE_MISMATCH` 与 AC-10/12/14/15/17 可达性（Goal 第 5 项）

- 更正位置：设计 §8.4 `S5` 行、§8.5 全节（含新分类前言与 §8.5.2 两行）、§14 `R19`；
  验收文档 §1 索引、§1.2 分类表、AC-10、AC-12、AC-14、AC-15、AC-17、AC-30、§10 第 4 项、§11。
- 更正后：
  - `PLAN_TERM_ROLE_MISMATCH`：组合入口**不可达**；公开阶段验证器（`validate_design_matrix`）
    也被 `AdapterError("CONTRACT_PLAN_MISMATCH")` 抢先；只能由显式标注的**内部投影探针**
    （直接调用私有 `_project_validated_matrix`）证明。AC-17e 要求**双断言**
    （内部探针 → `PLAN_TERM_ROLE_MISMATCH`；公开验证器 → `CONTRACT_PLAN_MISMATCH`）。
  - `CONTRACT_PLAN_MISMATCH`：组合入口不可达（合同/计划均由编排器自行编译，G9/G10 前置）；
    **信封层**可达（公开 `validate_pipeline_result` V2）与阶段级可达。
  - AC-10：从"请求层篡改"改为 `STAGE_LEVEL_PROBE`（请求类型无合同字段，组合入口不可表达）。
  - AC-12b：从"改计划字段 + 适配器 `CONTRACT_PLAN_MISMATCH` 兜底"改为组合入口的
    **陈旧摘要**路径（改 `config` → S3 G9/G10 同码的 `PIPELINE_INPUT_BINDING_MISMATCH`；
    改 `config` 同时改变 `contract_digest`，故通常 G9 先命中），
    并显式说明"同步重绑输入 = 一次合法新请求，不是篡改路径"。
  - AC-14：补充显式探针入口（`validate_design_matrix` 配合伪造 preparation/matrix）与
    STAGE_LEVEL_PROBE 标注；错误码保持不变。
  - AC-15：明确 a–d 为阶段级、e/f 为信封层；错误码保持不变。
  - AC-17a：从阶段级改为**组合入口可达**（`config` 的 holdout 与开发期重叠 → S1
    `DEVELOPMENT_HOLDOUT_OVERLAP`）；AC-17e 改为内部投影探针；AC-17f 明确在组合链外。
- 依据：`planning/matrix.py` 的 `validate_design_matrix`（先 `_validated_matrix_payload` → 再
  `validate_dataset` → 最后 `_project_validated_matrix`）、`_project_validated_matrix` 的
  docstring "not an entry point"、`datasets/synthetic.py` `_validate_inputs` 的重编译比对；
  实现测试对两者的双断言。

### 1.6 G11 与 AC-28d（Goal 第 6 项）

- 更正位置：§7.1 `G11` 行；§8.3 `PIPELINE_REPLICATIONS_EXCEED_LIMIT` 行；§11.3 绝对上界行；
  §11.3.1 `R17.2`；§14 `R17`；验收文档 AC-28 表与关键断言第 4 条、索引表。
- 更正后：该门**仅在 `bootstrap_plan.enabled is True` 时求值**；`enabled is False` 的计划
  没有重采样工作，其惰性 `replications` 声明**不**被拒绝（与 AC-28d 一致）。
- 依据：实现 `orchestrator.py` 的 `if bootstrap["enabled"] is True and bootstrap["replications"] > MAX...`；
  AC-28d 原文"上界门不适用"；R17 的资源语义（`3 × replications` 重采样）。

### 1.7 其余歧义（Goal 第 7 项）

- V4 结构失败（`pipeline_state` / `stages_completed` 不符）→ 既有封闭码 `PIPELINE_DIGEST_MISMATCH`；
  绑定条款失败 → `PIPELINE_REGISTRY_RECORD_INVALID` / `PIPELINE_REGISTRY_IDENTITY_MISMATCH`
  （§9.5 `V3`/`V4`、§10.3）。依据：实现 `_check_metadata` / `_check_registry_binding`。
- RB4 的 hex→sha256 映射**保留**（§10.3 明示 `bytes.fromhex(record_bytes_hex)` 后取 SHA-256）。
- G14 的错误类型明确为既有 `ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")`。
- 公开 20 符号面、14 码封闭表、常量值、schema、字段、签名、L1–L14、S0–S8、V1–V6、授权边界与
  全部上游契约保持不变（结构性计数见第 4 节）。
- 附带一致性修正（两处，均属"与仓库证据不符"的同类事实错误）：
  AC-27 的白名单路径计数 `6 → 7`（设计 §12.3 与实现 Goal 均列举 7 条）；
  AC-29d 引用的失败路径改为**组合入口**（原引用 AC-10，而 AC-10 已改为阶段级探针，
  不经由 `run_synthetic_pipeline`，无法验证编排器的 `localcontext` 行为）。

---

## 2. 精确变更清单（文件 / 节 / 行）

### 2.1 `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`

| 节 | 变更 |
| --- | --- |
| 头部状态段 | 新增 2026-09-12 设计更正清单与"公开面/常量/错误码未变"声明 |
| §4.4 `J4` | 重写：无一致有限上界、不新增尺寸门、保留十六进制往返 |
| §5.5 `D6` | 重写：计划/信封 + V5；执行产物不含稳健性块；派遣入口独立扫描且不在链上 |
| §6.1 `S0` 行 | 扫描目标改为"入口可得投影" |
| §6.2 `P3` | 补实测总计数与 S7 V2 额外一轮指针 |
| §7.1 `G11` 行 | 增加 `enabled is True` 求值条件 |
| §7.1 `G14` 行 | 明确两个求值点与既有 `ExecutionError` 载体 |
| §7.1 门禁时机段 | S0 描述改为"形态、类型与入口可得投影的禁止内容检查" |
| §7.1 S0 扫描面段 | 重写：删除不可实现的 contract/plan 扫描，指明 V5 |
| §8.3 复制上界行 | 同步 `enabled is True` 条件 |
| §8.4 `S5` 行 | 为 `PLAN_TERM_ROLE_MISMATCH` 加可达面指引 |
| §8.5 前言 + §8.5.1 + §8.5.2 | 重写入口级分类；`CONTRACT_PLAN_MISMATCH` 与 `PLAN_TERM_ROLE_MISMATCH` 移入不可达表并说明真实可达面 |
| §9.5 `V3`/`V4`/`V5` | 补失败码映射（含 V4 结构失败 → `PIPELINE_DIGEST_MISMATCH`） |
| §10.3 | 绑定失败码与 RB4 hex→sha256 映射说明 |
| §11.3 表 + 表下说明 | 三项上界改为实测值与依据；解释计数含验证重算；保留绝对上界 |
| §11.3.1 `R17.2` | 增加 `enabled is True` 求值条件与理由 |
| §14 `R2`/`R11`/`R17`/`R19` | 按实测重写 |

### 2.2 `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`

| 节 | 变更 |
| --- | --- |
| 头部状态段 | 新增更正说明 |
| §1 索引表 | AC-10/11/12/14/15/17/22/28 的验证阶段列按入口分类更新 |
| §1.2 | 可达性分类重写为五类（组合入口 / 信封层 / 阶段级探针 / 内部投影探针 / 静态证明），并列出结构性不可达码 |
| AC-10 | 改为 `STAGE_LEVEL_PROBE`，说明组合入口不可表达 |
| AC-12 | 表格增加"入口"列；AC-12b 改为组合入口陈旧摘要路径；删除不可表达的适配器分支 |
| AC-14 | 增加显式探针入口与可达性说明（错误码不变） |
| AC-15 | 可达性与验证阶段表述精确化（错误码不变） |
| AC-17 | 增加"可达入口"列；AC-17a → 组合入口；AC-17e → 内部投影探针 + 双断言；AC-17f 明确在链外 |
| AC-22d | 改为组合入口 / V5 信封层；新增"两条路径分开断言"段 |
| AC-25 | 新增"无总尺寸上限、无尺寸门"断言（第 7 条） |
| AC-27 | 白名单路径计数 `6 → 7` 并逐项列举 |
| AC-28 | 明确 G11 仅在 `enabled=true` 求值；新增关键断言第 4 条 |
| AC-29d | 失败路径引用由 AC-10 改为组合入口路径（AC-13 / AC-12b），保持"失败后全局 decimal 上下文不变"义务 |
| AC-30 | 探针入口列表更新为三类 |
| §10 第 4/5/7 项、§11 | 与上述分类和实测上界同步 |

### 2.3 新增文件

- `agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md`
- `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`（本文件）

---

## 3. 验证命令与结果（实际执行）

环境：`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`；
`$py = 'D:/量化分析-m4a2i/.venv/Scripts/python.exe'`（Python 3.13.9，numpy 2.5.3）。

| # | 命令 | 退出码 | 结果 |
| --- | --- | --- | --- |
| 1 | `& $py -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 0 | `15 passed in 0.14s` |
| 2 | `& $py -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py` | **1** | `185 passed, 2 errors`（三次运行一致：`80.56s` / `32.22s` / `28.70s`）——2 个 `tmp_path` 用例在 sandbox 内 setup/cleanup 阶段 `PermissionError: [WinError 5]`（见第 5 节"偏差"） |
| 3 | `& $py -m ruff check src tests` | 0 | `All checks passed!` |
| 4 | `git diff --check` | 0 | 无输出（无空白错误） |
| 5 | `git diff --cached --check` | 0 | 无输出 |
| 6 | `git status --short --branch` | 0 | 见第 6 节 |
| 7 | `git rev-parse HEAD origin/main refs/stash` | 0 | `d69ba05…` / `d3fcb196…` / `cb568ef…` |
| 8 | `git worktree list --porcelain` | 0 | 20 个 worktree，全部与任务开始时一致；主工作树 `D:/量化分析` 仍为 `3679b1ba…` |
| 9 | `git stash list` | 0 | 仅既有 `stash@{0}: On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4 record edit before Stage 1C` |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | 0 | `d3fcb1967e9e7f6d3caac3e3f08ea874646f3098`（与 `origin/main` 一致） |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | 0 | `[]`（无开放 PR） |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | 0 | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`（与 Goal 一致） |
| 13 | `git -C 'D:/量化分析' rev-parse HEAD` | 0 | `3679b1bac7a1634c6452784a4d8f6d139966f222`（与 Goal 一致） |
| 14 | `git diff --name-only origin/main...HEAD` | 0 | 仅 `agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`（HEAD 即 Goal 提交） |
| 15 | `git diff --name-only origin/main -- src tests reports config data events .github pyproject.toml README.md` | 0 | 空（受保护路径零改动） |
| 16 | `git hash-object docs/m4_bounded_execution_and_evidence_design_v1.md docs/m4b_hypothesis_registry_design_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json` | 0 | `9617f64360b6c3d9a6148ec08c25fa0209a0f9f4` / `6d9c292001c09a4b1a8e895e54619dc1e8826f3d` / `dfd41eaafc099e7748499f72de7ddd800bf97f69`（与 Goal 逐一相等） |

补充验证（Goal「Also verify」段）：

| 检查 | 方法 | 结果 |
| --- | --- | --- |
| 精确白名单 | `git status --short --branch` + 显式路径暂存记录 | 仅 5 条白名单路径中的 2 个规范文件被修改、2 个证据文件新增；无第 6 条路径 |
| Markdown 链接可解析 | 正则提取 `](target)` 后 `Test-Path`（跳过 `http(s)`/纯锚点） | 设计 8 个链接、验收 1 个链接，**未解析数 0** |
| UTF-8 / 无 CR / 无冲突标记 / 无行尾空白 / 末尾换行 | 逐字节读入后正则计数 | 设计：CR=0、冲突标记=0、行尾空白=0、末尾换行=true；验收：同为 0/0/0/true |
| 公开导出面 | 正则计数 §4.4 `__all__` 代码块中的带引号符号 | **恰为 20** |
| 14 码封闭表 | 正则计数 §8.3 表行 | **恰为 14 行**，逐项等于冻结清单 |
| 条款族计数 | §6.1 `S0`–`S8` = 9 行；§6.2 `P1`–`P7` = 7 项；§9.1 `L1`–`L14` = 14 行；§9.5 `V1`–`V6` = 6 行；§7.1 `G1`–`G14` = 14 行 | 全部不变 |
| 上游契约未改 | 受保护路径 diff 为空 + 三个受保护 blob 哈希相等 | 通过 |
| 每项更正有既有源码或实测证据支撑 | 见第 1 节逐项"依据" | 通过 |

---

## 4. 受保护基线与授权边界

- 冻结 blob：`9617f643…`（有界执行设计）、`6d9c2920…`（M4-B 注册表设计）、`dfd41eaa…`
  （Stage4P 契约 JSON）——本次**未修改**。
- 数据库：`D:/量化分析/data/research.duckdb` SHA256 未变（第 3 节第 12 行）。
- stash：未触碰（第 3 节第 9 行）。
- 其他工作树：未触碰；实现保全工作树仍在 `8a71fb9`。
- 授权边界：本次**未**新增任何真实数据、provider、数据库、网络、行情、文献、holdout、回测、
  排序、推荐、交易、持久化或注册表变更能力；两份文档仍声明
  `M4 SYNTHETIC PIPELINE NOT IMPLEMENTED` / `NOT AUTHORIZED`。
- 未推送、未开 PR、未合并、未进入实现或下一阶段。

---

## 5. 偏差、失败与残余风险

1. **Sandbox 测试失败（必须由 Codex 在宿主环境重跑）**：Goal 第 2 条 pytest 命令在本沙箱内
   以 `1` 退出：`185 passed, 2 errors`。两个 error 均为 `tmp_path` 相关用例
   （`tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance`、
   `tests/test_m4b_hypothesis_registry.py::test_ac12_and_13_canonical_bytes_are_order_and_cwd_independent`），
   在 setup/cleanup 阶段抛 `PermissionError: [WinError 5]`（沙箱拒绝目录枚举/清理）。
   补充隔离重跑（含 `--basetemp` 指向工作区内目录）同样得到这 2 个 error，证明是环境限制而非
   用例逻辑失败。**本次未把它们计为通过**。
2. **无法清理的沙箱临时目录**：补充重跑创建了 `.dsh-pytest-tmp/`（工作区内），沙箱同时拒绝
   `Remove-Item`（`Access to the path … is denied`），因此该空目录残留在工作树中。
   它不被 Git 跟踪（`git status` 仅提示无法打开该目录），不会被提交；Codex 可在宿主环境删除。
3. **未执行实现测试**：编排器不在本分支，按 Goal 不得把实现带入本任务；本次对 12/11/3 等实测值的
   采信来自保全分支的源码与测试断言（只读 `git show`），**未**在本次会话重跑该套 40 个实现测试。
   若 Codex 要求独立复现，可在实现工作树或合并后重跑。
4. **`_execute` 内部循环与 `3 × replications`**：本次只更正上界的"依据"列（补上 S7 V2 的第二次
   V3 重执行），未改变工作量数量级结论。
5. **`PIPELINE_INTERNAL_SOURCE_UNMAPPED` 的实际可触发点仍未被独立证实**（无实测触发），设计保留
   原 R1 兜底条款，本次未改动其语义。
6. **AC-22d 的"配置能否构造出通过 V5 之前全部检查的 `/` 参数"**：由实现测试证实（`{"trim":"A/B"}`
   与 `{"path":"0.0100"}` 都在 V5 被拒），本次未重跑；分类已按该实测结论更正。
7. **不涉及数据研究**：无数据来源、样本期、复权、单位、缺失值或未来数据泄漏问题需要记录。

---

## 5.1 对抗性最终复核（独立只读子代理）与整改

第 4 个只读子代理对最终差异做了**对抗性**复核（目标是证伪七项更正、查找残留矛盾与越界改动），
其独立结论为：**七项更正全部 SUPPORTED**、未授权面零改动（§3 常量、20 符号面、`L1`–`L14`、
`S1`–`S8`、`V1`–`V6`、`G1`–`G14`、授权矩阵、白名单、受保护 blob 全部与基线一致）、
未删除或放宽任何既有验收义务；同时报出 4 处真实缺陷。**四处均已在提交前修复**：

| # | 缺陷（复核意见） | 整改 |
| --- | --- | --- |
| D1（中） | 验收 §1.2 的"组合入口不可达"清单把 `INPUT_DIGEST_MISMATCH` 与适配器 `IDENTITY_CONFLICT` 一并列为不可达，与本文 AC-17d、§10 第 4 项及设计 §8.5.1 的 S4 行冲突（实测：`synthetic.py:552` 的 `INPUT_DIGEST_MISMATCH`、`:537/:549` 的输入级 `IDENTITY_CONFLICT` 都可由 `bound_inputs` 在组合入口触发） | 重写该段：不可达清单只保留 `CONTRACT_PLAN_MISMATCH`、`ARTIFACT_DIGEST_MISMATCH`、`PLAN_TERM_ROLE_MISMATCH`、`MATRIX_DIGEST_MISMATCH`，并新增"注意不要过度归类"段，显式声明 `INPUT_DIGEST_MISMATCH`/适配器 `IDENTITY_CONFLICT`/`EVIDENCE_DIGEST_MISMATCH`/`ROLE_BINDING_MISMATCH` 仍由组合入口 S4 触发 |
| D2（低） | AC-12b 把门禁归属写成 G10，但改 `config` 会同时改变 `contract_digest`，S3 实际由 **G9** 先命中（两者同码，可观察行为相同） | AC-12b 改为"S3 的 `PIPELINE_INPUT_BINDING_MISMATCH`；通常由 G9 先命中（G10 与之同码）"；本证据文件同步更正 |
| D3（低） | 验收头部称"不新增、删除或放宽任何验收义务，只修正入口归属"，与本文实际 diff 不符（新增 AC-25 第 7 条、AC-22d 双路径、AC-28 关键断言第 4 条；AC-27 与 AC-29d 亦有更正） | 头部改为"不删除、不放宽任何既有验收义务，只按实测修正入口归属，并新增与更正直接对应的断言"，并逐项列出新增项 |
| D4（低） | 设计 §6.3 "它们是 `_` 前缀私有实现，不是 acceptance 入口"与新增的 `INTERNAL_PROJECTION_PROBE`（AC-17e）表述冲突 | §6.3 补充唯一例外：验收测试可在显式标注 `INTERNAL_PROJECTION_PROBE` 后调用 `_project_validated_matrix`；**编排器仍不得**调用 |

复核同时确认证据文件对 pytest 的汇报是诚实的（退出码 1、`185 passed, 2 errors`、点名两个
`tmp_path` 用例、明确不计为通过）。

## 5.2 残留风险与不可复核项

- 复核子代理**无法**独立复现两项：（a）schema 上界子代理的字节级测量
  （40,004 条 history → 5,870,359 字节等，本次未重跑 Python 探针；源码层面无上限已独立确认）；
  （b）`git add` 被拒的实际报错（该命令会变更 Git 状态，只读子代理不得重跑）。两者均由主代理
  在本会话实际执行并记录。
- 因沙箱不能提交，最终提交内容需 Codex 在宿主环境按白名单暂存；复核期间文档仍在被修正，
  因此**以宿主提交时的实际字节为准**（本文件不锁定哈希）。

---

## 6. 最终 Git 状态

- 分支：`codex/m4-synthetic-pipeline-design-correction`
- 起始 HEAD：`d69ba05fb35fb076f7f10e1e84c29bc1e9cff0a2`
- 成果提交：**未创建**（原因见下方"提交记录"）
- 推送：**未推送**；PR：**未创建**；合并：**未执行**
- `origin/main` 与 live main：`d3fcb1967e9e7f6d3caac3e3f08ea874646f3098`

### 提交记录

**未创建提交（环境性硬阻塞）**。实测：`git add -- docs/m4_synthetic_end_to_end_pipeline_design_v1.md
docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md
agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md
acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`
→ `fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-synthetic-pipeline-design-correction/index.lock':
Permission denied`（退出码 128）。该工作树的 Git 目录位于会话工作区之外；按规则以
`danger-full-access` 重试同一条命令一次，平台回复 "requires approval, but no approval channel is
available"——审批通道不可用，失败关闭。Goal 的停止条件明确禁止用替代 index / 替代 `GIT_DIR` /
重建仓库绕过，因此**未创建任何提交**；HEAD 仍为 `d69ba05fb35fb076f7f10e1e84c29bc1e9cff0a2`。
变更以待提交状态存在，路径与 Goal 白名单逐一对应，由 Codex 在宿主环境按显式路径暂存并提交。

---

## 7. 结论

七项必改均已落地于两份规范文件并给出来源证据；公开能力面、错误码集合、常量、schema、字段、
签名、L1–L14、S0–S8、V1–V6、上游契约与授权边界保持不变；受保护 blob、数据库、stash 与其他
工作树未被触碰；本地/远端同步状态与任务开始时一致。

两项未能在本会话闭合，且都属环境限制、均已如实记录：

1. **scoped 提交未创建**——沙箱拒绝写工作区外的 Git index，升级审批通道不可用（Goal 的停止条件
   禁止绕过），需 Codex 在宿主环境按白名单显式路径提交；
2. **Goal 第 2 条 pytest 命令以 1 退出**——`185 passed, 2 errors`，两个 error 是 `tmp_path` 用例的
   沙箱目录枚举限制（`PermissionError: [WinError 5]`），需 Codex 在宿主环境重跑。

除上述两项外，本次任务的内容与证据已就绪，等待 Codex 的独立仓库证据复核与最终裁决。

---

## 8. Codex 宿主独立复核与最终裁决

Codex 未采信 DSH 的完成摘要作为通过依据，而是在宿主环境独立完成以下复核：

- 按 4 条显式白名单路径创建成果提交
  `f997b95d2e4e35345b92757b29b6c9a36018231a`；未使用 `git add -A`，未推送。
- 使用独立可写 `--basetemp` 重跑治理组：`15 passed in 0.10s`，exit 0。
- 使用独立可写 `--basetemp` 重跑第 2 条完整上游组：`187 passed in 31.91s`，exit 0。
  因而 DSH 的 `185 passed, 2 errors` 已确认仅由沙箱 `tmp_path` 权限造成，不再是验收缺口。
- 重跑 `python -m ruff check src tests`：`All checks passed!`，exit 0。
- 独立检查实际分支/HEAD、提交和差异、changed/untracked、stash、数据库哈希、保护 blob、
  `origin/main`、live main、开放 PR 与 Goal 白名单；未发现非白名单或受保护面变化。
- DSH 遗留的 `.dsh-pytest-tmp/` 是 Git 不跟踪的测试临时目录，不进入提交；不影响仓库验收。

内容层七项必改全部有据，第四路对抗审查的 D1–D4 已全部闭环；没有 API、能力、错误码、摘要、
阶段、上游契约或授权边界扩张。允许推送本设计修正分支、创建 PR 并等待 CI；只有 PR 合并且 main
同步后，才允许另立新 Goal 恢复实现阶段。

**最终裁决：`PASS`**
