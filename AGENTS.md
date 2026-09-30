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

Standing user authorization (2026-09-28): automatically merge task-scoped PRs
after independent review, successful required checks and verification of the
expected head and mergeability. Do not request per-PR confirmation. This applies
to engineering, evidence and governance PRs within the user's authorized scope,
including the PR recording this rule. It supersedes historical per-PR approval
stop points, but not their data, research or safety restrictions. Stop on failed
checks, conflicts or scope expansion; never bypass protections to merge.

Starting the next stage still requires authorization; existing continuing
authorization applies only within its stated scope. Automatic merging does not
authorize new data acquisition, real backtests, holdout use, force pushes or
destructive operations.

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
## 默认子任务执行器：DSH

- 入口协议：[agent/agent.md](agent/agent.md)；路由说明：[agent/model-routing.md](agent/model-routing.md)。
- 按用户明确要求，默认子任务执行器为 DSH；父代理负责规划、确定 Goal、约束审查和独立验收，并在目标工作树通过 `dsh --profile headless` 委派一个有界 DSH 任务。
- 交接必须包含分支与提交、Goal、允许与禁止范围、验证命令、授权停止点及回报格式，并使用最小充分上下文。DSH 不得递归派工；只有任务明确授权时才可修改指定文件，否则只读。
- DSH 不可用、执行失败或同一问题连续两次修复失败时，向父代理报告；禁止静默改用 Luna 或其他模型替代。
- 验收依赖实际工具证据，父代理保留 Git 操作与独立验收职责，不重复全量测试，也不只采信 DSH 的完成报告。
- 保持本文件原有治理、用户授权（含长期合并授权）与运行时权限；路由规则仅作用于后续委派，不追溯改写历史执行记录，也不承诺硬权限隔离或真实 token 节省。
