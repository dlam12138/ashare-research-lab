# Unified offline research entry

Objective: expose the four existing offline workflows through the installed
ashare-research research entry: report, facts, metrics, demo. Preserve original
tool selectors, rendering, error codes and output safeguards through delegation.
Verified base: origin/live main 676222d8ddebf6b2bc0e4065afc9849904955e6b;
branch codex/m2-unified-research-entry; owned worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance. Primary dirty
feat/m2-value-assessment-mvp at3679b1bac7a1634c6452784a4d8f6d139966f222,
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, local main966206f,
DB SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
must remain unchanged, as must captured protected hashes and other worktrees.

Allowed: src/ashare_research/cli.py; new
src/ashare_research/tools/research_entry.py; tests/test_research_entry.py;
README.md; this Goal; agent/record/2026-10-01_08-m2-unified-research-entry.md;
acceptance/2026-10-01_m2_unified_research_entry.md. DSH may write first four
only, parent owns records/Git/independent verification.
Forbidden: changes to existing offline implementations, old tests, providers,
data/snapshots/reports/config/events/evidence/mechanism/runtime/DB; network data,
messages, new formulas or research claims, backtests/holdout/admission; recursive
delegation, fallback models, arbitrary source/database selection.

Required: research top-level help explains four workflows and offline boundaries;
delegate tool arguments unchanged to their existing main(argv), including subtool
help, selectors and sanitized failures. Dispatch before legacy config/logging/
service initialization; ignore no config silently: reject global --config and
--debug combined with research rather than accepting misleading modifiers.
All current legacy commands and service_factory behavior remain intact.
No duplication of tool parsers or report calculations. CLI root help discovers
research. Existing module entries remain usable. No implicit current-date query.

Required local commands (PYTHONPATH=src, existing primary venv python):
python -m pytest -q tests/test_research_entry.py
python -m ruff check src/ashare_research/cli.py src/ashare_research/tools/research_entry.py tests/test_research_entry.py
python -m ashare_research.cli research metrics --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-unified-research-entry
git diff --check
Four meaningful test cases: discovery/help/dispatch/legacy preservation;
real report and synthetic flows with forbidden initialization guards;
actual dated facts and metric equivalence/PIT limits;
real export/existing-path safety and invalid/global-option rejection.
Parent runs targeted checks once, repeat only actual fixes; mandatory hosted full
suite and identity/contract gates required. DSH does not run tests or helpers.

Acceptance: usable unified entry and real artifact; independent diff review;
four tests and scoped lint pass; protected state unchanged; exact scoped commit,
clean task worktree and origin sync. Commit/push task branch only, create PR,
verify exact base/head/required successful checks/clean mergeability before merge
under standing authorization. Never push main. Stop on failures/conflicts,
DSH unavailable or two failed repairs, protection changes or scope expansion.
Final PASS/CHANGES_REQUIRED/BLOCKED evidence packet. Further scoped engineering
may continue under user direction; no new data or research stage authorization.
