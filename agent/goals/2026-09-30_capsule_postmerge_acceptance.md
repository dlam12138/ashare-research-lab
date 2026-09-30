# Goal: independently accept the merged capsule safety baseline

- Objective: verify PR #36 delivery and the composed capsule safety behavior on
  the actual merged main commit, and record any actionable remaining defect.
- Authorization: user requested continuation; bounded engineering acceptance only.
  Use the repository DSH route for one read-only review. No new research stage.
- Verified baseline: origin/main and live main
  209b06c3507e9def970b43bcdc5ce03a61b223fc; new isolated branch
  codex/capsule-postmerge-acceptance, initially clean.
- Protected primary branch feat/m2-value-assessment-mvp at
  3679b1bac7a1634c6452784a4d8f6d139966f222, including all pre-existing dirty
  and untracked files; stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
  research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed changes: this Goal, corresponding agent/record, and acceptance file.
  Read code/tests/committed evidence; test writes confined to owned temporary
  paths. Parent owns all Git operations. DSH has no write or Git authority.
- Forbidden: source/test/fixture/frozen-contract edits, provider acquisition,
  real data, research execution, holdout, primary worktree changes, cleanup of
  existing runtime data, branch deletion, direct main push, forced operations.
- Required behavior: check no-clobber publication, cleanup exception semantics,
  manifest inventory and input bindings against actual callers and regressions;
  separate observed behavior from unsupported authenticity/path-race guarantees.
- Required tests: nine focused capsule/caller modules below, run once by parent;
  pinned Ruff; whitespace checks. Existing platform/input skips must be explicit.
- Exact validation commands (PowerShell in the isolated worktree):
  $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
  python -m pytest tests/test_capsule_output_preservation.py tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_stage2g_dividend_correction_and_valuation.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
  & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
  git diff --check
  git diff --cached --check
  gh pr view 36 --json number,state,headRefOid,mergeCommit,statusCheckRollup,url
  git ls-remote origin refs/heads/main
- Acceptance: actual PR merge/head verified, all hosted checks successful; focused
  tests pass; independent source review has no blocking regression; protected
  primary status/diff/HEAD, DB and stash preserved; product/frozen paths unchanged.
- Stop conditions: failed checks, reproducible defect, scope conflict, DSH failure
  or protected-state change. Report findings; do not silently substitute workers.
- Commit/push: make one local evidence-only commit after review. No push/PR/merge
  is required for this acceptance task; report local-only synchronization exactly.
  Do not automatically begin another implementation or research stage.
