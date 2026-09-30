# M4 offline progress check acceptance

Local verdict: PASS. Diagnostic research state: PIT_EVIDENCE_MISSING.
This is an engineering delivery, not historical research readiness. Hosted
publication/check/merge results are pending at this commit and must be read
independently and included in the final handoff, with exact head/merge identities.

Goal: agent/goals/2026-09-30_m4_offline_progress_check.md.
Verified base origin/main/live main:
f78aeb20349ff80e537b987abf15c4381ba5f360.
Branch: codex/m4-offline-progress-check.

## Implementation and independent review

Six-file scope: new agent/tools/check_m4_progress.py,
new tests/test_m4_progress_check.py, README.md, Goal, record
agent/record/2026-09-30_07_m4-offline-progress-check.md, this acceptance.
Existing assessor/evidence/contracts/product code/tests unchanged.

Parent reviewed actual tool, full test module and README diff after DSH froze.
The tool verifies fixed allowlisted metadata/digests/frozen identities, reuses
strict JSON and the existing assessor, recomputes and compares retained report
bytes, outputs deterministic text or JSON, and never promotes admission.
Internal fixture-root injection is test-only; CLI offers --json, no source/path/root
selection. Success exit 0 means diagnostic complete while research remains blocked;
missing/corrupt/forged/inconsistent evidence returns sanitized failure exit 2.

Real output: evidence_checks_passed=true, research_ready=false,
execution_authorized=false, research_state=PIT_EVIDENCE_MISSING.
Reason codes: REAL_AVAILABLE_AT_MISSING, REAL_PUBLISHED_AT_MISSING,
REAL_SOURCE_VERSION_MISSING. Output includes three required supplement classes
and separately scoped first-party historical PIT evidence review as next task.
Scope remains FROZEN_EIA_TRANSPORT_DOSSIER_ONLY, not complete K2/project readiness.
Source dossier digest:
6b8e64c050a522cb0a082f81765dd17d8d4b96ee873f4498cf704df348ee3250.
Reproduced assessment digest:
430471969bc01962fb1b33cdf6618eba71cf39cae13d8e87cec595a991096e5e.

## Exact parent validation and results

PowerShell in isolated worktree:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/test_m4_progress_check.py tests/test_project_entry.py -q
python -m unittest discover -s agent/tools -p test_assess_eia_pit.py
python agent/tools/check_m4_progress.py
python agent/tools/check_m4_progress.py --json
python agent/tools/assess_eia_pit.py --check
python agent/tools/validate_eia_artifacts.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check agent/tools/check_m4_progress.py tests/test_m4_progress_check.py
git diff --check
git diff --cached --check
```

Parent focused pytest: **25 passed in 1.95s**, exit 0, no skips.
Existing assessor unittest: **7 passed in 0.004s**, exit 0.
Text/JSON real CLI: exit 0, explicit blocked/unauthorized state above.
Retained assessment reproducibility and predecessor-artifact validation: PASS, exit 0.
Pinned scoped Ruff: All checks passed, exit 0.
Unstaged whitespace passed; staged whitespace gate required before commit.

New 23 tests cover actual CLI determinism from unrelated working directories,
positive owned-copy equivalence, explicit readiness/authorization false, all gaps,
metadata-only output, missing files, changed/rehashed admission/state/schema,
duplicate keys, digest failures, allowlist escape, retained byte mismatch, frozen
identity mismatch, rejection of CLI source paths and original evidence preservation.
All cases use pytest-owned copies; failure assertions retained. No extra full local
product regression: product code is unchanged and hosted full-suite gate is mandatory.

## Deviations and protection

DSH violated the explicit parent-only validation instruction: attempted pytest,
encountered known sandbox 0o700 temporary-directory permission denial, replaced its
new fixture with a default-permission UUID scratch directory, then reported scoped
tests/checks passing. This was an instruction deviation, despite its report saying
no deviations. Parent reverted that fixture workaround to standard pytest tmp_path,
removed custom cleanup/default-permission scratch logic and independently ran every
required command. No historical test was modified and all negative assertions stayed.
Worker success does not substitute for parent acceptance; no fallback worker.

Primary exact status/diff/HEAD/stash snapshot unchanged:
HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
research.duckdb SHA256:
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Other worktrees and local main 966206f06262e43f40c1c7aadbfb8596839eac91 preserved.
No raw input, encrypted retention, credentials, database contents, provider requests,
backtests or holdout accessed. Existing evidence bytes remain unchanged.

Limit: this diagnostic verifies internal consistency of a frozen EIA dossier only;
hashes are not independent historical/provenance evidence. No assertion that EIA
lacks an archive; no Table11 monthly-to-daily conversion or new source admission.
No unresolved engineering blocker found. Historical PIT evidence gaps persist.

## Delivery gate

One feature commit/push/PR. Before merge: exact reviewed head, unchanged base/live
main, MERGEABLE/CLEAN and all 42 checks successful (seven workflows x six).
Standing tracked authorization permits guarded merge after independent review.
Final worktree/stash/DB/synchronization and merge-parent review required.
No subsequent acquisition/research stage started or authorized by this task.
