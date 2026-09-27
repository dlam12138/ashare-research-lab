# Goal: preserve existing capsule database outputs

Objective: fix build_temp_fact_db deleting a pre-existing caller-supplied target.
User authorized progressing independent project work while EIA evidence waits.
Base: origin/main/live main 4787968dfdf3fcb8d1e8c0ca3304bd2c20d6c0b2.
Branch: codex/capsule-output-preservation, initially clean. EIA branch preserved.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222; stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed: capsule.py target guard, dedicated regression tests, this Goal/record.
Required: reject existing files/directories and live/dangling symlinks before
snapshot loading or filesystem writes. Preserve successful fresh-path behavior.
No overwrite flag, deletion, research changes, real DB access, new data requests,
frozen baseline edits, EIA changes, main push or merge.
Tests use pytest temporary files and monkeypatch only; existing capsule suite
provides compatibility coverage. No claim of concurrent-writer atomic safety.
PowerShell prerequisite: `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`.
Commands: python -m pytest tests/test_capsule_output_preservation.py -q;
python -m pytest tests/test_stage2g_reproducibility.py -q;
git diff --check; git diff --cached --check; protected hash/stash/remote checks.
Acceptance: regression fails before fix, passes after; existing suite passes;
no existing output or protected data changed. Stop for baseline drift or failing
compatibility requiring wider changes. Local commit only; no push/merge.
