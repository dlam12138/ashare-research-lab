# M4 direct hypothesis comparison

Status: completed locally; branch publication and hosted checks tracked separately.
User continuation, root alone, no DSH/agents. Verified live origin/main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b, protected primary/stash/database
and 314 file hashes; clean isolated codex/m4-hypothesis-compare worktree.
Goal established before implementation:
agent/goals/2026-10-08_m4_hypothesis_compare.md.

Implemented research hypothesis-diff --left JSON --right JSON [--json].
Reuses research_plan.build_report once per side. Complete original envelopes,
SHA256 and compiler identities retained; deterministic canonical changes exclude
derived digest fields. Lists are atomic ordered values; JSON pointers, missing
versus null, JSON-type distinctions and escaped Markdown are explicit.
No network/database/executor calls; boundaries remain false.

Validation with PYTHONPATH=src and D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_hypothesis_compare.py tests/test_research_plan.py tests/test_research_entry.py
Initial run: 10 passed, 1 failed in 37.35s. New test incorrectly expected numeric
robustness parameter [1]; the original compiler canonically serializes ["1"].
Corrected that new expectation and added original envelope equality and explicit
boolean/integer list distinction. Existing tests and compiler unchanged.
python -m pytest -q tests/test_research_hypothesis_compare.py::test_presence_types_order_and_markdown_escaping
Affected case rerun: 1 passed in 0.67s. All 11 covered cases now pass.
python -m ruff check src/ashare_research/tools/research_hypothesis_compare.py src/ashare_research/tools/research_entry.py tests/test_research_hypothesis_compare.py
git diff --check
Both PASS. No redundant full local suite.

Retained real public CLI subprocess demo under tmp/hypothesis-compare-demo:
threshold -0.01 to -0.02 yields exactly three original changes at config and
contract /condition/threshold and plan /transform_plan/condition/threshold.
JSON equals original build output; Markdown retained; boundaries false.
Independent actual source/diff/tests/Goal review and protection recheck PASS:
314 protected hashes and primary HEAD/status/stash/all worktree refs unchanged
before commit. Acceptance: acceptance/2026-10-08_m4_hypothesis_compare.md.
Final commit, branch/origin/live synchronization and hosted checks recorded in
ignored tmp/hypothesis-compare-final-review.json and final response.
No real research, acquisition, execution, merge or next stage authorized here.
