# Goal: keep database publication outcomes independent of cleanup failures

- Objective: an OSError during owned staging cleanup must not turn successful
  publication into failure or replace the primary build/publication exception.
  Emit a warning identifying retained staging so failed cleanup remains visible.
- Authorization: continued engineering stability; DSH default; standing reviewed
  scoped-PR merge authorization in AGENTS.md. No new research stage.
- Verified base: origin/main and live main cb56755a00f4d4529c6adb72d0c5229e02ebd652;
  clean new branch codex/capsule-cleanup-outcome, previous branch 8f6fe0b unchanged.
- Protected primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
  stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed: src/ashare_research/reproducibility/capsule.py,
  tests/test_capsule_output_preservation.py, this Goal and corresponding record.
- Required behavior: unchanged staging, close, validation, hard-link no-clobber
  publication and all early guards. Explicitly handle only filesystem OSError
  from owned TemporaryDirectory cleanup, log WARNING, preserve successful return
  and original exception. No overwrite fallback, target removal or broad exception
  suppression. Non-OSError programming/interrupt exceptions are not swallowed.
- Tests: inject PermissionError at real cleanup boundary after success (returned
  database readable/complete), during a build failure (original error preserved,
  no target), and publication failure (original failure preserved, competing target
  intact where applicable). Assert warning, ownership-only cleanup and normal
  cleanup remains. Tests manage their injected-failure leftovers safely.
- Forbidden: other modules, new features, schemas/fixtures/data changes, provider
  acquisition, real backtests, deleting unrelated runtime/ignored data, test weakening.
- DSH edit only implementation/test paths; no Git mutations, recursion or fallback.
  Parent owns independent review, validation, commit/push/PR/merge.
- PowerShell validation prerequisite: $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
- Exact parent commands:
  python -m pytest tests/test_capsule_output_preservation.py tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_stage2g_dividend_correction_and_valuation.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
  & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
  git diff --check; git diff --cached --check
- Acceptance: baseline defect reproduced, regression and compatibility tests pass
  with explicit skips, precise diff reviewed and protected state unchanged; hosted
  checks all pass on exact PR head before expected-head guarded merge.
- Stop on scope conflict, regression, failed hosted checks or two failed repairs.
  Report DSH environment failures; never silently substitute another worker.
- Delivery: scoped commit/task-branch push/one PR and merge under standing
  authorization. No main push, force push, branch deletion or next research stage.
