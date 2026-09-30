# Goal: integrate capsule safety fixes and persist DSH routing

- Objective: deliver the three locally reviewed capsule fixes as one scoped PR,
  and remove stale Luna default routing that contradicted the user's DSH requirement.
- Authorization: user continued engineering work; verified standing authorization
  in agent/goals/2026-09-28_standing_merge_authorization.md covers reviewed scoped
  PR merging. This integration contract supersedes prior local-only delivery stops
  for these fixes, not any data/research restrictions. No new research stage.
- Verified start: clean codex/capsule-input-bindings@3fe0e764e8989af83ef957568fcfe4bb3da9d127,
  containing d2f62da and 43bf859. Initial origin/live main ae00efe7d5aa7cd592339b199c65281b9c1c441d.
  Governance PR #34 head 02a451861da9b3c74fb9ecf9c250303b385e61f0 reviewed:
  exact textual diff, clean tree, remote head matches, 42 SUCCESS checks, mergeable.
- Work branch: codex/capsule-safety-integration. Integrate live main normally;
  no force push/rebase of existing commits or direct main push.
- Protected primary M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
  stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; DB SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed new writes: AGENTS.md route section, agent/agent.md route section,
  agent/model-routing.md, this Goal/record. Existing capsule code/tests included
  unchanged. DSH may edit only the three route documents and review code read-only.
- Required behavior: default executor DSH through dsh --profile headless; parent
  plans/bounds/reviews and owns Git. No built-in Luna substitution, recursive
  dispatch, model hot-switch claim or rewritten historical records. Retain all
  other governance, permissions, evidence and research restrictions.
- Forbidden: new product code, tests weakened, fixture/schema/data changes,
  provider calls, real backtests, holdout, destructive cleanup, secret/runtime push.
- Validation: DSH bounded route edit plus read-only integrated safety review;
  parent inspect cumulative code/test/doc diff and exact route text;
  & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
  (verified Ruff 0.13.2 as pinned); git diff origin/main...HEAD --check;
  git diff --cached --check. Prior exact related suite at unchanged product hashes:
  181 passed, 4 skipped; rerun only if product changes or concern appears.
  Remote CI must pass all applicable checks for exact published head before merge.
- Acceptance: scoped PR complete/green, expected-head guarded merge, clean worktree,
  protected state unchanged, origin/live synchronization verified, no next stage.
- Stop on DSH failure, review blocker, scope expansion, conflict or failed checks.
  No bypassing protections. Parent commit/push task branch, create PR, verify CI,
  merge under standing authorization. No branch deletion.
