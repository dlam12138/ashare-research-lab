# Focused delivered metrics acceptance

Goal agent/goals/2026-10-06_m2_focused_review.md; verified base origin/live main
06e868291f68ed50b23c0d09ec51730a8da5ecff, branch codex/m2-focused-review.
Root alone, no DSH/agents.

read/review supports repeated metric/year and missing-only. Exact original rows
and original comparison entries retained; filters intersect, repeated values OR,
unknown metric/year checked against full original request. Missing-only selects
original value null, never zero; comparison includes keys in either selected
view and preserves the populated counterpart. State counts count selected original
labels without reclassification; complete original counts retained in source_read.
Original view dates/fact totals, row statuses/units/history/roles/date fields,
notes and metric limitations remain. Full original verified read envelope/receipts
retained under new focused schema; known empty explicit, no completeness inference.
Invalid IDs/years/section flags reject before load. Audit focus behavior preserved;
no flags preserve legacy JSON/Markdown. Complete original fresh outer verification
and canonical byte map once; no reread/restoration/cache, financial computations,
evidence upgrading, acquisition or qualification.

Exact local commands, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_review_focus.py
python -m pytest -q tests/test_review_focus.py::test_original_rows_comparisons_missing_zero_empty_and_legacy
python -m ruff check src/ashare_research/tools/review_focus.py src/ashare_research/tools/delivered_research.py src/ashare_research/tools/research_entry.py tests/test_review_focus.py
git diff --check
```
Initial two cases passed in28.21s. Independent review identified projected state
counts should reflect selected entries; affected case rerun1passed16.63s after
that correction. Ruff/diff PASS; one line length corrected before testing, no
failed tests/full local suite, existing tests unchanged. Pinned review DIR/ZIP
cases verify exact rows/comparisons/counts/null/zero/missing/history fields,
duplicates/empty/no comparison/legacy and immutable source; invalid flags before
absent-source load, unknown codes, forged outer review, verified map handed off
once after source mutation then next fresh read rejects it.

Public CLI retained workflow ZIP demonstration, exit0/no stderr:
python -m ashare_research.cli research read --archive
tmp/m2-handoff-walkthrough/delivery.zip --section review
--metric cash_based_free_cash_flow_proxy --year 2023 --json
Saved tmp/m2-focused-review-demo/{review.json,review.md}; Markdown rendered from
already verified envelope, output inspected. Selects2of14original metric rows/
1original comparison. Exact values17407700.000000000000 and17433900.000000000000
万元 and original 数值变更（重述） state retained. Source ZIP SHA256 unchanged
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.

Eight-file scope; original delivered reader prefix before class _Parser exactly
unchanged. Original review/audit build/render/export/schema, audit focus, old
tests/engine/verifiers/comparison/CI/baselines unchanged. Original primary dirty/
untracked snapshot/HEAD3679b1b/main966206f/stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
427 protected path/hash lines and foreign worktrees preserved. Actual committed
code/scope/Goal/tests/acceptance/refs/protections independently reviewed; all
required hosted exact-head/base/CLEAN gates before standing-authorized merge.
Final hosted/postmerge packet tmp/m2-focused-review-final-review.md.
Original source/parent/history gaps remain. Next stage requires continuation.
