# M3 Stage 3C-A — Mechanism Analysis Pipeline Lock & Synthetic Validation

## Objective

Freeze and implement the Stage 3C-A mechanism-analysis method before any real
PetroChina mechanism result is inspected. Produce machine-readable contracts,
synthetic-only execution, locked OLS/MBB inference, robustness transforms,
evidence capping, and model/pipeline digests.

## Verified baseline

- Branch: `feat/m2-value-assessment-mvp`
- HEAD: `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`
- Remote: `origin/feat/m2-value-assessment-mvp` at the same observed tip
- Existing worktree changes: one modified acceptance file, untracked
  `AGENTS.md`, existing M2 goal files, and one protected stash.
- No Stage 3A/3C implementation or R4 readiness artifact exists on this
  baseline; the implementation therefore records upstream contract identities
  without reading external raw data.

## Allowed scope

- New Stage 3C-A contracts, mechanism analysis modules, synthetic fixtures,
  tests, README status text, task acceptance, and work record.
- Add the `statsmodels>=0.14.6,<0.15` dependency.
- Add a dedicated synthetic-only CLI entry point.

## Forbidden scope

- Reading, acquiring, or analyzing R1/R4 external raw files, real 601857 rows,
  real crash dates/counts, real regression matrices, or any holdout data.
- Changing frozen legacy JSON, M2 artifacts, the default database, unrelated
  user changes, branches, remotes, stash entries, or protected baselines.
- Development/holdout execution, data-source work, automatic merge, PR, or
  push.

## Required behavior

- Input schema, adjusted close-to-close/simple return semantics, development
  boundary, crash threshold, fixed design-matrix order, control-only abnormal
  return, primary decision rule, PCG64 MBB, descriptive/conditional layers,
  robustness registry, evidence cap, execution gate, output schema, and digest
  separation are frozen in the four Stage 3C-A JSON contracts.
- Only `--execution-mode synthetic` is accepted. Development mode fails closed
  with `REAL_ANALYSIS_NOT_AUTHORIZED`; dates on/after 2023-01-01 fail closed
  with `HOLDOUT_SEALED`.
- Stage 3C-A emits synthetic fixture results only; no real-version output is
  created.

## Required tests and exact validation commands

```powershell
pytest -q tests/test_m3_stage3ca_pipeline.py
pytest -q
ruff check src/ tests/
python -m compileall -q src tests
python -m ashare_research.tools.m3_stage3ca_pipeline --execution-mode synthetic --fixture positive --output tmp/stage3ca-smoke
```

## Acceptance criteria

- Contracts are valid JSON and all required frozen constants are tested.
- Positive, null, negative, extreme-driven, missing-control, duplicate-date,
  unsorted-date, and holdout fixtures behave as specified.
- Focused and full offline tests, Ruff, compileall, and synthetic CLI smoke
  pass without reading real external inputs.
- Pipeline and model digests are deterministic and distinct.
- Final status is `M3_STAGE3CA_PIPELINE_LOCK_ACCEPTED`; development and
  holdout remain sealed.

## Stop conditions

Stop after synthetic validation and evidence recording. Do not proceed to
Stage 3C-B or unlock real development/holdout execution.

## Commit and push requirements

The user-requested delivery is approximately four focused commits on the
current feature branch, followed by a normal push to its matching origin
branch. Do not create a PR, merge, force-push, or change branches. Stage only
the files belonging to this task; preserve unrelated worktree changes.
