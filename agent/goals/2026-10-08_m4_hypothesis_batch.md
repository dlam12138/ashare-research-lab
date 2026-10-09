# M4 multi-hypothesis plan inventory

Objective: compile a bounded set of explicit hypotheses and expose original
per-plan requirements plus declared series overlap for input preparation.
Current user continuation authorizes this task, root alone, no DSH/agents.

Verified baseline: origin/main/live remote main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b. Clean isolated
codex/m4-hypothesis-batch, independent of open PR88 ec1749a and PR89 83b2c99.
Primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222, existing dirty/untracked
state and stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f preserved.
Database SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
1355 primary data/reports/config/events/fixtures/output/runs hashes and 55 foreign
worktree statuses/refs captured in ignored tmp/hypothesis-batch-baseline.json.

Allowed seven files: this Goal; agent/record/2026-10-08_03-m4-hypothesis-batch.md;
acceptance/2026-10-08_m4_hypothesis_batch.md; README.md;
src/ashare_research/tools/research_hypothesis_batch.py;
src/ashare_research/tools/research_entry.py;
tests/test_research_hypothesis_batch.py. Ignored validation artifacts allowed.
Forbidden: original research_plan or mechanism/compilers/contracts/adapters/
registry/executors/schemas, existing tests/fixtures/reports/config/events/CI,
acquisition/real data/statistics/outcomes/holdout, governance/routing changes,
user changes/databases/stash/foreign worktrees, cleanup/force push/direct main.

Required behavior: research plan-batch --hypothesis JSON (repeat, 1..16) [--json].
Use original build_report once per argument with its original strict 1MiB loader.
Reject duplicate compiled hypothesis IDs; input-order independent deterministic
inventory sorted by original hypothesis ID and declared series ID.
Retain complete original report/source SHA/config/contract/plan objects/digests.
Group original dataset requirements by declared series ID; retain exact original
requirement, its index, original plan digest, full sample-quality plan and universe
requirement per use. Count actual plans/roles/series only; show shared declaration
and role-independent requirement differences descriptively. Keep incompatible
declarations separate; do not merge windows, gate policies, identities or data.
Shared IDs do not establish actual source identity/reuse/availability/PIT evidence.
All original execution/readiness boundaries stay false. No registry update,
quality judgment, independent sealing or execution authorization.
Canonical JSON and Markdown bounded to 8MiB; fail closed before any stdout.
Invalid count/options reject before loading. Markdown shows original digests,
windows/gates/methods and exact per-use requirements with escaped values.
No paths/clocks or file writes; caller owns optional shell redirection.

Required tests: public original object/digest identities, overlapping and unique
requirements, different role/declaration/window/quality scope, input order
determinism, source formatting identity, single capture after mutation, guard
network/database/services/executor; duplicate IDs, invalid count/options,
malformed/oversized/unsupported-policy input, output limits and no partial stdout.
Exact local validation (PYTHONPATH=src; D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_research_hypothesis_batch.py tests/test_research_plan.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_hypothesis_batch.py src/ashare_research/tools/research_entry.py tests/test_research_hypothesis_batch.py
git diff --check
Retain actual public subprocess demo JSON/Markdown in ignored tmp/; recheck
committed diff/Goal/test/acceptance, protected hashes/primary/foreign statuses/
stash/refs and local-origin-live remote equality before final review.

Acceptance: seven scoped files only; original reports/requirements preserved,
deterministic descriptive inventory, strict input/output rejection, passing
local checks and protected state unchanged. Hosted checks reported independently.
Stop on unexpected concurrent edits, protected mismatch, drift/conflicts,
failed gates or scope expansion; fix authorized issues, never bypass gates.
Commit/push: normal scoped commit, branch push and evidence-backed PR.
Do not auto-merge under current user governance despite historical repository
standing authorization. No automatic next stage or research/data authorization.
