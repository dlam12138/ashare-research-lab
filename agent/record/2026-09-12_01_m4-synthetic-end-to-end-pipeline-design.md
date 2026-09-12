# 工作记录：M4 合成端到端流水线设计

## 基本信息

- 日期：2026-09-12
- 分支：`codex/m4-synthetic-pipeline-design`
- 基线：`origin/main@fd1cc35ee824aa9449f7e7800c12d0d80c845e05`
- Goal 提交：`f6ec598ac819c2d8db14f7a2e8c910a6ed85b301`
- Goal：`agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md`
- 最终设计审查：`PASS`

## 目标与边界

冻结一个仅内存、仅合成、确定性的 M4-A 端到端编排设计，组合已存在的合同编译、计划编译、
合成数据适配、矩阵物化和有界执行入口；可选 M4-B 记录只能作为只读元数据绑定。

本阶段不实现入口，不修改既有 M4 源码或测试，不接触真实候选、真实注册表数据、文献、provider、
数据库内容、真实行情或 holdout，不执行真实假设，不做回测、排名、推荐或交易结论。

## 实际过程

1. 独立核实 branch、HEAD、origin/main、live remote、worktree、stash、原始 M2 工作树、保护 blob
   与数据库 SHA256。
2. 从 PR #15 合并点创建独立 worktree 和分支；先建立并单独提交 Goal。
3. DSH 主 agent 使用四个受限只读子 agent：公共 API/组合审计、错误与摘要及授权审计、文档约定
   审计、对抗式设计审查。所有子 agent 继承 Goal 白名单和禁区。
4. DSH 创建设计、AC、README 更新和初始证据。第一次对抗审查返回 `CHANGES_REQUIRED`。
5. 根据证据修复：公共 `bound_inputs_identity_payload`、两遍输入协议、Decimal 局部上下文、
   bootstrap 绝对上界、`record_bytes_hex`、可绑定 registry 状态允许表、异常类型/错误码透传、
   摘要链、可达性分类与 AC-28/29/30。
6. 后续 DSH 复核继续发现并修复：公开面计数、`registry_record` 必填但可空语义、信封自摘要排除、
   `PIPELINE_DIGEST_MISMATCH` 闭合、G7–G11 时序、8.x 顺序、RB/BS 条款命名、AC 范围与资源引用。
7. 最终限定范围 DSH 复核返回 `PASS`，未发现未决 P0/P1 或实现阻断歧义。
8. DSH 测试沙箱产生的 `.pytest-tmp-stale/` 已由负责 reviewer 在核实绝对路径后删除；未使用
   `git clean` 或任何 broad destructive cleanup。

## 设计结果

- `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`：1,373 行；单一入口、不可变信封、
  S0–S8、G1–G14、14 个闭合错误码、L1–L14、V1–V6、M4-B 元数据绑定、确定性与资源边界。
- `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`：932 行；AC-01–AC-30，索引与
  正文各 30 项且完全一致。
- `README.md`：只更新设计状态、能力说明和授权边界；明确编排器尚未实现。
- `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md`：最终证据包。

## 验证结果

- 机械一致性：20 个公开符号且唯一；14 个闭合 `PIPELINE_*` 错误码；8.1–8.7 顺序正确；
  RB/BS 等条款无重复；AC index/body = 30/30；无畸形 Markdown 表格。
- 六组既有 M4 回归：Goal 原样命令因共享 venv editable install 指向旧 `m4a2i/src` 而在收集期
  失败；显式设置 `PYTHONPATH=<本工作树>/src` 后 **304 passed in 38.95s**。
- 项目入口与 Stage4P 治理：**15 passed in 0.19s**。
- Goal 原样 ruff 命令：`All checks passed!`。
- `git diff --check`：通过。
- Markdown 相对链接/锚点：通过，工作树无生成物残留。
- 五个保护 blob、数据库 SHA256、stash、原始 M2 HEAD 均未变。
- `git fetch --prune origin` 与 `git ls-remote` 成功；提交前 local/origin/live main 均为
  `fd1cc35ee824aa9449f7e7800c12d0d80c845e05`。

## 偏差与残余风险

- 共享 venv 的 editable install 指向旧工作树；这是任务前既存环境问题，且 venv 不在白名单内。
  因此同时保留 Goal 原样命令失败与当前源码显式绑定后 304 passed 的证据。
- 执行产物包含 `numpy.__version__`，跨 NumPy/BLAS 环境不承诺无条件字节一致；设计只承诺同一
  解释器、同一 NumPy 版本和固定 Decimal precision 下的一致性。
- 资源调用次数上界与公开 input-payload helper 的字节等价性须在后续实现 Goal 中实测。
- P4 的描述称 disposition 为 plan 字段，而冻结消息模板和 AC-06 使用真实权威路径
  `contract.evidence_rule.data_quality_failure_disposition`；两值按计划构造相同，实施以权威路径为准。

## 最终状态

设计阶段验收为 `PASS`。允许在正常 CI 全绿后推送、开 PR 和 merge；用户已给出该 standing
authorization。编排实现必须另建 Goal，且继续禁止真实数据、真实候选、文献、provider、数据库、
行情、holdout 与真实假设执行。
