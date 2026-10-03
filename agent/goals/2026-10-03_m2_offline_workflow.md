# One-command complete offline research workflow

Objective: compose existing session, review, audit and optional date comparison
into one navigable, deterministic, fully verifiable delivery directory.
User continuation explicitly authorizes this M2 engineering stage. Own execution;
no DSH/subagents. Verified origin/live main base
3a2abd2ec59929066fde2819a0331a26d67f1af1; clean owned worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance;
branch codex/m2-offline-workflow. Primary branch3679b1b, dirty/untracked snapshot,
stashcb568efd, localmain966206f and database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
are protected; capture protected reports/config/events/evidence/mechanism/fixtures.

Allowed eight files: this Goal; agent/record/2026-10-03_01-m2-offline-workflow.md;
acceptance/2026-10-03_m2_offline_workflow.md; README.md;
src/ashare_research/tools/research_workflow.py;
src/ashare_research/tools/research_entry.py;
src/ashare_research/tools/package_verification.py;
tests/test_research_workflow.py.
Forbidden: changes to prior builders/engines/tests/fixed sources, new financial
data/acquisition/messages, formulas/scoring/admission, database/cache/holdout or
real backtests; destructive cleanup, foreign worktree edits, direct main push.

Required: research workflow --as-of DATE --output NEW_DIR [--compare-with DATE]
[--year YEAR] [--metric ID] [--scope SCOPE]. Reuse public existing session build
and view exports. Keep original package bytes/layouts and known limitations.
Produce session/review/audit and, only when compare_with requested, comparison
with left as_of/right compare_with. Include relative-link index and canonical
root manifest with normalized request and inventories; no clocks/absolute paths.
Build all bytes before creating caller output. Reject existing output before
building and again through exclusive mkdir; never overwrite/clean supplied
paths. Reject symlink ancestry. Late write failure returns sanitized error2,
no success stdout and leaves own partial directory for inspection; do not claim
atomic directory publication. Verification recognizes workflow schema, rebuilds
from validated root request and compares every byte/layout/root manifest;
recorded paths never used for reading. Invalid selectors never create output.

Exact commands (PYTHONPATH=src; primary .venv/Scripts/python.exe):
python -m pytest -q tests/test_research_workflow.py
python -m ruff check src/ashare_research/tools/research_workflow.py src/ashare_research/tools/research_entry.py src/ashare_research/tools/package_verification.py tests/test_research_workflow.py
python -m ashare_research.cli research workflow --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-offline-workflow
python -m ashare_research.cli research verify --package tmp/m2-offline-workflow --json
git diff --check
Four meaningful cases: deterministic composition preserving nested packages and
single-date mode; full verification and rehashed outer/root/nested tampering;
existing/link output and prebuild/late failures preserving foreign content;
real CLI success/invalid args/verification and no legacy initialization.
Run targeted suite once, repeat only after actual fixes; no full local suite.

Acceptance: whole workflow verified, nested packages usable by existing commands,
80 files without comparison /131 with comparison, stable bytes, no protected
changes, meaningful four cases pass and scoped lint/diff clean. Commit/push only
eight files. Independently review exact diff/HEAD/contract/acceptance/protection/
stash/DB/task sync/live remote. Required42hostedchecks all successful, expected
head/base and clean mergeability before standing-authorized scoped PR merge.
Stop on failures, conflicts, changed baselines or scope expansion; do not bypass.
Final PASS/CHANGES_REQUIRED/BLOCKED evidence packet. Further engineering allowed;
new data/research stage unauthorized. Do not automatically start another stage.
