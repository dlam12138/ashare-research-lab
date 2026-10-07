# M4 compile-only plan comparison acceptance

Base: origin/live main 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Branch: codex/m4-plan-comparison. Goal:
agent/goals/2026-10-07_m4_plan_comparison.md.

Delivered optional research plan --compare-with JSON. Before/after full original
compiled reports and actual input byte SHA256 retained. Canonical config changes
use JSON pointer paths, explicit presence flags, atomic ordered lists and exact
JSON value comparison (including boolean versus number). No comparison of
derived duplicate compiler fields; no statistical inference from edits.
Same source path is loaded once. Different input paths load once each; source
mutation after read does not alter retained compilation or loaded-byte identity.
Formatting-only change is canonical equivalence, not a semantic change.
All execution/readiness/source-validation/holdout flags remain false.
Invalid second input produces sanitized stderr only and no partial stdout.

Actual commands (PYTHONPATH=src; D:/量化分析/.venv/Scripts/python.exe):

```powershell
python -m pytest -q tests/test_research_plan.py tests/test_research_plan_comparison.py tests/test_research_entry.py
python -m pytest -q tests/test_research_plan_comparison.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_entry.py tests/test_research_plan_comparison.py
python -m ashare_research.cli research plan --hypothesis docs/examples/m4_hypothesis.json --compare-with docs/examples/m4_hypothesis.json --json
git diff --check
```

Initial targeted run: 8 passed in 38.48s. Review improved JSON-type comparisons
and sorted escaped pointer paths; affected new tests rerun: 2 passed in 0.78s.
Ruff and whitespace checks pass. Public CLI smoke: IDENTICAL_SOURCE_BYTES;
same_source_bytes and same_canonical_config true, changes empty. No full-suite
local run, no failed tests, no existing test edits. Hosted checks are separate.

Protected primary HEAD/status/stash and captured hashes unchanged. All 427
tracked reports/config/fixture hashes unchanged. Foreign worktree HEAD/branch
identities unchanged. A foreign provider acquisition tree has unrelated routing
edits; it was read-only and its initial file hashes were not captured, so this
review does not claim its byte-for-byte protection or full ignored-runtime audit.
Primary snapshot covers 21 hashes including database; one Git-quoted non-ASCII
untracked path was not included in the hash snapshot, although status is unchanged.
No database connection or source acquisition occurred.

Local verdict: PASS. Commit/push and PR identifiers are final Git evidence,
reported in the final packet. Current user instructions require explicit merge
authorization; no automatic merge or next stage. Real research remains sealed.
