# 工作记录：M3 Stage 3C-A-R canonical recovery and M2 branch repair

## 基本信息

- 日期：2026-08-21
- Agent：Codex
- 当前分支：`repair/m3-stage3ca-canonical-recovery`
- 开始提交：`987caffe5b75fa3b0de58d0add43051cc9a55d17`
- 任务来源：用户提供的 M3 Stage 3C-A-R recovery contract
- 对应模块：机制验证 / 工程治理 / Git recovery

## 任务目标

在隔离 worktree 将错误落在 M2 分支的 Stage 3C-A 实现恢复到 canonical
M3，绑定真实有效的 Stage 3A/R1/R2/R4 文件 SHA，完成 synthetic-only 验收，
再在独立 worktree 用审计式 revert 恢复 M2 文件树到 `241c180` 内容身份。

## 开始前状态

- `git fetch origin --prune` 已执行。
- `origin/feat/m3-mechanism-validation-mvp` = `987caffe`。
- `origin/feat/m2-value-assessment-mvp` = `3679b1b`，错误链完整可见。
- 原 M2 worktree 保持 dirty/untracked/stash；没有切换或修改它。
- 新 M3 recovery worktree clean，HEAD 与 canonical remote `0/0`。
- canonical M3 已有 Stage 3B/R1-R4 数据准备模块和 `Stage3BContractError`；
  不能覆盖 package exports 或数据层。

## 非目标

不读取真实外部 raw/cache、601857 development outcome、真实 1902-row
matrix、真实 Crash/gamma/CI；不执行 Stage 3C-B；不解封 holdout；不重新获取
market/oil/industry；不 cherry-pick incident commits；不 reset/force-push。

## 实施计划

1. 审计 canonical M3 文档、上游 contracts/reports 与现有机制 package。
2. 建立真实 upstream SHA inventory 和 v2 recovery contracts。
3. 逐文件审查并集成候选分析实现，保护 Stage 3B exports。
4. 增加 recovery-specific tests，运行 M3 boundary/full/synthetic validation。
5. M3 local/final-tip CI 成功后，隔离 revert M2 并验证 tree identity。
6. 更新 acceptance/record，推送两个 feature branch，清理仅本任务创建的 worktrees。

## 当前决策

- 候选 M2 实现只通过 `git show`/文件级复制审查，不 cherry-pick。
- v1 M2 contracts 不复用；canonical recovery 使用 v2 并绑定实际 canonical
  bytes SHA。
- upstream identity、path、contract_id、version、SHA、effective/superseded
  status 必须同时记录；缺失或不匹配 fail-closed。

## 实际操作

已执行：`git fetch origin --prune`、remote tip 与事故链验证、canonical M3
recovery worktree 创建与 clean/0-0 验证；读取 canonical `CLAUDE.md`、
`agent/agent.md`、`agent/record/README.md`、README、Stage 3A/R1-R4 reports、
M3 boundary tests 和现有 mechanism package。候选实现通过 `git show` 逐文件
审查和移植，未 cherry-pick 事故提交；未访问真实数据输入。

已重写为 canonical recovery v2 的 contract/record 绑定实际文件 SHA-256；
新增 fail-closed inventory 校验，保留 Stage 3B exports，并只增加
`statsmodels>=0.14.6,<0.15`。

## 验证

- focused Stage 3C-A/recovery：`50 passed`
- explicit M3 Stage 3A/R1/R2/R3/R4/recovery boundary：`183 passed`
- canonical full suite：`2106 passed, 3 skipped`
- M2 protected-boundary checks：`110 passed`
- Ruff、compileall、`git diff --check`：通过
- statsmodels：`0.14.6`
- positive/null/negative/extreme synthetic smoke：通过；development gate
  在输入访问前返回 `REAL_ANALYSIS_NOT_AUTHORIZED`；holdout sealed
- `PIPELINE_DIGEST`：`f667598001e8f63734547f7da281c41cf571c70667d784e35e57b6eddd4e781b`
- `MODEL_DIGEST`：`28154ef29ac86984042c18d9d39292dd3d85ffa44450ef98d8f02add23b2ef11`

## CI 与 M2 cleanup 状态

本地 canonical M3 验证已完成；M3 final-tip CI 尚未运行/确认，因此 M2
revert 尚未开始，符合任务要求。待 M3 CI 在最终提交上全绿后，才创建
独立 M2 worktree，按逆序执行四个 `git revert --no-commit` 并验证 tree
与 `241c180` 完全一致。原 M2 dirty worktree、stash、数据库和既有 M3
worktree 持续保持 protected。

## 结果/遗留问题

当前状态为 recovery implementation local PASS、等待四次 canonical commit
与 M3 final-tip CI；Stage 3C-B 未开始，holdout 仍 sealed，真实 development
analysis 未执行。
