# M4 multi-hypothesis plan inventory acceptance

Local verdict: PASS.
Goal: agent/goals/2026-10-08_m4_hypothesis_batch.md.
Actual origin/live base: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Branch: codex/m4-hypothesis-batch, independent of open PR88/89.
Final commit/PR/hosted snapshot: tmp/hypothesis-batch-final-review.json.
Root implementation and independent repository evidence review, no DSH/agents.

Seven scoped files: this acceptance, Goal, work record, README.md,
tools/research_hypothesis_batch.py, tools/research_entry.py,
tests/test_research_hypothesis_batch.py. Original research_plan/engine/compilers,
existing tests/fixtures/contracts/reports/CI/governance remain unchanged.

Acceptance evidence:
- Complete original source reports/byte SHA/config/contract/plan and compiler
  identities preserved; each original file consumed once even after mutation.
- Counts are original hypothesis/role/declared-series counts. Stable source/group
  sorting produces identical JSON under reordered arguments; no path/clock fields.
- Every use binds original requirement index, exact requirement object, original
  plan digest, complete sample window/quality policy and universe requirement.
- Shared control versus factor retains different transform declarations.
  Different control slot alone is excluded from declaration comparison.
  Heterogeneous windows, coverage gates and universes remain explicit and separate.
- Duplicate hypothesis IDs, invalid source JSON/UTF-8/root/duplicates/nonfinite/
  oversized source, real identity policy, absent files and invalid count/options
  reject without partial stdout. Counts 1 and 16 pass; 0 and 17 reject.
- Source-envelope, aggregate-envelope and Markdown output limits tested; default
  8MiB maximum enforced before output. Markdown escapes links/HTML/emphasis/table
  separators; original digests, methods, gates and holdout boundaries visible.
- Network/database/service/executor guards and false authorization/readiness/
  statistics/holdout/outcome/source-validation boundaries preserved.

Exact commands (PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_research_hypothesis_batch.py tests/test_research_plan.py tests/test_research_entry.py
12 passed in 42.96s.
python -m pytest -q tests/test_research_hypothesis_batch.py::test_minimum_and_maximum_allowed_batches_preserve_all_plans
2 passed in 0.82s. All 14 distinct scoped/legacy cases covered successfully,
no test failures or changes to existing tests.
python -m ruff check src/ashare_research/tools/research_hypothesis_batch.py src/ashare_research/tools/research_entry.py tests/test_research_hypothesis_batch.py
All checks passed; initial four formatting findings fixed before tests.
git diff --check
PASS.

Public subprocess:
python -m ashare_research.cli research plan-batch --hypothesis tmp/hypothesis-batch-demo/first.json --hypothesis tmp/hypothesis-batch-demo/second.json --json
Same command without --json produces retained Markdown. Exit 0, stderr empty.
Counts: 2 hypotheses, 8 role requirements, 6 names, 2 shared declarations.
Reverse arguments: exact same JSON bytes. Both source hashes unchanged,
original per-use requirements verified against retained source plans.

Protected baseline: primary 3679b1bac7a1634c6452784a4d8f6d139966f222,
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
All 1355 data/reports/config/events/fixtures/output/runs hashes and 55 foreign
worktree statuses/refs unchanged at precommit audit. Includes previously ignored
primary runtime output/runs. Primary existing edits/untracked files preserved.
Final audit excludes only expected owned HEAD advance.

Limits: existing synthetic V1 identities, compiler reproduction only. Shared
names and role-independent requirement differences do not establish actual
source identity/interchangeability, common sample timing/PIT evidence, compatible
data, readiness, research findings, sealing or authorization. No window/gate
merging, registry mutation, source acquisition, statistical or holdout execution.
Local acceptance does not claim hosted completion; hosted exact-head state and
local/origin/live refs recorded separately. No automatic merge or next stage.
