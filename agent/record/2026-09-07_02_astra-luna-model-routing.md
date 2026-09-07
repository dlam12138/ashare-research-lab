# Work record: Astra/Luna routing

Date: 2026-09-07. Parent: Astra. Module: engineering governance.
Goal: [contract](../goals/2026-09-07_astra_luna_model_routing.md).
Base: 349101a; branch codex/astra-luna-model-routing; isolated worktree.
Verified original dirty M2 status, stash, DB, worktrees, remote main and open PR #9.
Read existing agent agreement, record index/recent records and official subagent schema.
Preserve the user's original untracked AGENTS.md; introduce its governance in the new tree.

Plan: one explicitly selected Luna writes bounded routing documents/config; Astra independently
checks installed runtime support, protected state and final changes. No duplicate implementation.
Read-only runtime checks and delivery evidence follow below.

## Actual work and decisions
- Spawned one worker explicitly as gpt-5.6-luna / medium / fork_turns=none. Worker owned
  four routing files while parent checked CLI compatibility and protected-state acceptance.
- First worker turn hit its usage limit after draft creation. User said "继续"; resumed
  the same Luna, without duplicating implementation or silently changing models.
- Independent review asked Luna to expand worker scope beyond docs/config, add a concrete
  worktree/Goal handoff, and separate unconditional test protection from commit authorization.
  Luna completed these bounded corrections and did not commit or push.
- CLI 0.153.4 recognizes project routing defaults via normal app-server config/read.
  Effective model/effort/concurrency exactly match Luna/medium/1; project layer is enabled.
- Strict-mode probe failed on unrelated global mcp_servers.fetch.type, so no global config
  was changed. Normal loader is the effective-client check. Prompt rendering verifies root
  instructions only; custom agent discovery is not inferred from a message-only debug view.
- TOML/entry/permission validation and diff checks passed. Existing focused entry and
  protected aggregate tests: 15 passed. No local full-suite duplication for docs/config only.
- Original dirty M2 worktree, all prior branches/worktrees, stash and database preserved;
  product/test/research/README/workflow/dependency diff remains empty.

## Handoff
Exact commands, observed probe limitations, changed files and protection values are in
[acceptance](../../acceptance/2026-09-07_astra_luna_model_routing.md).
One scoped commit and feature PR follow local review. Final HEAD, synchronization and CI
will be recorded in the PR body, without repeated evidence commits. No PR merge is authorized.
