# Stage 2K.1R4F.4A record

Task contract: the user-supplied R4F4A specification, materialized in `acceptance/m2_stage2k1r4f4a_independent_cycle_context_validation_preflight.md`. `agent/goals/` was preserved because the task explicitly protects it.

Baseline: branch `feat/m2-value-assessment-mvp`, commit `f1ef8ecb6615ce172e1cdfb4202a1b91e4979a46`, origin tracking point synchronized at verification time. The pre-existing modified acceptance file, untracked governance/goals/record files, and `stash@{0}` were preserved.

Implementation freezes future-realized-earnings reversion as primary, 4Q as primary horizon, 8Q as robustness, and current-earnings persistence as falsification benchmark. The single 3Y regime is machine-derived and explicitly left-censored. Its first observed date is not substituted for the unknown onset, formal anchor fields are null, and its target metadata availability is separated from protocol-valid maturity. The resulting valid onset-anchored mature counts are zero at both horizons and current validation is not executable. Readiness reads metadata only; no future EPS amount, 5Y fact, Brent value, score, or production outcome is produced.

Closeout correction: 5Y backfill is justified primarily to recover the left-censored onset if present within the frozen window and secondarily to expand independent-episode opportunity. It guarantees neither onset recovery nor recurrence, executability, or favorable results. Automatic extension beyond frozen 5Y is prohibited and requires a new North-Star review.

Decision: `PE_INDEPENDENT_CYCLE_VALIDATION_PROTOCOL_FROZEN_5Y_BACKFILL_REQUIRED` (stage verdict PASS). The repository governance final verdict is recorded after final independent validation.

Closeout status before the implementation push: `PASS — LOCAL CANDIDATE`; remote CI `PENDING`. R4F.4A1 remains `NOT STARTED`.

## Validation evidence

- `python -m pytest tests/test_m2_stage2k1r4f4a_independent_cycle_validation_preflight.py -q` — 19 passed.
- R4F1/R4F2/R4F3/R4F3A/R4F4 focused regression command — 196 passed.
- `python -m pytest -q` — 1905 passed, 2 pre-existing pandas date-parsing warnings.
- `python -m ruff check .` — passed.
- `python -m compileall -q src tests` — passed.
- R4F4A CLI `verify` — all three derived artifacts matched.
- `git diff --check` — passed.
- JSON, secret-like value, absolute user path, and trailing-whitespace scan across 13 stage files — passed.

Protected SHA-256 baselines remained unchanged: registry v2 `3fa988b…`, policy v2 `16b4099…`, shadow inputs v2 `7c9dffd…`, capsule v5 `dd94621…`, shadow v6 `c60ddef…`, sensitivity v8 `0541174…`, and default DB `4a71d3c…`.
