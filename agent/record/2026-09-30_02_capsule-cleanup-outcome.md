# Capsule cleanup outcome

Date: 2026-09-30. Goal: agent/goals/2026-09-30_capsule_cleanup_outcome.md.
Module: reproducible value-assessment infrastructure.
Base origin/main/live main cb56755a00f4d4529c6adb72d0c5229e02ebd652.
Working branch codex/capsule-cleanup-outcome, initially clean.

Reviewed actual Git/worktree/remote/stash state, current DSH rule, prior records,
build_temp_fact_db and preservation tests. Integration review identified that
TemporaryDirectory.__exit__ can raise after os.link succeeds, or mask a primary
build error. Plan: DSH makes bounded outcome-preserving cleanup handling/tests;
parent independently reproduces baseline, validates diff and required tests, then
publishes/reviews/merges only after hosted checks. Owned cleanup failure must
remain observable as a warning and must never delete or overwrite final output.
Protected DB/stash/primary changes remain untouched. No new research/data work.

Implementation and local validation completed; hosted delivery evidence follows
in GitHub PR/final handoff after exact-head checks.

Parent baseline reproduction loaded `git show cb56755:src/ashare_research/reproducibility/capsule.py`
in memory, injected PermissionError at TemporaryDirectory.cleanup, and called
builder on committed fixture in an owned TemporaryDirectory. Baseline raised
the injected cleanup failure after publication; readonly DuckDB query confirmed
33 facts in final target. Original cleanup then removed only test-owned staging.
Exit 0, defect reproduced. DSH task launched with only code/test write authority;
pytest explicitly left to parent due known DSH temporary-directory ACL limitation.

## Implementation and local independent acceptance

Local verdict: PASS. DSH exited 0, modified only capsule.py and preservation
tests, froze edits; did not run pytest or mutate Git. Parent inspected full actual
diff. Explicit TemporaryDirectory lifecycle now isolates cleanup OSError in a
finally block and logs WARNING with owned staging path. Other cleanup exceptions
propagate. Successful return and primary build/publication errors are preserved;
store close, no-clobber link, early guards and normal cleanup remain unchanged.

Five regression cases inject real rmtree-boundary failure: successful readable
33-fact/11-context/33-lineage DB, original insertion failure, competing target,
unsupported link, and unsuppressed non-OSError programming error. Tests clean only
their injected retained staging with captured real rmtree; no existing tests deleted.

Parent exact commands (PYTHONPATH absolute src):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/test_capsule_output_preservation.py tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_stage2g_dividend_correction_and_valuation.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
git diff --check
```

Results: 199 passed, 4 skipped in 71.52s; pinned Ruff 0.13.2 all checks passed;
whitespace passed. Two symlink-privilege skips and two missing-real-snapshot skips
remain unchanged. No provider input fetched or test condition weakened.

Validated file SHA256:
- capsule.py 853a04254c4ed1864137a3deebae35199b43d475ac875712ae146afd6c72ce96
- preservation tests a32b5925b027e4e6e2bcd1c4f5505e0ee28e513f92401abe290a32241e6c4f40

Protected DB SHA256 remains 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
stash remains cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f. Primary status, tracked
diff and HEAD exactly match captured baseline. Prior ignored runtime scratch
preserved; this task created no untracked diagnostic runtime tree.

Changed files: capsule.py, preservation tests, Goal and this record (four files).
Delivery branch codex/capsule-cleanup-outcome; base origin/main cb56755a00f4d4529c6adb72d0c5229e02ebd652.
Scoped commit/push/PR under standing authorization. Hosted CI must be entirely
green on exact published head, with unchanged base and expected-head merge guard.
Final PR/head/merge identities, clean-state and live remote checks supplied in
final handoff and PR acceptance evidence; no direct main push or branch deletion.

Remaining limits: failed cleanup may leave owned staging, reported by warning;
caller-controlled handler/logging failures are not newly suppressed. Non-OSError
programming failures intentionally propagate. No power-loss, provenance or hostile
path mutation guarantees added. No new research stage or real-data work started.
