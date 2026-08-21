# M3 Stage 3C-A acceptance

## Verdict

`PASS — CI CONFIRMED / STOP_FOR_NORTH_STAR_REVIEW`

This acceptance closes the synthetic-only Stage 3C-A pipeline lock. It does not
authorize real development execution or holdout access.

## Contract

- Goal/task contract: `agent/goals/2026-08-21_m3_stage3ca_pipeline_lock_and_synthetic_validation.md`
- New locked contracts:
  - `reports/m3_stage3ca_analysis_pipeline_contract_v1.json`
  - `reports/m3_stage3ca_model_specification_v1.json`
  - `reports/m3_stage3ca_robustness_registry_v1.json`
  - `reports/m3_stage3ca_output_schema_v1.json`

## Baseline and scope

- Verified base branch: `feat/m2-value-assessment-mvp`
- Verified base commit: `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`
- No Stage 3A/3C implementation or R4 readiness artifact was present on this
  checked-out baseline. Upstream Stage 3A identities are therefore bound as
  declared frozen identities in the model digest; no external raw contract or
  market file was read.
- Existing user changes, untracked governance files, protected baselines,
  default database, and stash were preserved.

## Implementation

- Added isolated `src/ashare_research/mechanism/` modules for input contracts,
  crash construction, fixed-order statsmodels OLS, control-only abnormal
  returns, PCG64 non-circular MBB, descriptive/conditional summaries,
  robustness transforms, BH-FDR, evidence cap, and separate pipeline/model
  digests.
- Added `src/ashare_research/tools/m3_stage3ca_pipeline.py`; only
  `--execution-mode synthetic` is accepted. Development mode returns
  `REAL_ANALYSIS_NOT_AUTHORIZED`; dates on/after 2023-01-01 return
  `HOLDOUT_SEALED`.
- Added `statsmodels>=0.14.6,<0.15` as a direct dependency.
- README now records Stage 3C-A locked/synthetic-only status. No old frozen JSON
  was changed.

## Acceptance evidence

- `tests/test_m3_stage3ca_pipeline.py`: 35 passed.
- Coverage includes positive/null/negative/extreme fixtures, exact crash
  boundary, schema and validity gates, adjusted/unadjusted mixing rejection,
  fixed design order/intercept, missing-value failure, MBB boundaries and
  PCG64 reproducibility, strict primary decision, extreme/year/threshold
  robustness, BH-FDR, evidence cap, digest separation, and synthetic output
  schema.
- Synthetic output contains only `analysis_input_manifest.json`,
  `mechanism_primary_result.json`, and `mechanism_robustness_result.json`;
  `real_inputs_read=false` and `holdout_sealed=true`.

### Exact validation results

```text
pytest -q tests/test_m3_stage3ca_pipeline.py
35 passed

pytest -q
1971 passed, 2 warnings

ruff check src/ tests/
All checks passed

python -m compileall -q src tests
PASS

JSON contract parse
4 contracts valid

python -m ashare_research.tools.m3_stage3ca_pipeline --execution-mode synthetic --fixture positive --output tmp/stage3ca-smoke
PASS; bootstrap.replications=5000; seed=20260813; rng=PCG64

python -c "import statsmodels; print(statsmodels.__version__)"
0.14.6
```

The two warnings are pre-existing pandas date-inference warnings in
`tests/test_quality.py`; no Stage 3C-A test warning remained.

## Repository evidence at handoff

- Final branch remains `feat/m2-value-assessment-mvp`; the final commit and
  origin synchronization are recorded in the handoff evidence below.
- The verified base was `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d` and the
  delivery was committed in four focused commits, then pushed to the matching
  feature branch as requested.
- The protected stash remains present and untouched.
- The pre-existing modified acceptance file, `AGENTS.md`, and pre-existing
  untracked M2 goal/record files remain untouched; only the Stage 3C-A files,
  README, and `pyproject.toml` belong to this implementation. `tmp/stage3ca-smoke`
  is an ignored synthetic runtime output.
- `git diff --check` passed. No destructive cleanup, branch switch, reset,
  force-push, merge, or PR was performed.

## Final state

```text
M3_STAGE3CA_PIPELINE_LOCK_ACCEPTED
M3_ANALYSIS_PIPELINE_LOCKED
M3_MODEL_SPECIFICATION_LOCKED
M3_MODEL_DIGEST_LOCKED
M3_TIER1_DEVELOPMENT_INPUTS_READY
M3_DEVELOPMENT_REAL_ANALYSIS_NOT_YET_EXECUTED
M3_HOLDOUT_REMAINS_SEALED
M3_STAGE3CB_DEVELOPMENT_REAL_EXECUTION_ALLOWED
M3_HOLDOUT_REAL_EXECUTION_NOT_ALLOWED
STOP_FOR_NORTH_STAR_REVIEW
```

No Stage 3C-B execution is included or started by this acceptance.
