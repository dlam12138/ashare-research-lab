# M4 compile-only plan package export and verification

Objective: user continuation, root alone, no DSH or agents. Make the existing
explicit hypothesis plan portable and independently reproducible with
research plan --hypothesis JSON --output NEW_DIR [--json] and --verify DIR [--json].
Verified base origin/live main 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b;
clean isolated branch codex/m4-plan-package. Primary branch/HEAD3679b1b, dirty
files, stash, local main966206f, database and protected hashes captured before
implementation in tmp/m4-plan-package-baseline.json. No changes to foreign trees.

Allowed: this Goal; acceptance/2026-10-07_m4_plan_package.md;
agent/record/2026-10-07_02-m4-plan-package.md; README.md;
src/ashare_research/tools/{research_plan,research_plan_package,research_entry}.py;
tests/test_research_plan_package.py. Ignored local evidence allowed.
Forbidden: modifying existing tests, mechanism/config/schema/compiler/executor/
registry/adapter/fixtures/reports/CI; data acquisition, statistics, real research,
holdout, DB writes; user dirt/stash/foreign worktrees; main push, merge,
force push and destructive cleanup. Supplied user governance forbids automatic
merge without explicit authorization, despite historical standing repository rule.

Required behavior: original bounded strict JSON parsing and original compilers
retained. Export source bytes from one read, exact deterministic JSON/Markdown
and manifest inventory. Four flat regular files only, no host paths/timestamps.
Validate before destination creation; exclusively create a new directory and
files, reject existing destinations and links/reparse paths, never overwrite or
delete. On write failure report failure and retain partial owned output; no
success receipt. Existing parent required. This is not atomic publication or a
hostile concurrent filesystem sandbox. Verification reads bounded files, rejects
missing/extra/nested/linked entries, recompiles saved original bytes through
current existing compilers, compares every expected file byte-for-byte including
manifest; reject corrupted outputs even if inventory hashes are forged.
Digest/inventory/recompilation are consistency checks, not an independent seal,
historical-source validation, authenticity, execution authority or research readiness.
Original six false boundaries retained. Existing stdout modes remain unchanged.
Sanitized errors and no partial stdout. Invalid flag combinations fail closed.

Exact required validation, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan.py tests/test_research_plan_package.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_package.py
git diff --check
Public export/verify CLI demo and independent actual committed diff/scope/Goal/
acceptance/refs/protection review required. Cases: original bytes and compiler
identities, offline guards, one-read mutation handoff, deterministic relocation,
corruption/forged manifests, false readiness, invalid input/flags, existing/link/
extra/missing/oversized entries and injected write failure without overwrite.
Targeted tests once; rerun only affected failures/changes; no full local suite.

Acceptance: all local commands pass; demo verifies after relocation; exact eight
files and protected/primary/stash/database snapshots unchanged. Normal scoped
commit/push/PR, required hosted checks reviewed before acceptance. Stop failed
checks, conflicts, base drift or scope expansion; do not bypass protections.
Final evidence packet reports PASS/CHANGES_REQUIRED/BLOCKED, exact commit/tests,
sync and remaining risks. No automatic merge or following stage.
