# M4 direct hypothesis comparison acceptance

Local verdict: PASS.

Goal: agent/goals/2026-10-08_m4_hypothesis_compare.md.
Base origin/main and live main: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Delivery branch: codex/m4-hypothesis-compare; final commit and hosted check
evidence retained separately in tmp/hypothesis-compare-final-review.json.
Root implemented and reviewed actual code, no DSH/agents.

Seven scoped files: Goal, this acceptance, work record, README.md,
research_hypothesis_compare.py, research_entry.py and new comparison test file.
No frozen mechanism, fixtures, existing tests, CI, policy or baseline edits.

Acceptance evidence:
- Complete original left/right compiler envelopes and source-byte SHA retained.
- Identical and reformatted inputs distinguish byte equality from canonical equality.
- Threshold, reordered controls and holdout changes retain original values and
  propagate to compiled plans without authorizing execution.
- Deterministic JSON pointer changes, atomic ordered lists and absence versus
  null; numeric robustness values preserve original decimal string serialization.
- Source files loaded once per side; subsequent mutation cannot change captured
  results. Original plan command and unified legacy entry remain compatible.
- Malformed, oversized, duplicate/nonfinite/root/UTF-8 inputs, unsupported real
  identity, absent files and invalid CLI arguments fail with empty stdout.
- Explicit guards prohibit database, network, service and executor access;
  readiness/holdout/outcome/statistics/authorization all remain false.
- Markdown escapes user links, table separators, emphasis, code and HTML.

Exact local commands (PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_research_hypothesis_compare.py tests/test_research_plan.py tests/test_research_entry.py
10 passed, 1 failed in 37.35s. Failure was new test expectation [1] instead of
original compiler decimal string ["1"]. Corrected to original canonical value.
python -m pytest -q tests/test_research_hypothesis_compare.py::test_presence_types_order_and_markdown_escaping
1 passed in 0.67s; all 11 affected/compatibility cases now pass.
python -m ruff check src/ashare_research/tools/research_hypothesis_compare.py src/ashare_research/tools/research_entry.py tests/test_research_hypothesis_compare.py
All checks passed.
git diff --check
PASS.

Public subprocess demo:
python -m ashare_research.cli research hypothesis-diff --left tmp/hypothesis-compare-demo/before.json --right tmp/hypothesis-compare-demo/after.json --json
Same command without --json renders retained Markdown. Exit 0, stderr empty.
Threshold -0.01 to -0.02 yields exactly three changes: config/contract
/condition/threshold, plan /transform_plan/condition/threshold; boundaries false.

Protected state rechecked against ignored pre-implementation snapshot: primary
HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222, existing dirty/untracked state,
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f and all 314 protected hashes
unchanged. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Foreign worktree refs unchanged before commit; post-commit verification excludes
only the owned branch's expected commit advance.

Limits: existing V1 synthetic identities/vocabulary only; canonical comparison
does not establish historical evidence, improve methodology or authorize real
research. Lists produce complete-value changes rather than element edit scripts.
No automatic merge or next stage; current user governance takes precedence over
repository historical standing merge authorization. Hosted results must be
reported separately; local acceptance does not claim hosted completion.
