# Goal: integrate and publish three capsule safety fixes

User continued the proposed combined integration review and single PR handoff.
This authorizes publishing the existing fixes, not merging this or PR #32.
Base main/origin/live: 4787968dfdf3fcb8d1e8c0ca3304bd2c20d6c0b2.
Starting clean branch codex/capsule-context-validation at
e357efbaa2e4cd1c6eca3ff94ff9cb1a421f2a68; includes 2471b87 and 443b232.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222; stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Scope: independent combined diff inspection, six related offline test modules,
this Goal/acceptance record, scoped commit, push branch and one review PR.
No new features, fixture/schema mutation, real database access, provider calls,
backtests, main push or PR merge. Stop on regression requiring scope expansion.
Required behavior: retain all three safety properties and old valid workflows.
PowerShell prerequisite: `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`.
Validation: python -m pytest tests/test_capsule_output_preservation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q;
python -m ruff check tests/test_capsule_output_preservation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py;
git diff origin/main...HEAD --check; git diff --cached --check;
verify protected hashes/stash, clean worktree, pushed HEAD and PR diff scope.
Acceptance: related tests pass with explicit platform limitations, no baseline
changes, one PR without EIA commits. Remote CI state must be stated honestly.
