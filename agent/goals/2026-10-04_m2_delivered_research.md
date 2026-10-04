# Read and compare delivered research

Objective: user explicitly selected direct viewing/comparing metrics and evidence
inside delivery packages. Root executes, no DSH/subagents. Provide verified
workflow/section report reading and extend existing financial comparison to
session/workflow ZIP inputs without caller restoration or new calculations.

Verified base origin/live mainffb6a9d97b316af45ba2e4ac57eb46cc07b82de9;
owned branch codex/m2-delivered-research, capsule-postmerge-acceptance worktree.
Primary original full snapshot unchanged, HEAD3679b1b/localmain966206f/stashcb568efd;
427protected hashes freshly compared; databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged.

Allowed eight files: this Goal; acceptance/2026-10-04_m2_delivered_research.md;
agent/record/2026-10-04_03-m2-delivered-research.md; README.md;
src/ashare_research/tools/delivered_research.py;
src/ashare_research/tools/session_compare.py;
src/ashare_research/tools/research_entry.py; tests/test_delivered_research.py.
Forbidden: existing tests, builders/verifiers/baselines/financial calculations/CI,
new data/network/research/backtests/holdout, foreign worktrees/runtime/database/
stash/user changes, direct main/force pushes/destructive cleanup.

Required: research read (--package DIR | --archive ZIP) --section review|audit|compare
[--json], full existing package verification before selecting fixed canonical
report bytes, workflow or matching section package only; absent section/wrong
kind fail explicitly. JSON envelope retains complete original report and full
verification; readable output uses existing renderer and all existing limits.
No arbitrary member path, caller output, retained-file reread/cache.
research compare per side mutually exclusive --left/--left-archive and
--right/--right-archive. Existing directory behavior unchanged; ZIP may contain
session or workflow, fully verify outer package then use canonical session bytes
once. Preserve view selectors, original comparison engine/report/export format;
export remains independently verifiable. Sanitized errors2/no partial stdout.

Validation with PYTHONPATH=src and D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_delivered_research.py tests/test_session_compare.py
python -m ruff check src/ashare_research/tools/delivered_research.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_delivered_research.py
git diff --check
Two new meaningful cases using actual fixed workflow/session archives: report
JSON/Markdown equivalence for three sections and directory/ZIP, mixed and ZIP
financial comparison equality, portable export verification; invalid argument,
wrong kind, missing section, corrupted/rehashed outer report rejected before
success, no caller mutations. One targeted run, repeat only necessary fixes.
Actual retained delivery read/compare CLI demonstration and saved receipts.

Acceptance: original metrics/values/inputs/gaps retained; two-point comparison
seven value changes matches existing engine; every package fully verified;
eight-file scope; targeted/lint/diff checks pass, no full local suite; primary/
stash/database/427hashes unchanged. Commit/push scoped branch/PR; independent
actual commit/diff/Goal/acceptance/refs/protection review; required hosted checks
and exact head/base/CLEAN gate before standing-authorized merge. Stop on failure,
conflict/drift/scope expansion. Final PASS/CHANGES_REQUIRED/BLOCKED with actual
evidence. No automatic next stage/new research qualification.
