# Capsule safety integration and DSH routing

Date: 2026-09-30. Goal: agent/goals/2026-09-30_capsule_safety_integration.md.
Start codex/capsule-input-bindings@3fe0e764e8989af83ef957568fcfe4bb3da9d127,
clean worktree. New branch codex/capsule-safety-integration.
Reviewed actual state, cumulative files, protected DB/stash, and pending PRs.
Standing merge authority exists in tracked Goal and PR #34, not inferred from
chat summary. PR #34 exact diff changes merge confirmation rule only; expected
head matches remote, 42 checks SUCCESS, MERGEABLE. Processed with expected-head
guard under its existing Goal. New task integrates existing safety fixes and
persists explicit DSH correction; historical implementation records retained.

DSH bounded task: edit route documents only, read-only review of cumulative
capsule changes. Parent retains validation and all Git/publication actions.
No new research or acquisition. Delivery results pending.

PR #34 merged with `gh pr merge 34 --merge --match-head-commit 02a451861da9b3c74fb9ecf9c250303b385e61f0`;
merge commit 5b899ccc14f4a93f28f8627ee0918f6acdf9f087. Fetched main and normally
merged into task branch: d7b2100caee5ea7528bfdb8a62b8bcf427143147. No conflicts.
Initial `python -m ruff check src tests` used global Ruff 0.12.0 and reported five
UP038 findings in unchanged mechanism files. Project pins Ruff 0.13.2; primary
venv provides that exact version. Use its executable for project-version validation;
no unrelated source edits or test relaxations.
`& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests`:
All checks passed with pinned Ruff 0.13.2. Parent inspected cumulative capsule.py
diff: staged private DB + finally close + no-clobber link publication, exact
portable inventory, validated metadata bindings; no provider/schema/fixture edits.

DSH exited 0. Edited only the three allowed route documents and performed the
read-only cumulative safety review: PASS, no regression blocker. Parent inspected
exact doc diff; standing merge/Git/data restrictions retained, default DSH matches
primary user instruction. Product hashes match prior validated suite. Earlier
Luna implementation records remain historical; this task does not rewrite them.

Review follow-up: cleanup failure after a successful hard link can surface an
error while leaving a valid published DB. Record as a non-blocking operational
limitation for bounded follow-up; no new product changes in this integration.
Coverage review found a further build_test_capsule caller in
tests/test_stage2g_dividend_correction_and_valuation.py; parent runs that module
and full hosted CI still gates merge. Runtime DB/provenance/path-race exclusions
remain explicit. DSH did not claim new test execution or protected DB hashing.

Parent executed (PYTHONPATH absolute src)
`python -m pytest tests/test_stage2g_dividend_correction_and_valuation.py -q -rs`:
13 passed in 5.97s. `git diff --check` passed. Existing eight-module product
validation remains 181 passed / 4 skips at identical code/test hashes.
Local integration acceptance: PASS. Hosted CI/final merge acceptance pending.
Scoped new files: AGENTS.md, agent/agent.md, agent/model-routing.md, this record,
and integration Goal; cumulative PR additionally contains the ten files from
the three local capsule fixes. No runtime/scratch/raw/private data staged.
Protected database/stash/primary changes unchanged. Final commit/PR/CI/merge
identities are verified and supplied in final handoff/GitHub PR evidence.
