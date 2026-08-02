# Work record: M2 Stage 2I ROIC methodology and fact readiness

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `f79824b74e909edb9d34709ea4f38b7f49c38440`
- Task source: `agent/goals/2026-08-02_m2_stage2i_roic_methodology_and_fact_readiness.md`
- Module: value assessment / official financial facts / engineering governance

## Objective

Complete the authoritative M2 Stage 2I contract: perform a fresh North-Star
Review after Stage 2H.1R, freeze a transparent ROIC methodology, audit
PetroChina FY2020-FY2025 canonical official-fact readiness and PIT/restatement
coverage, produce the minimum official acquisition plan, and run at most one
isolated non-production shadow feasibility calculation if the evidence gate
allows. Stop at the Stage 2I decision without creating a production ROIC
Metric or opening scoring, Web, target-price, recommendation, automatic
trading, or market-mechanism work.

## Scope and non-goals

In scope are the Stage 2I review, ROIC methodology/input/readiness contracts,
deterministic readiness audit, minimal official acquisition plan, optional
non-production shadow feasibility evidence, tests, acceptance and records.
The default database, stash, protected `354 Fact / 102 Metric Result / 16
definitions` baseline, existing value profile and all untracked
`agent/goals/` files are protected. No production ROIC metric or definition,
scoring, Web, target price, recommendation, automatic-trading, or
market-mechanism work is in scope.

## Starting state

- Branch: `feat/m2-value-assessment-mvp`; HEAD and origin both equal
  `f79824b74e909edb9d34709ea4f38b7f49c38440`.
- Worktree: only the user-provided untracked `agent/goals/` directory is
  present; no additional worktree is listed.
- Remote: `origin` is
  `https://github.com/dlam12138/ashare-research-lab.git`; upstream is
  `origin/feat/m2-value-assessment-mvp`; ahead/behind is `0/0`.
- Stash: `stash@{0}` remains
  `protect pre-existing Stage 1B.4 record edit before Stage 1C`.
- Default DB: `data/research.duckdb`, SHA-256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline: `354 Fact / 102 Metric Result / 16 definitions`.
- Prior Stage 2H.1R acceptance records a successful pre-edit remote CI run
  `30744466406` and successful post-push Ubuntu/Windows runs
  `30745949298` and `30746189865`.
- The current repository has no Stage 2I files or production ROIC metric.

## Mandatory review completed before implementation

Read the authoritative Stage 2I contract, both project North-Star documents,
`CLAUDE.md`, `agent/agent.md`, `agent/record/README.md`, the latest three
work records, Stage 2G/2H/2H.1/2H.1R acceptance records, `README.md`, the value
fact coverage roadmap, the existing capital-return methodology/config, and
the current project governance boundaries. Remaining code/standards review
and the fresh North-Star gate are recorded below as they are executed.

## Plan

1. Finish the North-Star and mature-project/academic/official review before
   freezing ROIC policy; stop if the review is `BLOCKED`.
2. Freeze NOPAT, tax, invested capital, cash, debt, leases, NCI, associates/JV,
   goodwill, averaging, PIT and restatement policies before any shadow output.
3. Audit FY2020-FY2025 official canonical Fact readiness with deterministic
   status, exact IDs, PIT/version lineage and explicit gaps.
4. Produce the smallest official acquisition plan for one internally
   consistent candidate and run at most one isolated shadow feasibility run if
   the evidence gate permits.
5. Run local/clean-clone/Ubuntu/Windows gates, review protected state, create
   scoped commits and push, then record the single Stage 2I decision and stop.

## Decision log

- North-Star Review completed in `docs/post_risk_veto_north_star_review.md`.
  Decision: `ALLOWED`. The review is qualitative, answers all eight required
  questions, and keeps scoring/market-mechanism work out of scope.
- Methodology frozen before inspecting any shadow result: Candidate B
  operating-profit bridge + financing-view invested capital; direct operating
  tax required; no silent cash subtraction, ending-only balance, net-profit
  NOPAT, generic debt, manual plug, or LLM inference.
- Evidence gate after the readiness audit:
  `BLOCKED_WITH_EXPLICIT_GAPS`. Because the gate did not allow a value
  feasibility run, no ROIC shadow was executed.

## Actual operations

- Added North-Star review, frozen methodology/config/input contracts,
  deterministic canonical inventory and readiness implementation, readiness
  reports, acquisition plan, Stage 2I acceptance, and focused tests.
- Ran the pre-production readiness command with the committed inventory:
  `PYTHONPATH=src python -m ashare_research.tools.roic_fact_readiness
  --output-dir reports`.
- The current canonical inventory was derived from an isolated run-scoped
  foundation artifact; the default DB remained untouched. The selected ROIC
  input inventory contains 64 eligible canonical Facts from the protected
  354-Fact evidence baseline.

## Verification

- `python -m json.tool config/value_evaluation_methodology_roic_v1.json`:
  passed.
- `python -m pytest -q tests/test_roic_stage2i.py`: `3 passed`.
- `python -m pytest -q`: `970 passed, 2 warnings in 152.44s`; the warnings
  are the pre-existing date-format warnings in `tests/test_quality.py`.
- `ruff check src/ tests/`: passed after formatting the new readiness tool
  and focused test.
- Clean clone at the committed Stage 2I state replayed the readiness command,
  focused test (`3 passed`), and Ruff successfully.
- Full clean-clone suite: `970 passed, 2 warnings in 151.81s`; the same two
  pre-existing date-format warnings were observed.
- Readiness output: `BLOCKED_WITH_EXPLICIT_GAPS`, shadow `NOT_RUN`, production
  Metric/Metric Result/value profile all false.
- Readiness coverage: 11 ready selected input concepts in each of
  FY2021-FY2025, plus FY2020 opening parent equity and total assets. Explicit
  gaps include direct operating tax, finance/non-operating decomposition, NCI,
  cash-purpose classification, qualifying non-operating assets, goodwill,
  associate/JV scope, interest-bearing long-term payables and the operating
  liability reconciliation view.
- The default DB hash, stash, protected baseline and untracked goal files were
  checked before implementation and are preserved pending final verification.

## Result

Stage 2I is complete through the evidence decision and is waiting only for
the required final local/clean-clone/Ubuntu/Windows delivery gates. Decision:
`ROIC_FACT_ACQUISITION_REQUIRED`.

## Open issues

- Official acquisition is required under the minimum batch in
  `docs/roic_official_fact_acquisition_plan.md`; the listed missing concepts
  are not to be backfilled by a proxy or formula switch.
- A shadow feasibility value was intentionally not produced because the
  evidence gate is blocked.

## Final Git state

Pending final delivery-gate verification, scoped commit and push.
