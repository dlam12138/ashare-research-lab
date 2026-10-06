# Focused comparison acceptance

Base origin/live main1893ba0309b0c416cd366b186127b42273c70425;
branch codex/m2-focused-comparison. Root alone, no DSH/agents. Goal
agent/goals/2026-10-06_m2_focused_comparison.md.

research compare accepts repeatable --metric ID/--year YEAR and --changes-only,
with or without --evidence. Selectors deduplicated/sorted; no default latest year.
Whole existing comparison verifier map used once per side, then exact original
metric/year entries selected. Plain change filtering uses original financial
states; evidence mode also includes changed fields and expands only changed roles.
Complete original report retained in explicit focused schema with selectors,
original/selected key counts and selected role count. Source objects not mutated.
Markdown clearly labels selection/counts and renders only selected original rows/
roles with unchanged source/parent/history notes. Empty matches are explicit
successful results; unknown metric/year distinct errors. Invalid selectors or
focus with --output fail before source load/output creation. No selector preserves
old metric/evidence output/export bytes. No arithmetic, imputation, new source/
data/research, causality/quality/transitive claims, cache or retained rereads.

Exact local commands (owned tree PYTHONPATH=src; python is
D:/量化分析/.venv/Scripts/python.exe):
```powershell
python -m pytest -q tests/test_comparison_focus.py
python -m ruff check src/ashare_research/tools/comparison_focus.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_comparison_focus.py
git diff --check
```
Targeted run2passed41.52s. Ruff/diff PASS; formatting/import order corrected before
tests, one reading-note wording simplified after tests, no behavior change or
rerun. No full local suite/repeated targeted run, old tests untouched.
Actual pinned session/ZIP verify exact original selected rows/states/bindings,
duplicate selectors, plain/evidence changes, unchanged missing values, valid empty
results, legacy default schemas/evidence equality, invalid/unknown selectors,
fail2/no partial stdout/output for export mixes, forged outer ZIP rejection,
verified canonical map used once after mutation and next fresh read rejects it.
Independent synthetic selection specimen verifies an unchanged supplied financial
state does not hide field differences, only changed roles included, source not
mutated. This specimen is not a retained-source research finding.

Retained original public CLI demo, exit0:
python -m ashare_research.cli research compare --left-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-view compare_with --evidence
--metric cash_based_free_cash_flow_proxy --year 2023 --changes-only --json
Saved tmp/m2-focused-comparison-demo/{focused.json,focused.md}; Markdown rendered
from already verified JSON envelope, no source ZIP reread. Source7metric keys,
selected1original2023cash-proxy key/2changed roles, original view dates and full
source/history/parent gaps retained. Source SHA256 unchanged
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.

Eight-file scope; original comparison/evidence render/build/export functions,
verifiers/engine/old tests/baselines/CI unchanged. Physical exact original primary
dirty/untracked snapshot, HEAD3679b1b/main966206f/stashcb568efd,427protected hashes
and databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 preserved.
Independent actual committed branch/HEAD/diff/Goal/acceptance/tests/refs/protection
review and all hosted gates/exact head/base/CLEAN before standing-authorized merge.
Final hosted/postmerge evidence tmp/m2-focused-comparison-final-review.md.
No automatic next stage; fixed snapshot/source/history limitations remain.
