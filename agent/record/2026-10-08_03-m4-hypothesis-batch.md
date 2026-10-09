# M4 declared inputs across multiple hypotheses

Status: locally completed; publication/hosted status reported separately.
Current user continuation, root alone, no DSH/agents. Actual origin/live main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b. Previous PR88/89 remain open,
completed checks successful; full CI still pending at preflight.
Clean isolated codex/m4-hypothesis-batch, no dependency on either open PR.
1355 protected primary files and 55 foreign worktree statuses/refs captured,
primary dirty state, HEAD, database and stash unchanged.
Goal established before implementation:
agent/goals/2026-10-08_m4_hypothesis_batch.md.

Added research plan-batch --hypothesis JSON (repeat, 1..16) [--json].
Original build_report called once per argument, complete source reports/SHA/
config/contract/plan/digests retained. Original requirements grouped by declared
series ID with exact requirement index/plan digest/sample plan/universe scope.
Stable source/group ordering, descriptive name overlap and role-independent
requirement differences; no window/gate/identity merging or compatibility claim.
Counts measure original hypotheses/roles/series only, all boundaries false.
Output bounded 8MiB, invalid count/options before loading, duplicates and invalid
source reject entire batch with stable stderr and empty stdout.

Actual validation, PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_hypothesis_batch.py tests/test_research_plan.py tests/test_research_entry.py
12 passed in 42.96s, no test failure.
Independent review added explicit legal minimum/maximum batch coverage:
python -m pytest -q tests/test_research_hypothesis_batch.py::test_minimum_and_maximum_allowed_batches_preserve_all_plans
2 passed in 0.82s; 14 distinct scoped/legacy cases successfully covered.
python -m ruff check src/ashare_research/tools/research_hypothesis_batch.py src/ashare_research/tools/research_entry.py tests/test_research_hypothesis_batch.py
git diff --check
Final both PASS. Initial Ruff four line-length findings fixed before test run;
no disabled checks, existing test changes or repeated full local suite.

Retained public subprocess JSON/Markdown at tmp/hypothesis-batch-demo.
Two explicit synthetic hypotheses: 8 original role requirements, 6 declared
series IDs, 2 shared names. A control used as another plan's factor retains
different transform declarations; moved control slot alone is not a declaration
difference. 2020/2021 starts, 0.99/0.98 coverage and universe A/B remain separate.
Reversed CLI argument order produces byte-identical JSON; sources unchanged,
per-use requirement/index matches original plan and false boundaries retained.

Reviewed actual code/diff/Goal/test evidence, precommit protection review PASS:
1355 primary data/reports/config/events/fixtures/output/runs hashes, dirty status,
HEAD/database/stash and 55 foreign worktree statuses/refs unchanged; live main
still verified base. Acceptance: acceptance/2026-10-08_m4_hypothesis_batch.md.
Final commit/PR/actual committed blob review/protection/local-origin-live sync and
hosted snapshots in ignored tmp/hypothesis-batch-final-review.json.
Current user governance overrides repository historical standing merge policy:
no automatic merge, acquisition, statistics, holdout or next stage.
