# Capsule manifest completeness

Date: 2026-09-28. Module: reproducible value-assessment infrastructure.
User requested continuation of engineering stability work.
Goal: agent/goals/2026-09-28_capsule_manifest_completeness.md.
Base d2f62da7a2c0c6557a94b7849391bddfbb7a08bd; clean new branch
codex/capsule-manifest-completeness in the existing dedicated worktree.

Inspected actual branch/commit/diff/worktrees/remote/stash, protected DB hash,
project agreement and recent records. verify_capsule_manifest accepts an empty
outputs inventory if its logical digest is recomputed; build_test_capsule always
generates six portable outputs. Plan: reproduce defect, enforce shared exact
inventory and explicit shape validation, test existing consumers, review and commit.
No data acquisition or research methodology changes.

Baseline reproduction executed a read-only `git show d2f62da:src/ashare_research/reproducibility/capsule.py`
copy in memory and built a capsule from committed fixture into TemporaryDirectory.
Set outputs to [], recomputed logical_digest, and corrupted the market CSV.
Baseline verifier still returned success: defect reproduced, exit 0.
No tracked or real data changed. Initial contract count of seven corrected to
six after inspecting actual builder list (four snapshot JSON, CSV, registry JSON).

Read docs/stage2g_reproducibility_contract.md and reproduction guide; existing
contract requires hashed portable output verification and independent A/B builds.
The derived temporary DuckDB is intentionally outside the portable inventory.
Assigned one Luna/medium worker per repository routing; parent reviews changes
and runs integration independently. Review explicitly requires retaining baseline
output order/digest and rejecting malformed input with ValueError.

## Implementation and independent acceptance

Verdict: PASS.

Builder and verifier share six canonical portable paths. Inventory shape,
unique complete membership and lowercase 64-character SHA256 strings are validated
before hashing output files. Non-object manifests raise ValueError. Existing
snapshot/content/digest checks remain. Temporary DB is not added to the manifest.
Parent corrected draft output ordering to preserve original digests, simplified
redundant path normalization checks to exact membership, and added precise hash,
unexpected path and non-string path regressions before final validation.

Worker focused run (before parent corrections): 21 passed. Parent final run:
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`
`python -m pytest tests/test_capsule_manifest_validation.py tests/test_capsule_output_preservation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs`
returned 121 passed, 4 skipped in 42.13s. Two skips require Windows symlink
privilege; two require absent real baostock snapshots. No tests weakened.
`python -m ruff check src/ashare_research/reproducibility/capsule.py tests/test_capsule_manifest_validation.py`:
All checks passed. `git diff --check`: passed.

Parent separately loaded the baseline source with `git show d2f62da:src/ashare_research/reproducibility/capsule.py`
and executed both builders against the same committed snapshot under a temporary
directory. Asserted full manifest equality, capsule_manifest.json byte equality,
and new compare_capsules(old, new) status == pass. All passed (six outputs).
Parent reviewed the complete actual diff and new tests, not just worker results.

Final scoped files: capsule.py, test_capsule_manifest_validation.py, this record,
and Goal. No schema/fixture/database/provider changes. Protected database SHA256
remains 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
stash remains cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f. Primary worktree status,
tracked diff and HEAD exactly match the captured baseline.

Final branch: codex/capsule-manifest-completeness, scoped local commit identified
in handoff; based on local d2f62da (previous atomic-publication fix).
origin/main and live main remain ae00efe7d5aa7cd592339b199c65281b9c1c441d.
Remote feature branch absent. No push/PR/merge. Cached whitespace and final clean
worktree checks are performed during delivery.

Limitations: this enforces inventory integrity, not authentication against someone
rewriting all artifacts and hashes together, or hardening against filesystem races.
Existing broader manifest input-metadata validation is unchanged. No live market
data or new research stage authorized/started. Engineering continuation remains
the user-selected direction; this bounded increment is complete.
