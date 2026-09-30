# Capsule runtime database isolation

Date: 2026-09-30. Module: reproducible value-assessment infrastructure.
Goal: agent/goals/2026-09-30_capsule_runtime_db_isolation.md.
Source: user requested continuation after CHANGES_REQUIRED audit.
Base branch codex/capsule-postmerge-acceptance at 217c45fe53c2be978848d4f3f11d1295d4b2a4f7.
New branch codex/capsule-runtime-db-isolation, same isolated worktree.
Remote main 209b06c3507e9def970b43bcdc5ce03a61b223fc, verified live.

Reviewed actual branch/HEAD/status/worktrees/remote/stash/protected DB hash,
AGENTS.md, agent agreement/routing, latest three records, previous Goal and
acceptance evidence. Actual run_test_capsule still reuses root/temporary_fact.duckdb
while declaring verified snapshot inputs. Existing binding test hardcodes that
old path; retain its assertions and strengthen runtime ownership assertions.

Plan: DSH implements a fresh owned runtime database and bounded regressions;
parent independently inspects actual diff, reproduces baseline with new tests,
runs required focused suite and pinned lint, verifies protected state and commits
locally. No new acquisition, research, frozen-contract or builder changes.

Decision: rebuilding from the verified snapshot avoids an additional semantic
cache validator and platform-dependent DuckDB byte hashes. Capsule cache remains
untouched. Per-run overhead is bounded by the existing 33-fact synthetic fixture;
large real-data execution is outside this API's authorization. Cleanup filesystem
errors remain visible as warnings and do not mask run outcomes.

Implementation/validation pending. DSH may edit only three Goal-listed source/
test files, no Git or test execution; parent handles exact validation because of
the known DSH temporary-directory ACL limitation. No tests claimed yet.

## Baseline reproduction

Parent reran the real synthetic revenue-tampering probe before any DSH source
edits. Wrapped the real run_formal to capture facts read by _load_canonical_facts,
then invoked the real formal runner and artifact verifier. Six revenue facts
were doubled only in the synthetic cached DB; portable manifest remained valid.
Exit 0: consumed_verified_snapshot_values=false, consumed_cache=true,
cache_preserved=true, runtime_db_exists_after_return=true, runner_status=pass,
artifact_verification=pass. All probe files lived in an owned TemporaryDirectory.
The same probe command will run after implementation to check changed behavior.

## Implementation and first validation

DSH implementation task exited 0, edits frozen: runner module, new runtime
isolation tests, strengthened existing binding-test ownership assertion only.
It ran syntax/import and scoped Ruff checks, no pytest. Parent reviewed actual
diff and all new tests rather than adopting its unexecuted behavior claims.

Parent reran identical real revenue probe on the new implementation: exit 0,
consumed_verified_snapshot_values=true, consumed_cache=false, cache_preserved=true,
runtime_db_exists_after_return=false, runner_status=pass, artifact_verification=pass.
Six original revenue facts consumed despite altered cached values.

Parent loaded the verified 217c45f runner source in memory and ran the new
test_changed_snapshot_values_are_consumed_and_cache_is_untouched regression:
expected exit 1, one assertion failure (consumed old cache value 9216100 rather
than verified snapshot value 9216101). Worktree source was not rolled back.

Exact Goal pytest command: 3 failed, 210 passed, 4 skipped in 102.09s. All three
failures were new real-run byte comparisons using differing run IDs. Actual
summary JSON/Markdown include run_id, so identical inputs with different IDs
are deliberately not byte-identical. Existing test_stage2g_reproducibility uses
the same ID in different roots. Source, cache-protection and fresh-lifecycle
assertions passed. Parent pinned Ruff src/tests passed; whitespace passed.

One precise DSH repair delegated: use the same baseline run ID in compared
real runs, retain all comparisons/cache assertions, and put injected cleanup
test ownership cleanup in finally. Only the new test file authorized; no product
or comparator change. Parent will rerun that module only after the repair;
unchanged compatibility modules already passed in the Goal run.

DSH precise correction exited 0 and froze only the new test module. Parent
confirmed summary.json/run_manifest.json differed only by run_id, and summary.md
only by its Run ID line. All checksum/comparison assertions retained; no source
or comparator edit. Cleanup tests now release only recorded owned directories
in finally, clearing tracking references.

Targeted repair validation:
`python -m pytest tests/test_capsule_runtime_db_isolation.py -q -rs`:
14 passed in 16.57s. Pinned Ruff src/tests and whitespace passed again.
Source/binding-test hashes match those used by the earlier compatibility run.
Parent is performing one final retry of the exact Goal focused command so the
contract has an exit-0 result on the final file state; not a full offline-suite
rerun or a broader test expansion. Original three failures remain documented.

## Final independent acceptance

Verdict: PASS. Final exact ten-module focused pytest command from Goal exited 0:
213 passed, 4 skipped in 102.78s. Skips unchanged: two unprivileged symlink cases,
two absent real-baostock snapshot cases. No weakening/extra skips. Final pinned
Ruff src/tests passed; git diff --check and git diff --cached --check passed.
Parent inspected actual source/test diff and all six staged paths; new tests
keep cache protection, input semantics and artifact byte-comparison assertions.

Validated SHA256:
- runner 5dbcfe4b722354b39e3db95bbe58b5cde4673ddb62a12291d98be2e9d10d1c5e
- new tests 903114667a8490d27fed1f436d2a27d7b5ce66fb788916ecb01dfe935993dcee
- binding tests e2db6f7f1c6afe519acde051ef8db55b2b7b3cf553794cb3d2d6a5ecd3706abc

Protected primary status/binary diff/HEAD/stash compare exactly to start state;
research.duckdb SHA256 unchanged. Live remote main and origin/main remain
209b06c3507e9def970b43bcdc5ce03a61b223fc. Local main 966206f in its separate
worktree was preserved. No source changes beyond the runner, no builder,
fixture/research-contract/report/provider changes or real inputs acquired.

Six repair files: runner, new runtime isolation tests, strengthened binding
tests, Goal, this record and acceptance document. Local scoped commit only;
final commit identity/clean state/live synchronization independently checked
after commit and reported in final handoff. Prior audit commit retained.
No push/PR/merge or new stage authorized by this Goal. The remote main still
needs this local fix integrated before it has the repaired behavior.

Remaining limits: owned runtime cleanup OSError can retain temporary files,
with warning; non-OSError and logging failures propagate. Concurrent portable
input mutation/provenance authentication remain excluded. Rebuild per run is
intentional and bounded. All injected-failure temporary directories in tests
cleaned using recorded owners; normal ignored test/lint caches preserved.

Staged evidence whitespace gate initially found a trailing blank line in the
new acceptance document. Removed it before final checks/commit; no code/test
change. The final gate result below, not that initial warning, governs acceptance.
