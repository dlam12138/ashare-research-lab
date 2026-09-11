## Project Governance

### Shared Source of Truth

- Git branches, commits, PRs, tracked Goal contracts, acceptance files, and actual test results are the shared source of truth.
- Every task must begin by verifying the real branch, HEAD, worktree, remote state, stash, relevant files, and protected baselines.
- Never rely only on a previous agent report or chat summary.
- Long or staged tasks must use the repository’s established Goal/task-contract path, preferably `agent/goals/*.md`, unless the repository already defines another canonical location.

### Required Task Contract

Before implementation begins, establish or verify:

- Objective
- Verified baseline
- Allowed scope
- Forbidden scope
- Required behavior
- Required tests
- Exact validation commands
- Acceptance criteria
- Stop conditions
- Commit and push requirements

### Final Review Duties

Before accepting a completed task, the responsible reviewer must independently inspect:

- actual branch and HEAD
- commit and diff
- changed and untracked files
- test evidence
- worktree and stash
- protected baselines and databases
- local/origin/remote synchronization
- Goal compliance
- acceptance evidence

Do not accept a completion summary without checking repository evidence.

The final verdict must be exactly one of:

- PASS
- CHANGES_REQUIRED
- BLOCKED

Do not automatically merge or start the next stage without explicit authorization.

### Git and Safety Rules

- Never push directly to `main`.
- Never force-push unless the task explicitly authorizes it.
- Do not use destructive cleanup commands such as `git reset --hard` or `git clean -fdx` without explicit user authorization.
- Do not weaken, delete, skip, or rewrite tests merely to obtain a passing result.
- Preserve unrelated user changes, stash entries, local databases, runtime data, and ignored artifacts.
- Hooks, if present, are deterministic permission and validation gates; they are not a cross-session communication bus.

### Final Evidence Packet

Every completed implementation task must report:

- Goal/task-contract path
- verified base branch and commit
- final branch and commit
- files changed
- implementation summary
- exact validation commands and results
- acceptance evidence
- worktree and stash state
- local/origin/remote synchronization
- deviations, blockers, and unresolved risks
- whether proceeding to the next stage is allowed
## Astra/Luna 路由入口

- 入口协议：[agent/agent.md](agent/agent.md)；路由说明：[agent/model-routing.md](agent/model-routing.md)。
- Astra 负责规划、约束审查和独立验收；默认由一个 Luna worker 以 medium 执行有界实现。worker 不得递归派工。
- 委派时显式指定 `gpt-5.6-luna` 与 `medium`，使用最小 fresh context；可用工具时传 `model=gpt-5.6-luna`、`reasoning_effort=medium`、`fork_turns=none`。命名 agent 不支持这些字段时，明确写出等价参数。
- 同一问题连续两次修复失败，或出现语义/保护边界冲突，升级给父代理。验收依赖实际工具证据，不重复全量测试，也不只采信 worker 报告。
- 交接与结果必须包含基线、写入路径、行为、测试、授权停止点、实际提交和证据；父代理完成规划审查与独立验收后再决定下一步。
- 保持本文件原治理、用户授权和运行时权限；禁止静默回退到更昂贵模型。配置仅作用于后续委派：主任务须由用户在界面选择 Astra，配置不会热切当前任务；主线合并后新工作树继承，旧会话/工作树不会自动更新。
- 本机制只提供规则与配置，不承诺硬权限隔离或真实 token 节省。
