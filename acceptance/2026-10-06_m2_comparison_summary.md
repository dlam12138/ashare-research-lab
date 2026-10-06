# Verified comparison summary acceptance

Goal agent/goals/2026-10-06_m2_comparison_summary.md; base origin/live main
02bb6e9038f71b6d01ea5d62072950c012629d7e, branch codex/m2-comparison-summary.
Root alone, no DSH/agents.

research compare --summary [--json] consumes completed original comparisons,
including evidence, metric/year/changes selection and direct fact selection.
No extra verification/selection or source reread/cache/restoration. New
m2_verified_comparison_summary_v1 retains complete source_report, exact original
selected metric rows/states/values/units, original selected evidence entries and
fact references, selector/count and original side context. Markdown compactly
shows original values/units/statuses/classifications, dates/views/scopes/requests/
manifests, selected roles and direct references with parent original statuses.
Empty selection explicit; null and unselected distinct. Original notes preserved
through all wrappers; raw evidence field JSON expansion omitted only in Markdown.
No arithmetic, conversion/delta/rank/score, causal/indirect/quality interpretation,
new data/research or qualification. Summary/output mixes fail before source load
or path creation. Without summary all original outputs/export bytes unchanged.

Exact local commands, PYTHONPATH=src and Python
D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_comparison_summary.py
python -m ruff check src/ashare_research/tools/comparison_summary.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_comparison_summary.py
git diff --check
```
One targeted run2passed40.53s; scoped Ruff and diff PASS. One line-length fixed
before testing, no failed test run/repeat/full local suite or old tests edited.
Two actual pinned directory/ZIP cases cover plain/evidence/plain-focus/evidence-
focus/fact-focus output and exact rows/roles/refs/units/context/notes, missing versus
unselected/added, valid empty and legacy output, no source mutation; invalid export
before loading absent sources, unknown fact, whole outer forgery rejection and
canonical handoff once after mutation with subsequent fresh rejection.

Actual retained public CLI demonstration, exit0/no stderr:
python -m ashare_research.cli research compare --left-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-view compare_with
--fact 7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289
--evidence --changes-only --summary --json
Saved tmp/m2-comparison-summary-demo/{summary.json,summary.md}; Markdown rendered
from already verified envelope. Source7keys selected3/6roles/3original left refs,
all original dates/units/classifications/limitations retained. SourceZIP SHA256
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561 unchanged.

Eight-file scope. Existing comparison prefix before class _Parser unchanged;
original evidence/focus/fact modules, engine/verifiers/old tests/CI/baselines
untouched. Physical primary dirty/untracked snapshot, HEAD3679b1b/main966206f/
stashcb568efd/databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
427protected hashes and foreign worktrees preserved. Independent actual committed
scope/Goal/tests/acceptance/refs/protections and all required hosted gates/exact
head/base/CLEAN before standing-authorized merge. Final hosted/postmerge packet
tmp/m2-comparison-summary-final-review.md. Next stage requires continuation.
