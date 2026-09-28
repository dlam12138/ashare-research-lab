# Capsule atomic publication

Date: 2026-09-28. User requested continued project progress.
Module: reproducible value-assessment infrastructure.
Goal: agent/goals/2026-09-28_capsule_atomic_publication.md.
Base: origin/main ae00efe7d5aa7cd592339b199c65281b9c1c441d.
Branch: codex/capsule-atomic-publication; clean separate worktree.

Inspected actual Git/worktree/remote/stash state, recent EIA and capsule records,
build_temp_fact_db and DuckDBStore lifecycle. Existing implementation writes
directly to final target and closes only after success. EIA request allowance
is exhausted; this task performs offline engineering only.

Plan: bounded worker implements private staging and atomic no-clobber publication,
with failure and competing-writer regression coverage. Parent independently
inspects changes, runs related tests, checks protected state and records outcome.
Hard-link publication avoids replacing a concurrent destination; unsupported
filesystems must fail explicitly. No rename/replace or destructive cleanup fallback.

User subsequently selected engineering stability and existing functionality.
Repository routing requires one gpt-5.6-luna/medium worker; assigned only the
implementation module and preservation tests, without commit/push authority.

Baseline verification on unchanged code in the v2 worktree: Goal's six-module
pytest command returned 88 passed, 4 skipped in 8.96s. Two skips are Windows
symlink privilege, two are unavailable real baostock snapshots. Scoped ruff passed.
Inspected callers in build_test_capsule and run_test_capsule: returned final path
and on-disk contents must remain compatible. No provider or real DB was opened.

## Implementation and independent acceptance

Verdict: PASS.

Changed build_temp_fact_db to construct in a private sibling TemporaryDirectory,
close DuckDBStore in finally, and publish the validated closed file with os.link.
FileExistsError is preserved for both early checks and concurrent destination
creation. Unsupported hard links raise an error without replacing any output.
Owned staging is cleaned on normal completion and handled exceptions.

Six new cases cover failure after schema creation, insertion failure, validation
failure, destination creation at publication, unsupported publication, and readable
success with 33 facts / 11 contexts / 33 lineage rows. Failure cases explicitly
assert the store is closed and no target or staging remains. No tests weakened.

Parent inspected actual implementation and test diffs and required preservation
of exception type plus stronger schema/close checks before acceptance.
Parent independently executed the Goal's exact six-module pytest command with
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`: 94 passed, 4 skipped in 19.57s.
The same two symlink-privilege and two missing-real-snapshot skips remain.
`python -m ruff check src/ashare_research/reproducibility/capsule.py tests/test_capsule_output_preservation.py`:
All checks passed. `git diff --check`: passed.

Protected database SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
stash remains cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f. Primary worktree status,
tracked diff and HEAD compared to captured baseline without changes.
No tracked fixture, schema, database, runtime or other worktree modification.

Final files: this record, Goal, capsule.py, test_capsule_output_preservation.py.
Delivery: scoped local commit on codex/capsule-atomic-publication; exact final
commit supplied in handoff (the commit contains this record).
Base/origin/main/live main: ae00efe7d5aa7cd592339b199c65281b9c1c441d.
Remote feature branch absent at verification; no push, PR or merge performed.
Final cached diff and clean status are checked after staging/commit.

Limitations: publication requires filesystem hard-link support; unsupported
filesystems fail closed. This is exception-safe publication, not power-loss
durability or hostile filesystem/path-mutation protection. Abrupt process death
can leave owned staging directories. Whole-capsule directory publication remains
outside scope. No real-market-data test or research-readiness claim is made.
No new research stage authorized or started; current engineering increment ends here.
