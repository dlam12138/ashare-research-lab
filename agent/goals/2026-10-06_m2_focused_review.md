# Read selected original delivered metrics and missing results

Objective: root alone, no DSH/agents. Extend research read --section review
with repeatable --metric/--year and --missing-only for original metric rows
and corresponding original comparisons. Verified base origin/live main
06e868291f68ed50b23c0d09ec51730a8da5ecff; new codex/m2-focused-review.
Owned clean; original primary HEAD3679b1b/main966206f/stashcb568efd and dirty/
untracked snapshot unchanged. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
427 protected path/hash lines and foreign worktree heads recorded before edits.

Allowed eight files: this Goal; acceptance/2026-10-06_m2_focused_review.md;
agent/record/2026-10-06_08-m2-focused-review.md; README.md;
src/ashare_research/tools/{review_focus,delivered_research,research_entry}.py;
tests/test_review_focus.py. Ignored demo/review evidence allowed. Forbidden:
existing tests/read_report function/original review or audit builders/renderers/
schemas/exports, verification/comparison/engine modules/CI/baselines/data,
acquisition/backtests/holdout, new calculations/evidence upgrading, user changes/
stash/databases/foreign worktree edits, main/force push or destructive cleanup.

Required: explicit sorted/deduplicated selectors; empty/whitespace metric IDs,
years<1 and section-incompatible flags rejected before source loading. Audit
selectors retain previous behavior; compare rejects focus. Review disallows fact/
gaps-only; audit disallows missing-only. Whole existing outer verification once,
original read_report byte map reused without reread/cache/restoration. Unknown
metrics/years against complete original request fail METRIC_NOT_SELECTED/
YEAR_NOT_SELECTED. Filters intersect, repeated selectors OR. Missing-only means
original value is null, never zero or inferred missingness. Exact selected rows,
units/status/missing-role/history/date fields remain unchanged. Comparison entries
retain original before/after values/states for keys present in selected rows of
either original view; missing-only can therefore retain a populated counterpart.
Projected comparison state counts count selected original labels only; original
full state counts remain in source_read, no classification or financial recompute.
Original view dates/fact counts are not filtered or reinterpreted. Known empty
intersection succeeds explicitly and is not proof of completeness. New focused
schema retains full verified source envelope/receipts/request/notes/limitations,
selected counts and projected review. No flags preserves exact legacy output.

Exact local commands, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_review_focus.py
python -m ruff check src/ashare_research/tools/review_focus.py src/ashare_research/tools/delivered_research.py src/ashare_research/tools/research_entry.py tests/test_review_focus.py
git diff --check
Two meaningful pinned review DIR/ZIP cases: exact row/comparison filtering,
null/zero distinction/history/empty/legacy/source immutability; invalid/unknown
selectors, forged outer report and canonical map handoff once then fresh reject.
One targeted run, affected failure reruns only, no full local suite. Original ZIP
public CLI demo, original SHA preserved. Independent scope/code/Goal/acceptance/
actual branch/HEAD/diff/tests/refs/protections review and all existing required
hosted exact-head/base/CLEAN gates before standing-authorized scoped merge per
tracked AGENTS.md. Normal commit/push/PR; stop on failure/conflict/drift/scope
expansion, no bypass. Acceptance: original values/rows/comparisons exact, legacy
unchanged, local PASS, eight-file scope and all protected snapshots unchanged.
Final PASS/CHANGES_REQUIRED/BLOCKED packet; next stage requires continuation.
