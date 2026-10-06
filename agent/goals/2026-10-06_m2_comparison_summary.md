# Compact reading of verified metric and evidence comparisons

Objective: root alone, no DSH/agents. Formalize the retained one-page comparison
reading artifact as research compare --summary [--json], compatible with existing
evidence, metric/year/changes and fact selectors. Verified base origin/live main
02bb6e9038f71b6d01ea5d62072950c012629d7e, clean owned branch
codex/m2-comparison-summary. Original primary HEAD3679b1b/main966206f/stashcb568efd,
dirty/untracked snapshot, databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
427protected path/hash lines and foreign worktree heads/branches verified.

Allowed eight files: this Goal; acceptance/2026-10-06_m2_comparison_summary.md;
agent/record/2026-10-06_06-m2-comparison-summary.md; README.md;
src/ashare_research/tools/{comparison_summary,session_compare,research_entry}.py;
tests/test_comparison_summary.py. Ignored demo/review evidence allowed. Forbidden:
existing tests, focus/evidence/fact builders/renderers, original comparison
build/render/export functions/schemas, verification/engine/CI/data/baselines,
acquisition/backtests/holdout, extra calculations/quality/causal/indirect claims,
user changes/stash/databases/foreign trees, main/force push/destructive cleanup.

Required: summary consumes completed verified report once, no source reread or
second comparison/selection. Plain, evidence, focused and fact-focused reports
all supported. Exact selected original metric rows/states/values/units preserved;
left/right requested views/dates/scopes/manifests/limitations shown. Explicit
counts, selectors, original selected evidence roles and matching direct fact
locations shown compactly, with no raw field/parent JSON expansion in Markdown.
Null metric values distinct from unselected metric, empty selections explicit;
original source/parent/history limitations remain. New summary schema retains
complete source_report and exact original rows, selected evidence and fact refs.
--summary with --output rejected before source load/path creation. No flag keeps
all old default/evidence/focus/fact outputs/export bytes unchanged. No arithmetic,
unit conversions, delta/ranking/scores, imputation, qualification or new research.

Exact local commands, PYTHONPATH=src, Python
D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_comparison_summary.py
python -m ruff check src/ashare_research/tools/comparison_summary.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_comparison_summary.py
git diff --check
Two pinned session/ZIP cases: all report modes/exact rows/units/roles/refs/notes,
empty/missing/unselected, no mutation/legacy output, invalid/export/unknown errors,
whole outer forgery rejection and canonical verified handoff once after mutation
with next fresh read rejecting it. One targeted run, affected failure reruns only;
no full local suite. Actual retained ZIP public CLI demo with source hash unchanged.

Acceptance: exact original values/states/presence and compact contextual reading,
complete original source retained, existing behavior untouched; targeted pass,
exact eight-file scope, protected physical snapshot unchanged. Normal commit/push/
PR; independent actual committed code/Goal/tests/acceptance/refs/protections and
all required hosted exact-head/base/CLEAN gates before standing-authorized merge
documented in tracked AGENTS.md. Stop on failure/conflict/drift/scope expansion;
no bypass. Final PASS/CHANGES_REQUIRED/BLOCKED packet; next stage needs continuation.
