# M3 Stage 3A — North-Star Mechanism Research Preflight Acceptance

Status: LOCAL PASS — commit, push, and remote CI pending

## Decision

- Verdict: **PASS** locally.
- Decision: `M3_MECHANISM_RESEARCH_CONTRACT_FROZEN`.
- Next stage: `M3_STAGE3B_DATA_ACQUISITION_AND_NORMALIZATION_ALLOWED`.
- Stage 3B has not started.

## Scope boundary

This stage freezes a daily-data research design for the first M3 case. It does not test whether PetroChina has abnormal crash-day performance, does not estimate index offset, and does not infer a funding actor or intent.

No real market/oil/industry/style data was acquired or read. No regression, fitted statistic, p-value, confidence interval, bootstrap result, holdout result, evidence grade, minute-data analysis, Web/M4/trading work, or `mechanism/` package was produced.

## Frozen protocol

- Canonical target: `601857.SH`, daily, requested `2015-01-01..2026-08-13`.
- Primary condition: `SH_MARKET_EX_601857 <= -0.01`.
- Robustness thresholds: `-0.005`, `-0.015`, `-0.02`; ex-post tuning prohibited.
- Primary outcome: abnormal return after pre-registered controls; raw positive-return probability is descriptive only.
- Required controls: ex-target market, point-in-time-safe oil, and petrochemical industry.
- Oil alignment: latest information observable before A-share close; lagged `t-1` fallback. Same-day overseas close is prohibited.
- Effective sample begins at the common trustworthy start of required primary inputs; earlier requested history is descriptive only and never forward-filled.
- Moving-block bootstrap, seed `20260813`, 5000 replications, and percentile 95% CI are frozen before results.
- One unadjusted primary inference; robustness family uses BH-FDR at 5%.
- Development sample ends `2022-12-31`; `2023-01-01..2026-08-13` holdout is sealed until pipeline and model digest are locked.
- Extreme-date checks include leave-one-event-out and removal of top-1/top-3 absolute abnormal returns. Winsorization is descriptive robustness only.
- Index contribution is a separate estimated pipeline, never official point attribution without exact historical weights.
- North-Star evidence levels are retained; daily MVP is capped at level 3.

## Data inventory

Existing provider interfaces cover target daily prices, trade calendars, and index daily prices. They do not establish the point-in-time Shanghai constituent/weight history needed to reproduce `SH_MARKET_EX_601857`, nor the required oil and petrochemical-industry controls. The primary proxy therefore fails closed as `DATA_ACQUISITION_REQUIRED`; direct substitution with the SSE Composite is prohibited.

## Artifacts

- `reports/m3_stage3a_mechanism_hypothesis_contract_v1.json`
- `reports/m3_stage3a_data_requirements_v1.json`
- `reports/m3_stage3a_statistical_protocol_v1.json`
- `reports/m3_stage3a_preflight_decision_v1.json`
- `src/ashare_research/tools/m3_stage3a_preflight.py`
- `tests/test_m3_stage3a_mechanism_preflight.py`
- `agent/goals/2026-08-13_m3_stage3a_north_star_mechanism_preflight.md`
- `agent/record/2026-08-13_Stage3A_north_star_mechanism_preflight.md`

## Validation evidence

- Independent A/B builds: 4/4 SHA-256 maps identical.
- `python src/ashare_research/tools/m3_stage3a_preflight.py verify`: PASS.
- `python -m pytest tests/test_m3_stage3a_mechanism_preflight.py -q`: 10 passed.
- `python -m pytest -q` with `PYTHONPATH` bound to this clean worktree: 1943 passed, 3 skipped, 2 pre-existing pandas date-parser warnings.
- The first full-suite attempt inherited the original checkout's editable install and therefore mixed two repository roots. Two focused manifest tests proved the mismatch; binding `PYTHONPATH` to this worktree corrected the environment without changing tests or implementation.
- Ruff, compileall, diff-check, pollution/protected-state checks: pending final pre-commit gate.
- Remote CI: pending.

## Protected state

- M2 annotated tag must remain at `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`.
- M2 merged main baseline is `7cc6a9bc51162ee3bac3748576070eb04d4904fb`.
- Original M2 worktree state, stash, default DB, and prior artifacts remain outside this stage.
