# M4 verified plan comparison acceptance

Contract: agent/goals/2026-10-07_m4_plan_compare.md.
Verified base: codex/m4-plan-archive@1640ee54aec0fc20f283734a226a2eda86917862.
Root performed the work directly, without DSH or delegated agents.

Implemented read-only research plan-compare for two independently verified
directory/native ZIP inputs, including mixed containers. Existing verifiers and
compilers are unchanged. Config, contract and plan differences have deterministic
RFC6901 pointers, positional list handling, strict scalar types and explicit
present/value wrappers. Source-byte identity is separate from canonical equality;
known top-level digest identities appear separately from content rows. JSON and
escaped Markdown preserve complete values and all six false execution boundaries.
There is no research execution, scoring, independent seal or readiness authority.

Exact local validation (PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe):

```
python -m pytest -q tests/test_research_plan_compare.py
python -m ruff check src/ashare_research/tools/research_plan_compare.py src/ashare_research/tools/research_entry.py tests/test_research_plan_compare.py
git diff --check
python tmp/m4-plan-compare-demo.py
```

Final targeted result: 3 passed in 1.22s; Ruff all checks passed; diff check passed.
Initial targeted run: 1 failed, 2 passed, exposing Markdown identity iteration
order dependent on JSON round-tripping. Fixed the renderer to use an explicit
identity order; reran the affected file successfully. No existing test changed.
Tests cover mixed verified inputs, source/compiled identities, exact differences,
reverse comparison, format-only changes, immutable/relocated inputs, offline
guards, missing/null/type distinctions, escaped pointers/Markdown, corruption,
missing/linked inputs, argument rejection and one-read verified snapshots.

Actual CLI subprocess demo: 10 changes (config2/contract2/plan6), JSON and Markdown
both successful; all seven source/package/archive input hashes unchanged. Actual
Windows junction fails with LINKED_PACKAGE_PATH, code2 and empty stdout. Evidence:
tmp/m4-plan-compare-demo/evidence.json and comparison.json/comparison.md.

Completion gate: independent committed seven-file diff/Goal review, original408
protected hashes, primary dirt/refs/stash/database, both dependency worktrees and
foreign registrations intact; clean owned tree, local/origin/live head identical,
all exact-head hosted checks successful. Final immutable commit/PR/check results
and actual hosted test summaries are recorded in tmp/m4-plan-compare-final-review.md
after the gate. This document does not claim pending hosted checks have passed.

Stacked PR targets codex/m4-plan-archive; depends on PR69, then PR68, which remain
open. No merge or following stage authorized by this completion. Content comparison
does not establish an independent seal, historical provenance or execution readiness.
