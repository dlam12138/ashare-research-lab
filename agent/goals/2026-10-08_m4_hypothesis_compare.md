# M4 explicit hypothesis comparison

Objective: directly compare two user hypothesis JSON files through the existing
frozen compilers. User requests root execution, no DSH or other agents.

Verified baseline: origin/main and live remote main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b; owned clean branch
codex/m4-hypothesis-compare. Primary remains feat/m2-value-assessment-mvp at
3679b1bac7a1634c6452784a4d8f6d139966f222 with pre-existing edits/untracked files.
Stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f retained. Primary database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
314 primary protected data/reports/config/events/fixture file hashes, original
status, HEAD, stash and worktree refs captured in ignored
tmp/hypothesis-compare-baseline.json before implementation.

Allowed scope: this Goal, agent/record/2026-10-08_01-m4-hypothesis-compare.md,
acceptance/2026-10-08_m4_hypothesis_compare.md, README.md,
src/ashare_research/tools/research_hypothesis_compare.py,
src/ashare_research/tools/research_entry.py,
tests/test_research_hypothesis_compare.py. Ignored validation artifacts allowed.
Forbidden: frozen mechanism/config/contract/plan compilers, existing tests,
fixtures, reports, schemas, CI, governance and routing changes, providers,
real research/data acquisition/statistics/holdout, user edits/databases/stash,
foreign worktrees, destructive cleanup, force push or direct main push.

Required behavior: expose research hypothesis-diff --left JSON --right JSON
[--json]. Reuse research_plan.build_report once per side; preserve complete
original envelopes and source/config/contract/plan identities. Compare canonical
config/contract/plan recursively with deterministic JSON pointer paths; retain
list order, added/removed/value changes, distinguish absence from explicit null.
Do not include derived contract/plan digest fields as semantic changes.
Report source-byte equality independently of compiled content identity.
No interpretation of improvement, evidence, readiness, or authorization.
Render valid Markdown with escaped user strings; errors sanitized and stdout
empty until both inputs compile and full rendering succeeds.

Required tests: public unified entry, compiler identity and change propagation,
same bytes/reformatted bytes/semantic changes, list ordering/missing fields,
invalid side JSON/unsupported policies/arguments, no network/database/execution,
one load per side even if input mutates afterward, deterministic results.
Exact validation (PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_research_hypothesis_compare.py tests/test_research_plan.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_hypothesis_compare.py src/ashare_research/tools/research_entry.py tests/test_research_hypothesis_compare.py
git diff --check
Public CLI demo saved under tmp/; inspect real diff/commit and recheck protected
hashes/primary status/HEAD/stash/worktree refs/live remote before final verdict.

Acceptance: original objects/digests preserved, complete deterministic changes,
strict input errors and false execution boundaries, passing tests/lint/diff,
seven scoped files only and protected state unchanged.
Stop on scope expansion, concurrent unexpected edits, failed gates, conflict,
protected mismatch or remote baseline drift; no gate bypass.
Commit/push: normal scoped commit and branch push, PR with evidence if available.
Do not merge automatically: current user governance requires explicit
authorization. No automatic next stage. Final PASS/CHANGES_REQUIRED/BLOCKED
with actual evidence and any hosted checks still pending stated explicitly.
