# Goal: bind capsule execution to a fresh snapshot-derived database

- Objective: close the reproduced cached-DuckDB input mismatch in run_test_capsule.
- Authorization: user said continue after the post-merge audit identified this
  defect. Bounded engineering repair, using DSH; no new research/data stage.
- Verified base: clean codex/capsule-postmerge-acceptance at
  217c45fe53c2be978848d4f3f11d1295d4b2a4f7; new repair branch
  codex/capsule-runtime-db-isolation at that commit. Remote main/origin/main
  209b06c3507e9def970b43bcdc5ce03a61b223fc; preceding audit is one local commit.
- Protected primary branch/HEAD: feat/m2-value-assessment-mvp at
  3679b1bac7a1634c6452784a4d8f6d139966f222, all dirty and untracked files retained.
  Stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f. research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed product paths: src/ashare_research/tools/stage2g_reproducibility.py,
  tests/test_capsule_runtime_db_isolation.py, and the existing path-specific
  assertion in tests/test_capsule_input_bindings.py (replace with stronger
  isolated-lifecycle assertions). Parent also writes this Goal, record and a new
  acceptance document. DSH edits only those three product/test paths.
- Required behavior: verify capsule manifest before any runtime build/output;
  always construct a fresh database from verified snapshot in an owned temporary
  directory outside the capsule. Run formal processing and artifact verification
  while that database exists. Never read, change, recreate or delete the capsule's
  existing temporary_fact.duckdb, including invalid/foreign/missing caches.
  Preserve declared input hash/count, normal outputs, repeated-run reproducibility
  and current no-overwrite protections. No source/default DB inference.
- Cleanup: remove only task-owned runtime directory after success or error. An
  OSError from cleanup logs warning with retained path, preserving result/primary
  error as in the existing capsule builder. Do not swallow non-OSError errors.
- Required regressions: changed fact values, missing/additional facts, changed
  contexts/lineage, foreign/corrupt and missing cache; consume original snapshot
  contents and preserve cache bytes. Repeated runs use different fresh paths and
  return compatible results. Build/run/artifact failures preserve primary errors
  and clean owned paths without deleting pre-existing outputs/cache. Test outer
  cleanup OSError handling. At least one real formal-run regression; existing
  valid build/run/compare compatibility tests retained.
- Forbidden: capsule.py/builder changes, financial/research methods, schemas,
  fixtures, frozen contracts, provider calls, real inputs, holdout, test weakening,
  unrelated paths, primary worktree mutation, existing runtime cleanup, recursion
  or worker substitution. Parent owns Git and independent validation.
- Exact parent validation, PowerShell in this worktree:
  $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
  python -m pytest tests/test_capsule_runtime_db_isolation.py tests/test_capsule_output_preservation.py tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_stage2g_dividend_correction_and_valuation.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
  & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
  git diff --check
  git diff --cached --check
- Acceptance: parent reviews actual implementation/regressions, reproduces old
  behavior and verifies new behavior on committed synthetic inputs; required
  commands pass with explicit existing skips; protected primary/DB/stash and
  forbidden paths unchanged. Audit defect is superseded by new repair evidence,
  historical audit is not rewritten as a passing result.
- Stop: scope conflict, failed validation after two repairs, DSH unavailable or
  failed, protected-state drift; report honestly, no silent worker fallback.
- Delivery: one scoped local repair commit, including Goal/record/acceptance.
  No push/PR/merge required. Report local-only synchronization and current remote
  state accurately. No automatic next stage; further research remains unauthorized.
