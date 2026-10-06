# Compare original metrics by direct fact references

Objective: root alone, no DSH/agents. Connect existing fact lookup and verified
comparison with repeatable research compare --fact ID, combinable with metric,
year, changes-only and evidence selectors. Base origin/live main
e61b4673bd0417e79d8ea0f8447f3949156687d4 verified, owned clean branch
codex/m2-fact-comparison. Primary HEAD3679b1b/main966206f/stashcb568efd and
original dirty/untracked snapshot unchanged; database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
427 protected hashes and foreign worktrees preserved.

Allowed eight files: this Goal; acceptance/2026-10-06_m2_fact_comparison.md;
agent/record/2026-10-06_05-m2-fact-comparison.md; README.md;
src/ashare_research/tools/{fact_comparison,session_compare,research_entry}.py;
tests/test_fact_comparison.py. Ignored demo/review evidence allowed. Forbidden:
existing tests, comparison_focus/evidence builders, original build/render/export
functions and schemas, verification/engine/CI/data/baselines, acquisition,
backtests/holdout, indirect dependency/causal claims, user changes/databases/stash,
foreign worktree edits, main/force push and destructive cleanup.

Required: normalized deduplicated explicit fact IDs, empty/whitespace and export
mix rejected before source load. Complete fresh original verification once per
side; unknown fact (including any unknown in a repeated selection) returns
FACT_NOT_REFERENCED against the complete compared original before/after inputs
and direct parent entries, independent of other filters. Requested facts use OR;
metric/year/changes selectors intersect their matching original metric keys.
Known empty intersection succeeds explicitly. New fact comparison schema retains
complete original report through the focused comparison source_report; selected
rows/states/bindings unchanged. Matched original references record side, metric,
year, fact, role, input versus direct-parent kind, complete original binding and
matched parent records. Missing parents stay unresolved. Evidence changes-only
role behavior unchanged; references describe original selected keys including
unchanged roles, not causal influence. No fact selector preserves all existing
default/evidence/focus/export behavior and bytes. No reread/cache/restoration,
arithmetic, imputation, scoring, evidence upgrading or new research.

Exact local commands with PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_fact_comparison.py
python -m ruff check src/ashare_research/tools/fact_comparison.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_fact_comparison.py
git diff --check
Two meaningful pinned session/ZIP cases: original direct input and missing-parent
selection on both sides, repeated/multiple facts, combined selectors/empty,
original states/evidence/legacy behavior; invalid/unknown/export errors,
forged outer archive rejection and canonical handoff once then fresh rejection.
One targeted run, affected failure reruns only; no full local suite. Retained ZIP
public CLI demonstration, original source hash unchanged.

Acceptance: exact selected original keys and references, no mutation/inference,
known-empty and unknown distinct, legacy behavior unchanged; local pass, exact
eight-file scope and physical protection. Normal commit/push/PR. Independently
inspect actual branch/HEAD/diff/Goal/acceptance/tests/refs/protections and all hosted
required gates/exact head/base/CLEAN before standing-authorized merge documented
in tracked AGENTS.md. Stop on failure/conflict/drift/scope expansion, no bypass.
Final PASS/CHANGES_REQUIRED/BLOCKED evidence packet. Next stage requires continuation.
