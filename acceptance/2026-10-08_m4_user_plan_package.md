# M4 explicit plan package acceptance

Local verdict: PASS.
Goal: agent/goals/2026-10-08_m4_user_plan_package.md.
Base origin/live main: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Branch: codex/m4-user-plan-package, independent of unmerged PR88.
Final commit/PR/hosted check snapshot: tmp/plan-package-final-review.json.
Root implemented and independently reviewed actual files, no DSH/agents.

Eight scoped files: Goal, this acceptance, work record, README.md,
tools/research_plan.py, tools/research_plan_package.py, tools/research_entry.py,
tests/test_research_plan_package.py. No existing test/frozen engine/fixture/
report/schema/CI/governance/routing changes.

Evidence:
- Exact original source bytes and SHA256; original canonical config/contract/plan
  and boundary objects retained. Legacy plan tests and unified entry compatible.
- Deterministic four-file packages reproduce after relocation/deleting original
  source. Source captured once; each package file captured once for verification.
- Report/Markdown/manifest tampering, source formatting changes, missing/extra/
  nonregular members rejected. Forged authorization/contract and canonical
  rehashed manifest are rejected even when the manifest matches forged bytes.
- Strict JSON failures, unsupported real policy, bad CLI modes, size limits,
  pre-existing file/directory, collision race, missing parent and simulated late
  write failure preserve callers' content and owned partial output.
- Actual Windows junctions (Unix symlinks on that platform), member links,
  linked ancestors and traversal rejected. Parent switched to link during
  source capture cannot redirect export; external directory remains empty.
- Database/network/service/executor guards, original boundary values all false.

Exact commands (PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_research_plan_package.py tests/test_research_plan.py tests/test_research_entry.py
13 passed in 49.78s.
python -m pytest -q tests/test_research_plan_package.py::test_public_export_reproduce_relocate_and_original_boundaries tests/test_research_plan_package.py::test_content_tampering_and_rehashed_forgery_fail_closed
2 passed in 0.91s after strengthening canonical forged-manifest coverage and
fencing receipt Markdown. Independent review added path race guards and case:
python -m pytest -q tests/test_research_plan_package.py tests/test_research_plan.py
10 passed in 1.67s. All 14 distinct scoped/legacy cases successfully covered.
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_package.py
All checks passed. Initial three, then one formatting issues fixed; no test
failures, bypasses, disabled checks or edits to existing tests.
git diff --check
PASS.

Public CLI subprocess commands:
python -m ashare_research.cli research plan-package --hypothesis docs/examples/m4_hypothesis.json --output tmp/plan-package-demo/package --json
python -m ashare_research.cli research plan-package --verify tmp/plan-package-demo/package --json
Both exit 0, stderr empty; receipts, four original files and source digest retained.
Final-code package export also compared byte-for-byte to initial package.

Protection baseline: primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
314 protected hashes and 54 foreign statuses/refs unchanged before commit,
primary dirty/untracked state preserved. Final recheck excludes only expected
owned HEAD advance; no foreign branch synchronization or stash operations.

Limits: existing synthetic V1 vocabulary, compatible compiler/renderer required,
canonical bytes required (even report reformatting fails). No source provenance,
independent seal, signatures, evidence readiness, research/statistical execution
or holdout permission. Partial owned output retained on late failure.
Local acceptance does not claim hosted completion. Hosted exact-head results,
pending/failures and local/origin/live sync reported separately. Current user
governance prohibits automatic merge; next stage not started or authorized here.
