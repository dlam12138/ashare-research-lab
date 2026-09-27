# Capsule output preservation

Goal: agent/goals/2026-09-27_capsule_output_preservation.md.
Baseline main 4787968, clean codex/capsule-output-preservation branch.
Inspection found build_temp_fact_db unconditionally unlinks existing output,
unlike the enclosing build_test_capsule, which rejects existing output.
Plan: reproduce using synthetic temporary targets, add early refusal, verify
compatibility using existing offline fixtures. No real database opened.

Implementation: reject target.exists() or target.is_symlink() before snapshot
validation and directory creation; remove unlink. Existing callers create fresh
paths or explicitly reuse an already-built capsule DB, so no overwrite option
is needed. Existing outputs are untouched. Concurrent-writer races remain out
of scope; this is an accidental-overwrite fix, not an atomic publication design.

Validation (PowerShell, set `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`):
- Initial pytest without PYTHONPATH failed import; no tests executed in that run.
- Before fix: `python -m pytest tests/test_capsule_output_preservation.py -q`
  produced 2 expected failures, 1 pass, 2 Windows symlink-privilege skips.
- After fix: `python -m pytest tests/test_capsule_output_preservation.py tests/test_stage2g_reproducibility.py -q`
  produced 23 passes, 2 skips. Real symlink tests remain enabled on capable
  systems; a portable mocked dangling-link branch test also passes.
- `python -m ruff check tests/test_capsule_output_preservation.py`: passed.
- `git diff --check`: passed.

Parent reviewed actual diff and both production callers. Protected DB SHA256
and stash match Goal; unrelated dirty M2 worktree and EIA branch preserved.
Four scoped files: capsule.py, dedicated tests, Goal and this record.
Local commit only; no push, merge, data acquisition or new research stage.
DSH completed bounded read-only review with verdict PASS; did not rerun tests.
Parent test outputs above provide execution evidence; staged whitespace check
covers the newly added files before commit.
