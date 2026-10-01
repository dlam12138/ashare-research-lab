# M2 dated financial fact explorer

Objective: deliver one usable offline batch: dated latest financial facts, two-date
version comparison, honest source/context/lineage tracing, Markdown/JSON and fresh
directory export. Continuing M2 engineering authorization; no new research stage.

Verified baseline: origin/main and live remote main
9db39e8520f733966c0357b4367c696145d4c7e4; clean owned worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance; branch
codex/m2-pit-fact-explorer. Primary feat/m2-value-assessment-mvp at
3679b1bac7a1634c6452784a4d8f6d139966f222 dirty and preserved; stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
local main remains 966206f06262e43f40c1c7aadbfb8596839eac91.

Allowed: new src/ashare_research/tools/pit_fact_explorer.py,
tests/test_pit_fact_explorer.py, README.md, this Goal,
agent/record/2026-10-01_06_m2-pit-fact-explorer.md and
acceptance/2026-10-01_m2_pit_fact_explorer.md. One bounded DSH implements first
three paths only; parent owns governance, Git and validation.

Forbidden: other code/tests, fixtures/reports/config/evidence/database changes,
network/data acquisition, external messages, metrics/scoring/ranking/backtests,
holdout/registry/Brent gates, modifying default DB, recursive delegation, model
fallback, overwrites of existing export paths. Preserve unrelated work and stash.

Required behavior: fixed committed canonical snapshot (33 facts, 5 concepts,
601857.SH), four source byte hashes pinned to verified base; use public
validate_snapshot/build_temp_fact_db/AsOfQuery.get_latest_available in an owned
TemporaryDirectory, close DB before cleanup. Required --as-of ISO date, optional
--compare-with later/equal date, repeatable --concept, --period-end and --scope
consolidated/parent_company; mutually exclusive Markdown default/--json/--output.
Strict input validation, unknown concepts rejected; truthful empty snapshots.
Select via existing PIT/verification/eligibility gates, restore exact source
value_decimal by selected fact_id (no float financial arithmetic). Compare by
concept/period/scope with distinct added/removed/value_changed/version_changed/
unchanged states, exact decimal comparison and before/after IDs. Show original
units/dates/context/lineage/parent IDs; mark unavailable parents/evidence missing,
never fabricate full source evidence or imply original availability proven anew.
Trace only PIT-eligible selected facts; future parents remain unresolved.
Stable output, no runtime timestamp; export complete rendered report.md,
report.json and hash manifest after validation/rendering into exclusive new root.
Do not read caller DB or silently default to today. Chinese readable output and
README runnable examples and retained source/evidence limitations.

Required local validation (PYTHONPATH=<owned worktree>/src):
python -m pytest -q tests/test_pit_fact_explorer.py
D:/量化分析/.venv/Scripts/python.exe -m ruff check src/ashare_research/tools/pit_fact_explorer.py tests/test_pit_fact_explorer.py
python -m ashare_research.tools.pit_fact_explorer --as-of 2024-03-31 --compare-with 2025-03-31 --concept net_profit_attributable_to_parent --period-end 2023-12-31 --output tmp/m2-pit-fact-comparison
git diff --check
Four to five meaningful tests: actual PIT boundary/restatement/source precision,
selection/empty/input errors, trace gaps/no future expansion, export determinism/
existing path safety and failure-before-output. Parent alone runs local tests;
one final targeted run, repeat only for actual fixes. Mandatory hosted workflows
retain full suite on both platforms; no full local duplication.

Acceptance: actual portable comparison artifact, independently reviewed diff,
scope/protected hashes/primary dirty snapshot/stash/DB unchanged, local tests and
Ruff pass, required hosted checks pass on exact PR head, clean mergeability.
Stop: source digest mismatch, unclear source admission, DSH failure/unavailability,
two unsuccessful repairs, failed CI/conflict/scope expansion. No bypass/fallback.
Commit/push only task branch; create scoped PR, review exact base/head and all
required checks, merge under standing AGENTS authorization. Never push main.
Parent reports PASS/CHANGES_REQUIRED/BLOCKED with actual refs, commands, files,
acceptance and protection/sync evidence. No automatic new research stage.
