# Goal: validate snapshot lineage structure

User authorized next independent engineering stage. Base local
codex/capsule-output-preservation 2471b873fd361f20c2875fc42038a0c02b70bf4b;
origin/live main 4787968dfdf3fcb8d1e8c0ca3304bd2c20d6c0b2.
New branch codex/capsule-lineage-validation; initially clean.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222, stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Objective: reject truncated, duplicate, orphaned or misbound snapshot lineage
before database import. Allowed: capsule.py validation, new targeted tests,
this Goal and record. Keep existing manifest/schema and fixtures unchanged.
Required: lineage count equals manifest, integer unique lineage IDs, each row
belongs to a known fact, and per-fact declared lineage IDs match actual rows.
Forbidden: real DB access, network acquisition, research changes, frozen fixture
rewrites, EIA work, main push/merge. This is structural validation, not proof
against a coordinated rehash/rewrite of all snapshot inputs.
Tests: PowerShell `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`;
python -m pytest tests/test_capsule_lineage_validation.py -q (red then green);
python -m pytest tests/test_stage2g_reproducibility.py tests/test_capsule_output_preservation.py -q;
python -m ruff check tests/test_capsule_lineage_validation.py; git diff --check;
git diff --cached --check; protected DB/stash checks.
Acceptance: targeted regression fails before fix, passes after; existing suite
passes with only pre-existing platform skips. Stop for incompatible fixtures,
protected-state drift or required scope expansion. Local commit only, no push.
