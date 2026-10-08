# M4 reproducible explicit plan packages

Status: locally completed; publication and hosted status recorded separately.
User continuation, root alone, no DSH/agents. Verified origin/live main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b; previous PR88 still open with
36 successful checks and four full-suite jobs pending at preflight.
Clean isolated codex/m4-user-plan-package, independent of PR88.
Primary HEAD/status/stash/database/314 protected hashes and 54 foreign
worktree statuses/refs recorded before implementation.
Goal: agent/goals/2026-10-08_m4_user_plan_package.md.

Added research plan-package --hypothesis JSON --output NEW_DIR [--json] and
--verify DIR [--json]. Original strict byte loader/compiler split into additive
helpers; legacy report content, rendering/errors and single-read behavior remain.
Export retains original bytes plus canonical report.json/report.md/manifest.json;
verification captures each bounded regular file once, recompiles original source,
regenerates all four artifacts and compares exact bytes. No paths or clocks.
Self-consistency is explicitly distinct from provenance/sealing/authorization.

Exclusive output root/files, no parent creation or overwrite. Reject links,
Windows reparse points, traversal, extra/missing/nonregular/oversized members.
Render before mkdir, read back before success, preserve partial owned output.
Independent review added parent revalidation after source compilation and owned
directory identity checks before each write. Test replaces parent with junction
or symlink during source capture: rejection, external target remains empty.

Actual local validation, PYTHONPATH=src and D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan_package.py tests/test_research_plan.py tests/test_research_entry.py
13 passed in 49.78s. No test failures. Initial Ruff found three style issues
(import layout/two line lengths); fixed. Strengthened forged-manifest test to
retain canonical formatting and verify its claimed report hash actually matches.
Default Markdown receipt now fences manifest JSON.
python -m pytest -q tests/test_research_plan_package.py::test_public_export_reproduce_relocate_and_original_boundaries tests/test_research_plan_package.py::test_content_tampering_and_rehashed_forgery_fail_closed
2 passed in 0.91s. Added assertion introduced one line-length issue, fixed.
After directory race hardening/new case:
python -m pytest -q tests/test_research_plan_package.py tests/test_research_plan.py
10 passed in 1.67s. All 14 scoped/legacy cases covered successfully across runs.
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_package.py
git diff --check
Final both PASS. No repeated full suite.

Public subprocess export/verify succeeded, four files, stderr empty; retained
receipts/packages under tmp/plan-package-demo. Original example SHA256
974b8cc55309e2219dc12dec6bdff45e346e2092f88435581f7533bbfe6cdb47 unchanged.
Canonical contract 56e914cf9afef8af935c2553e242dc2c0c888d537c5494dabb05eb094a1c4610
and plan c73268f7b63a24f300aec8e5fd3f20adbe3fc1031b85acebe3835148964c3267
retained; every authorization/readiness/statistics/holdout flag false.

Actual source/diff/Goal/test review and precommit audit PASS: 314 hashes, primary
HEAD/status/stash/database, 54 foreign worktree statuses/refs and remote main
unchanged. Acceptance: acceptance/2026-10-08_m4_user_plan_package.md.
Final commit/PR/protection/local-origin-live checks and hosted status in ignored
tmp/plan-package-final-review.json and final response. Current user governance
overrides repository historical standing merge authorization. No acquisition,
real execution, holdout, merge or next stage.
