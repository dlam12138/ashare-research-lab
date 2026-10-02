# Verified cross-session metric comparison

Objective: compare independently saved research sessions, including changed date,
year and metric selectors, without new financial calculations or data acquisition.
Verified base origin/live main dd0f6583e8c58a16bafabcb48203dea3769fc42f;
clean owned worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance,
new branch codex/m2-session-compare. Primary feat/m2-value-assessment-mvp
3679b1bac7a1634c6452784a4d8f6d139966f222 and full dirty/untracked snapshot,
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, local main966206f,
DB SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
and protected reports/config/events/evidence/mechanism/fixtures hashes preserved.

Allowed seven files: src/ashare_research/tools/session_compare.py;
src/ashare_research/tools/research_entry.py; tests/test_session_compare.py;
README.md; this Goal; agent/record/2026-10-02_02-m2-session-compare.md;
acceptance/2026-10-02_m2_session_compare.md. User expressly requires own execution,
no DSH or delegation. Forbidden modifications to prior engines/tools/tests/fixed
inputs, default DB, research admission, formulas/scores, financial data fetching,
messages, real backtests/holdout and destructive operations.

Required research compare --left DIR --right DIR with optional --left-view and
--right-view (as_of default, compare_with explicit), Markdown/--json/--output.
Verify both complete sessions using public verifier and regenerate canonical
bytes using public builder. Selected views must exist; different symbols/scopes
rejected as incomparable. Normalize keys by metric ID/year; distinguish added
and removed selections from status changes. Common-key comparison uses existing
public metric comparison, retaining every original record, input trace and exact
decimal/unit without arithmetic. Show both full requests, selected dates/views,
manifest digests and descriptive counts, no causal claim or readiness judgment.
Same-date equality does not prove historical publication. Original missing roles,
sources and parents remain visible in JSON and included evidence.

Portable export51files: compare.md/json/outer integrity inventory + two unchanged
24file nested sessions, relative links. Existing file/dir/link refused; verify,
compose and render before exclusive output mkdir. Invalid inputs create no output
parent; late IO may leave owned partial outputs. Error2, sanitized/no partial
stdout; no absolute machine paths or current clock in report. Outer inventory
is not a signature, archive-only verifier or authenticity proof.

Exact local validation in owned worktree with PYTHONPATH=src and primary venv:
python -m pytest -q tests/test_session_compare.py
python -m ruff check src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_session_compare.py
python -m ashare_research.cli research compare --left tmp/m2-research-session --right tmp/m2-research-session --right-view compare_with --output tmp/m2-session-compare
python -m ashare_research.cli research session --verify tmp/m2-session-compare/left
python -m ashare_research.cli research session --verify tmp/m2-session-compare/right
git diff --check
Four meaningful cases: exact restated results/full traces; selector differences,
equal dates/missing values and incompatible views/scopes; portable byte-exact
evidence and moved verification; real CLI, tamper, malformed args/output safety.
One targeted run, repeat only actual fixes; no full local regression. Hosted CI
mandatory. Acceptance actual artifact, all local checks and protected comparisons,
independent scope/diff/Goal review; commit/push seven files only, no main push.
Standing merge authorization requires expected base/head, clean mergeability and
all42successful checks. Stop on failed checks/conflicts/protection or scope change.
Final PASS/CHANGES_REQUIRED/BLOCKED with evidence; engineering continuation allowed,
new data/research stage still requires authorization.
