# Goal: one-command offline M4 progress check

Objective: reduce repeated repository investigations with a deterministic, read-only
command which verifies the existing EIA transport/PIT metadata and reports exact
historical evidence blockers and the smallest next evidence task.
Base: origin/main/live main f78aeb20349ff80e537b987abf15c4381ba5f360;
PR #38 actual MERGED, 42 successful checks. Clean new branch
codex/m4-offline-progress-check at that base. User requests continued progress
with attention to speed; no further low-priority capsule repair in this task.

Protected: primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222,
dirty/untracked files and all other worktrees; stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Local main 966206f06262e43f40c1c7aadbfb8596839eac91 preserved.

Allowed: new agent/tools/check_m4_progress.py; new
tests/test_m4_progress_check.py; concise README current capability/usage text;
this Goal, agent/record/2026-09-30_07_m4-offline-progress-check.md,
acceptance/2026-09-30_m4_offline_progress_check.md. One bounded DSH worker edits
only tool/test/README; parent owns Git, records and independent acceptance.
Forbidden: previous evidence/assessor/source/tests/contracts changes; network,
raw values/quarantine/credentials, providers/databases/holdout/backtests;
scope expansion, recursive workers, test weakening or destructive operations.

Behavior: fixed repository metadata paths, no user input/source-path CLI arguments.
Reuse assess_eia_pit strict JSON, canonical, digest and assess functions. Verify
allowlisted authorization/goal/ledger link digests, matching frozen identities and
recomputed assessment bytes against retained PIT report. No simply trusting an
old readiness flag. Output deterministic summary and --json report, explicitly
scope FROZEN_EIA_TRANSPORT_DOSSIER_ONLY, research_ready=false,
execution_authorized=false, evidence checks passed separated from research blocked.
List all three missing publication/availability/version reason codes and required
supplements from the recomputed assessment. State not a complete K2 or whole-project
readiness assessment, and provide next task: separately scoped first-party historical
PIT evidence review before any new acquisition/execution. No archive absence claim
or monthly-to-daily conversion. No timestamp/network/write/runtime reads.
Exit 0 = diagnostic completed with research blocked; integrity/missing evidence
exit 2 with concise error, no values/tracebacks. Do not embed raw dossier/proof/auth
in output. Report failure as evidence validation failure, not missing-PIT success.

Tests: actual repo CLI text/JSON deterministic from unrelated CWD and explicit false
authorization; corrupt/missing/rehashed fake-ready metadata cannot produce success;
duplicate-key/linked-path escape/mismatched retained assessment rejection. Use owned
fixture copies only; no repository evidence mutation. Bounded tests, meaningful
failure behavior and explicit exit semantics. Existing assessor/project-entry tests.

Exact parent validation from this worktree:
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

Acceptance: independently reviewed exact six-file scope, all checks above pass;
failure fixtures fail closed, protected state retained; no duplicate full local
product regression (unchanged product source), hosted exact-head required checks.
Stop: DSH failure/unavailable, scope conflict, protected/head/base drift, failed
tests after two repairs or hosted failure. No fallback or bypass.
Delivery: one scoped commit, feature push and PR; standing-authorized guarded merge
only after all 42 expected checks, seven workflows x six, exact head/base and
MERGEABLE/CLEAN. No automatic subsequent stage or new acquisition.
