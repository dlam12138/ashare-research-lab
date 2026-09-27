# Snapshot context validation

Goal: agent/goals/2026-09-27_capsule_context_validation.md.
Base 443b232, branch codex/capsule-context-validation, clean start.
Inspection: context IDs are converted to strings and a set, hiding duplicates.
Importer may reject conflicting rows only after creating the target DB; identical
duplicates can be ignored. Export selects referenced contexts only. Validate
that invariant before import, using temporary mutated copies, no fixture edits.

Implemented explicit nonempty string ID, duplicate rejection and exact context
coverage check. Existing missing-context error remains. No normalization, data
repair, schema change, or authenticity claim introduced.

PowerShell prerequisite: `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`.
Red: `python -m pytest tests/test_capsule_context_validation.py -q --tb=no`
returned 5 failures and 1 pass before implementation.
Green: `python -m pytest tests/test_capsule_context_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_output_preservation.py tests/test_stage2g_reproducibility.py -q`
returned 40 passed, 2 skipped (existing Windows symlink privilege limitation).
`python -m ruff check tests/test_capsule_context_validation.py`: passed.
`git diff --check`: passed. Parent independently inspected implementation and
exporter's referenced-context selection. Protected DB hash/stash unchanged.
PR #32 independently checked: OPEN, 42 checks successful, not merged.

Four scoped files changed. No tracked fixtures or other modules changed.
Local commit only. The three local capsule fixes now form one reviewable series;
prefer integration review/publication next, not additional speculative hardening.
DSH read-only review found no concrete blocker. It did not execute tests;
the parent-run results above are the test evidence.
