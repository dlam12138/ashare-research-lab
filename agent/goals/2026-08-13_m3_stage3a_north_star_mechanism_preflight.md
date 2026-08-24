# M3 Stage 3A — North-Star Mechanism Research Preflight

> Authoritative task contract. This stage freezes a daily-data research protocol. It does not acquire research data, compute a real result, inspect the holdout, or implement the mechanism-analysis engine.

## Objective

Pre-register the question, primary hypothesis, market proxy, thresholds, outcomes, controls, point-in-time alignment, sample, analysis layers, bootstrap, multiplicity policy, holdout discipline, extreme-date checks, index-contribution estimate, and evidence ceiling for the first M3 case.

Expected decision, subject to verification:

- `M3_MECHANISM_RESEARCH_CONTRACT_FROZEN`
- `M3_STAGE3B_DATA_ACQUISITION_AND_NORMALIZATION_ALLOWED`

## Verified Baseline

- M2 checkpoint tag: `m2-value-assessment-conditional-closeout` -> `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`
- M2 PR: `#2`, squash merged after PR CI `31706668191` passed
- merged `origin/main`: `7cc6a9bc51162ee3bac3748576070eb04d4904fb`
- branch: `feat/m3-mechanism-validation-mvp`, created from merged main
- branch start: `7cc6a9bc51162ee3bac3748576070eb04d4904fb`
- start local/origin: 0 ahead / 0 behind
- isolated M3 worktree: clean
- original M2 worktree, its pre-existing edit/untracked files, default DB, ignored runtime state, and stash are protected and outside this stage

## Allowed Scope

- read governance, both North-Star files, M2 closeout evidence, and existing provider interfaces;
- inventory data requirements as `AVAILABLE`, `ACQUIRABLE`, `PROXY_REQUIRED`, `DATA_ACQUISITION_REQUIRED`, or `NOT_RELIABLY_AVAILABLE` without network calls;
- create four deterministic JSON contracts, one thin offline build/verify tool, focused tests, acceptance evidence, and a work record;
- use synthetic/static fixtures only for contract validation;
- update README status minimally after acceptance;
- commit and normally push only to `feat/m3-mechanism-validation-mvp` after local validation.

## Forbidden Scope

- no real stock, index, constituent, weight, oil, industry, style, currency, turnover, or volatility acquisition;
- no real hypothesis result, conditional return, regression, coefficient, p-value, confidence interval, bootstrap result, correlation, abnormal return, offset estimate, or evidence grade;
- no holdout read or real-data pipeline execution;
- no conclusion that PetroChina supports or stabilizes the market and no inference about state/fund intent;
- no minute data, Web UI, M4 generic engine, trading signal, target price, ranking, or recommendation;
- no `mechanism/` implementation package;
- no mutation of the default DB, M2 tag/history/artifacts, original M2 worktree, protected user state, or stash;
- no direct push to main, force push, tag rewrite/deletion, feature-branch deletion, or automatic merge.

## Required Behavior

1. Freeze the canonical question exactly around 2015-to-cutoff daily evidence, ex-target Shanghai market decline, abnormal return after controls, and estimated index offset; explicitly reject the wording “is PetroChina used to support the market?”.
2. Freeze one primary H0/H1 on positive abnormal return, not raw positive return.
3. Primary market proxy is `SH_MARKET_EX_601857`; return `EX_TARGET_PROXY_EXACTLY_REPRODUCIBLE` only if point-in-time constituents and historical weights are demonstrably available. Current inventory must fail closed as `DATA_ACQUISITION_REQUIRED`.
4. Freeze primary crash threshold `-0.01`; robustness thresholds are `-0.005`, `-0.015`, and `-0.02`. Ex-post tuning is prohibited.
5. Freeze primary `abnormal_return` and secondary raw return, positive-return indicator, market-relative return, and estimated index offset. Positive-return probability is descriptive only.
6. Controls use three tiers: required market/oil/industry, main alternatives dividend/central-SOE/large-cap, and robustness-only currency/turnover/volatility/style spread.
7. Oil must be point-in-time observable before the A-share close; the primary fallback is lagged `t-1`. Same-day overseas close is prohibited.
8. Requested sample is `2015-01-01` through the frozen cutoff at `1d`; effective primary start is the common trustworthy start of required controls, with earlier days descriptive only and no forward fill.
9. Freeze descriptive, conditional, base-regression, and robustness layers without computing them.
10. Freeze moving-block bootstrap, deterministic seed, replications, CI method, and a block-length selection rule before results.
11. Freeze one unadjusted primary inference and BH-FDR for the robustness family.
12. Freeze development `2015-01-01..2022-12-31` and holdout `2023-01-01..frozen_end`; holdout remains sealed until pipeline and model digest are locked.
13. Freeze leave-one-event-out, top-1/top-3 absolute abnormal-return removal, and winsorized descriptive-only checks.
14. Keep estimated index contribution separate from abnormal return. If exact historical weight is unavailable, label it an estimate rather than official point attribution.
15. Reuse North-Star evidence levels 1-5 and cap the daily MVP at level 3.

## Required Artifacts

- `reports/m3_stage3a_mechanism_hypothesis_contract_v1.json`
- `reports/m3_stage3a_data_requirements_v1.json`
- `reports/m3_stage3a_statistical_protocol_v1.json`
- `reports/m3_stage3a_preflight_decision_v1.json`
- `src/ashare_research/tools/m3_stage3a_preflight.py`
- `tests/test_m3_stage3a_mechanism_preflight.py`
- `acceptance/m3_stage3a_north_star_mechanism_preflight.md`
- `agent/record/2026-08-13_Stage3A_north_star_mechanism_preflight.md`

## Exact Validation Commands

```powershell
python src/ashare_research/tools/m3_stage3a_preflight.py build --output-root tmp/m3_stage3a_a
python src/ashare_research/tools/m3_stage3a_preflight.py build --output-root tmp/m3_stage3a_b
# compare A/B SHA-256 maps
python src/ashare_research/tools/m3_stage3a_preflight.py verify
python -m pytest tests/test_m3_stage3a_mechanism_preflight.py -q
python -m pytest -q
python -m ruff check src tests
python -m compileall -q src tests
git diff --check
```

Also verify no network/acquisition call, no real-result field, no holdout read, no `mechanism/` package, no absolute-path/secret/cache pollution, protected M2 checkpoint/tag unchanged, default DB unchanged, and local/origin synchronization after push.

## Acceptance Criteria

PASS requires deterministic contracts, all 15 required behaviors, fail-closed data inventory, all validations passing, and no forbidden-scope behavior. The decision must be exactly `M3_MECHANISM_RESEARCH_CONTRACT_FROZEN`; the only next-stage authorization is `M3_STAGE3B_DATA_ACQUISITION_AND_NORMALIZATION_ALLOWED`.

## Stop Conditions

Stop on any real-data access, holdout access, fitted statistic, p-value/CI, threshold selection from outcomes, real mechanism conclusion, evidence above level 3, minute/Web/M4/trading work, protected-state mutation, or inability to keep required controls/proxies fail closed.

## Commit and Push Requirements

- use coherent additive commits on `feat/m3-mechanism-validation-mvp` only;
- do not amend, rebase, force push, merge, rewrite/delete the M2 tag, or delete branches;
- push normally after validation;
- do not start Stage 3B automatically.
