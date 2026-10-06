# Direct fact comparison acceptance

Goal agent/goals/2026-10-06_m2_fact_comparison.md; base origin/live main
e61b4673bd0417e79d8ea0f8447f3949156687d4, branch codex/m2-fact-comparison.
Root own execution, no DSH/agents.

Repeatable research compare --fact ID selects original metric keys referring to
requested facts in either before/after original inputs or direct parent entries.
Facts deduplicated/sorted, OR among facts and intersection with existing metric,
year and changes-only filters, with or without evidence. Any unknown requested
fact fails FACT_NOT_REFERENCED against complete original comparison, including
when the other valid filters yield empty. Known empty intersection succeeds.
Invalid empty/whitespace fact or fact/output mix fails before source load/output.
New m2_verified_fact_comparison_v1 retains complete original report via
comparison.source_report and exact selected original entries/bindings/states.
References retain side, metric, year, fact, role, input/direct-parent kinds, full
original input and matched original parents. Parent gaps remain unresolved;
references concern original selected metric keys, even if evidence changes-only
hides unchanged roles. No causal/indirect inference, arithmetic, data/research,
evidence upgrading, cache/restoration/reread. Original whole verification once
per side; no fact leaves default/evidence/focus/export behavior unchanged.

Exact local commands with PYTHONPATH=src, Python
D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_fact_comparison.py
python -m ruff check src/ashare_research/tools/fact_comparison.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_fact_comparison.py
git diff --check
```
One targeted run: 2 passed in61.06s. Ruff/diff PASS. Actual parent status and
explicit operating-cash-flow role checked before testing; no failed runs, old
tests modified, local full suite or repeated targeted run. Two pinned directory/
ZIP cases check exact direct input and missing-parent references, both sides and
repeated/multiple facts, combined selectors/empty unchanged/legacy outputs,
source immutability, invalid/unknown/export rejection/no partial stdout/output,
forged outer file rejection and verified canonical map consumed once after
mutation with the next fresh read rejecting it.

Public retained demo (exit0):
python -m ashare_research.cli research compare --left-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-view
compare_with --fact 7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289
--evidence --changes-only --json
Saved tmp/m2-fact-comparison-demo/{comparison.json,comparison.md,summary.json};
source7metric keys selected3/6changed input roles,3original left references.
Markdown rendered from verified JSON, no source reread. Original ZIP SHA256
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561 unchanged.
All original source/parent/history limitations retained.

Eight-file scope; original session comparison before class _Parser, focus and
evidence builders/renderers, engine/verifiers/old tests/CI/baselines unchanged.
Primary dirty/untracked snapshot, HEAD3679b1b/main966206f/stashcb568efd and database
SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
427protected hashes and foreign worktrees preserved. Independent actual scope/
code/Goal/tests/acceptance/refs/protection review and all required hosted gates/
exact base/head/CLEAN before standing-authorized merge. Final hosted/postmerge
packet tmp/m2-fact-comparison-final-review.md. No automatic next stage.
