# M2 Stage 2K.1R4F.4B — Post-5Y PE North-Star Disposition

> Authoritative task contract. This stage freezes the disposition after R4F.4A1. It is a decision-and-verification closeout, not a new financial-data or scoring implementation stage.

## Objective

Decide, using only committed evidence through R4F.4A1, what status PE has in M2, whether the scoring addendum may be conditionally closed, and whether M3 North-Star preflight (design only) may be the next separately authorized stage.

Expected selected disposition, subject to verification:

- `PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE`
- `M2_SCORING_ADDENDUM_CONDITIONAL_CLOSEOUT_ALLOWED`
- `M3_NORTH_STAR_PREFLIGHT_ALLOWED`

## Verified Baseline

- branch: `feat/m2-value-assessment-mvp`
- local HEAD at start: `d5acfd8615ff35022853bb5391ceb58368bea90b`
- origin branch at start: `d5acfd8615ff35022853bb5391ceb58368bea90b`
- ahead/behind at start: `0/0`
- origin main at start: `9e016e772156fe689cbf77ed1febd772833c830e`
- stash at start: `stash@{0}: On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4 record edit before Stage 1C`
- pre-existing tracked modification: `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`
- pre-existing untracked state includes `AGENTS.md`, `agent/goals/`, and `agent/record/2026-08-08_01_Stage2K1R4F3A_precondition_check.md`

All pre-existing local changes, untracked files, ignored runtime artifacts, default databases, and stash entries are protected and outside this stage except this newly authorized Goal file and the explicitly required 4B deliverables.

## Allowed Scope

- read and verify R4F, R4F.1, R4F.2, R4F.3, R4F.3A, R4F.4, R4F.4A, and R4F.4A1 committed artifacts;
- add a thin offline `verify-upstream` / `build` / `verify` CLI that reads committed artifacts only;
- add a deterministic North-Star disposition matrix in JSON and Markdown;
- add a machine-readable PE disposition decision contract;
- add focused tests, acceptance evidence, a work record, and the minimum README status update;
- verify protected artifact hashes, default DB hash, deterministic A/B output, path/secret hygiene, and regression tests;
- create at most two coherent commits and perform a normal push only after all required validation passes.

## Forbidden Scope

- no historical extension beyond frozen 5Y and no 2014-or-earlier economic-fact acquisition;
- no Brent, WTI, industry-cycle, peer-company, or other new acquisition;
- no future EPS/outcome read;
- no new PE percentile computation, threshold tuning, or outcome-driven method selection;
- no PE numeric component score, zero imputation, valuation-weight redistribution, production score, overall score, rank, recommendation, or target price;
- no M3 implementation;
- no default DB modification, upstream artifact rewrite, history rebase/amend, force push, or direct push to main;
- no weakening, deletion, skipping, or rewriting of tests to obtain a pass.

## Required Behavior

- exact upstream R4F.4A1 decision must be trusted;
- readiness must remain `1211/1211`, blocked `0`;
- episode evidence must remain 1 candidate, 0 observed onset, 1 left-censored, 0 valid onset episode, and 0 mature at 4Q/8Q;
- `future_eps_values_read` must remain false;
- raw PE and 3Y/5Y percentiles remain descriptive trusted evidence;
- PE component and valuation-dimension numeric scores remain null/false, never zero;
- PB/PS weights are not renormalized around the blocked PE component;
- M2 remains `CONDITIONALLY_CLOSED`; the scoring addendum becomes `CONDITIONAL_CLOSEOUT_ALLOWED`;
- next stage is `M3_NORTH_STAR_PREFLIGHT`, while implementation remains unauthorized;
- method reopening is allowed only for a new pre-registered method, a new independent evidence class, or a material North-Star change; history-only extension, ex-post threshold tuning, and outcome-driven method selection are prohibited.

## Required Tests and Exact Validation Commands

Run in this order:

```powershell
python src/ashare_research/tools/m2_stage2k1r4f4b_post_5y_pe_disposition.py verify-upstream
python src/ashare_research/tools/m2_stage2k1r4f4b_post_5y_pe_disposition.py build --output-root tmp/r4f4b_a
python src/ashare_research/tools/m2_stage2k1r4f4b_post_5y_pe_disposition.py build --output-root tmp/r4f4b_b
# compare A/B SHA-256 maps
python src/ashare_research/tools/m2_stage2k1r4f4b_post_5y_pe_disposition.py verify
python -m pytest tests/test_m2_stage2k1r4f4b_post_5y_pe_disposition.py -q
# run targeted regressions for R4F through R4F.4A1 plus R4F.4B
python -m pytest -q
python -m ruff check src tests
python -m compileall -q src tests
git diff --check
```

Also verify default DB SHA-256 unchanged, protected upstream artifact hashes unchanged, stash unchanged, pre-existing local edits unchanged, no absolute-path/secret/cache pollution, and local/origin synchronization as applicable.

## Acceptance Criteria

PASS requires every required behavior above, deterministic committed artifacts, all required validations passing, protected state unchanged, and no forbidden-scope behavior. The final stage decision is exactly `PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE`.

If the North Star demonstrably requires an M2 PE number, stop with `M2_SCORING_ADDENDUM_REMAINS_OPEN_METHOD_REDESIGN_REQUIRED`; do not extend history. Any forbidden behavior or mutation yields `POST_5Y_PE_DISPOSITION_NOT_TRUSTED`.

## Stop Conditions

Stop immediately on future-outcome access, numeric PE assignment, zero imputation, weight renormalization, production/overall scoring, ranking/recommendation, new >5Y/commodity/peer acquisition, M3 implementation, upstream mutation, default DB mutation, or inability to preserve pre-existing user state.

## Commit and Push Requirements

- maximum two commits: one implementation/decision freeze and one CI/status evidence closeout;
- do not stage unrelated pre-existing changes or protected untracked files;
- no amend, rebase, force push, direct main push, merge, PR, tag, or release;
- a normal push is permitted only after validation and review evidence are complete;
- do not begin M3 automatically.
