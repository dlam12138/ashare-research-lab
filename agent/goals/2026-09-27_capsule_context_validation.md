# Goal: reject ambiguous snapshot contexts before import

User requested continued independent project implementation. Base
codex/capsule-lineage-validation 443b232caef75d595f0680c5b2ed6c62fff0e0ea;
origin/live main 4787968dfdf3fcb8d1e8c0ca3304bd2c20d6c0b2.
New branch codex/capsule-context-validation starts clean.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222; stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Objective: validate context IDs without lossy set/string coercion. Reject
duplicate, empty/non-string and unreferenced context IDs before DB creation.
Export already selects only contexts referenced by exported facts. Keep existing
missing-context rejection and all valid snapshot behavior.
Allowed: capsule.py, targeted tests, this Goal/record. Forbidden: fixtures/schema
changes, real DB reads/writes, EIA requests, backtests, pushes or PR merges.
Tests: set `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')` in PowerShell;
python -m pytest tests/test_capsule_context_validation.py -q (red/green);
python -m pytest tests/test_capsule_context_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_output_preservation.py tests/test_stage2g_reproducibility.py -q;
python -m ruff check tests/test_capsule_context_validation.py;
git diff --check; git diff --cached --check; protected hash/stash/remote checks.
Acceptance: mutation tests fail before fix, pass afterward, old tests remain
green except documented platform skips. No cryptographic authenticity claim.
Stop on valid-fixture incompatibility, scope expansion or protected-state drift.
Local commit only. Review/publication of accumulated fixes is a separate step.
