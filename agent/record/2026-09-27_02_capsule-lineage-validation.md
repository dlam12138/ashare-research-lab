# Snapshot lineage validation

Goal: agent/goals/2026-09-27_capsule_lineage_validation.md.
Base 2471b87; branch codex/capsule-lineage-validation.
Observed validator loads lineage but never checks manifest lineage_count or
the fact-to-lineage references. Add structural checks and negative tests on
temporary copies only. Existing tracked fixtures remain unchanged.

Implemented lineage count, integer/unique ID, known fact ownership and exact
per-fact reference matching. Missing, duplicate, boolean and string declarations
are rejected. No schema/hash format changes; this is structural consistency,
not authentication against coordinated rewrites or validation of parent facts
outside the bounded snapshot.

PowerShell prerequisite: `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`.
Before fix `python -m pytest tests/test_capsule_lineage_validation.py -q`:
5 failures, 1 pass, confirming missing early validation.
After fix `python -m pytest tests/test_capsule_lineage_validation.py tests/test_stage2g_reproducibility.py tests/test_capsule_output_preservation.py -q`:
34 passed, 2 skipped (prior Windows real-symlink privilege tests).
`python -m ruff check tests/test_capsule_lineage_validation.py`: passed.
`git diff --check`: passed. DSH bounded read-only review found no concrete
blockers; it did not execute tests. Parent reran tests and independently reviewed
the diff and additional declaration cases.
Protected DB hash and stash unchanged. Only four scoped files changed;
no tracked fixture mutation. Local commit, no push/merge or next-stage launch.
