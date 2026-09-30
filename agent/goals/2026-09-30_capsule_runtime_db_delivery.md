# Goal: publish and independently accept the capsule runtime database repair

- Objective: deliver the already locally validated runtime DB isolation fix and
  its audit evidence through one reviewed PR to main, then verify synchronization.
- Authorization: user requested continuation after local repair; reviewed
  engineering PR delivery and merge under standing user authorization recorded
  in AGENTS.md and merged PR #34. This supersedes the prior local-only delivery
  stop for this handoff, without rewriting historical contracts or results.
- Verified base: remote main/origin/main
  209b06c3507e9def970b43bcdc5ce03a61b223fc; clean repair branch
  codex/capsule-runtime-db-isolation at
  57e710c818774c0e7c31c36bfc2d995e62e397fc. New delivery branch
  codex/capsule-runtime-db-delivery at the repair commit; prior audit 217c45f
  retained. Scope relative to main is the existing nine audit/repair files plus
  this delivery Goal, corresponding record and delivery acceptance document.
- Protected primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222,
  all existing dirty/untracked files and user worktrees; stash
  cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed new changes: this Goal, agent/record/2026-09-30_05_capsule-runtime-db-delivery.md,
  acceptance/2026-09-30_capsule_runtime_db_delivery.md. Parent owns scoped
  commit/push/PR/merge and optional clean fast-forward of this delivery worktree.
  DSH receives one read-only independent audit, no edits/tests/Git mutations.
- Required behavior: retain exact accepted source/test bytes; inspect cumulative
  code and regression diff, original defect/repair evidence and unchanged frozen
  paths. Validate focused regression and pinned lint once, verify all hosted
  checks on exact published PR head, actual mergeability and unchanged base before
  guarded merge. Record actual PR/head/merge identities in final handoff/PR evidence.
- Forbidden: product/test/fixture/contracts changes, method or schema edits,
  real inputs/provider requests/backtests/holdout, primary/stash/runtime cleanup,
  direct main push, force push, branch deletion, history rewrite or next stage.
- Exact local validation (PowerShell in this worktree):
  $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
  python -m pytest tests/test_capsule_runtime_db_isolation.py -q -rs
  & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
  git diff --check
  git diff --cached --check
  git diff origin/main...HEAD -- src tests
  Get-FileHash -Algorithm SHA256 -LiteralPath @('src/ashare_research/tools/stage2g_reproducibility.py','tests/test_capsule_runtime_db_isolation.py','tests/test_capsule_input_bindings.py','D:/量化分析/data/research.duckdb')
- Prior ten-module acceptance is 213 passed / 4 explicit existing skips on repair
  57e710c. Reuse only after exact source/test hash equality; do not rerun the full
  local offline suite for a docs-only delivery. Hosted workflows gate exact head.
- Exact delivery commands after acceptance: git push -u origin codex/capsule-runtime-db-delivery;
  gh pr create --base main --head codex/capsule-runtime-db-delivery --title <reviewed-title> --body-file <owned-temp-file>;
  gh pr view <PR> --json state,headRefOid,baseRefOid,mergeable,statusCheckRollup,mergeCommit,url;
  gh pr merge <PR> --merge --match-head-commit <verified-head>;
  git fetch origin; git ls-remote origin refs/heads/main refs/heads/codex/capsule-runtime-db-delivery.
- Acceptance: DSH and parent independent review have no blockers, exact bytes
  match tested repair, local checks pass, hosted checks all SUCCESS on exact head,
  PR merged under expected-head guard, remote main contains repair and delivery
  evidence, protected state unchanged; final task worktree clean and refs reported.
- Stop on failed checks, head/base drift, conflict, scope expansion, DSH failure
  or protected-state drift. No bypass or silent worker substitution.
- Delivery: one evidence-only commit atop existing audit/repair, push task branch,
  one PR and guarded merge under standing authorization. No extra commits after
  successful CI merely to self-record commit hashes. Final results reported in
  final handoff and PR evidence; no automatic new implementation/research stage.
