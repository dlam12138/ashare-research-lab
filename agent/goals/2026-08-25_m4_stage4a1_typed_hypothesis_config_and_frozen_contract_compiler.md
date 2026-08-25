# M4 Stage 4A.1 — Typed Hypothesis Config & Frozen Contract Compiler

## Status

`ACTIVE_IMPLEMENTATION`

## Objective

Implement a typed, strictly validated synthetic-only `HypothesisConfig`, an
allow-listed compiler to an immutable `FrozenMechanismContract`, canonical
serialization, semantic config identity, and deterministic contract digest.
The implementation must remain a thin generic layer over the proven M3 core
and must not execute research.

## Verified baseline

- Canonical base: `origin/main`
- Canonical SHA: `7a6668d8a683d02eabd9a860d19546fd163a20c1`
- Feature branch: `feat/m4a1-typed-hypothesis-contract`
- Isolated worktree: `D:\量化分析-m4a1`
- North-Star SHA-256: `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`
- Stage4P architecture: `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`

## Scope

- `src/ashare_research/mechanism/hypothesis_config.py`
- `src/ashare_research/mechanism/contract_compiler.py`
- focused synthetic tests and minimal public API exposure if required
- Stage4A.1 Goal, report, acceptance, and work record
- minimal README status update if needed

## Forbidden scope

- real market data, provider calls, network acquisition, or real symbols
- real hypothesis, regression, bootstrap, robustness, holdout, or outcome execution
- dataset adapter, analysis plan builder, executor, CLI execution surface
- M4-B registry, literature, anomaly, portfolio, recommendation, M5, or M6
- new dependencies or changes to proven M3 modules unless additive necessity is
  demonstrated first

## Required behavior

- schema version `M4_HYPOTHESIS_CONFIG_V1`
- strict unknown-field rejection at every mapping boundary
- explicit allow-lists for factor, condition, analysis, bootstrap/RNG, and
  evidence semantics
- canonical decimal normalization without binary-float identity drift
- ordered controls and robustness entries preserved, duplicates rejected
- frozen immutable nested contract values
- semantic config digest and contract digest exclude runtime/path metadata and
  contract digest self-reference
- safe YAML loading only; mapping root required
- compiler has no data, provider, network, or execution dependency

## Required tests and validation

- focused Stage4A.1 synthetic tests
- Stage4P governance tests
- M3 boundary tests and full `pytest -q`
- `ruff check .`
- `python -m compileall -q src tests`
- `git diff --check`
- JSON parsing and protected baseline byte-identity checks
- static no-network/no-execution import boundary checks

## Acceptance criteria

- typed config and frozen contract are distinct types
- invalid schema, fields, values, dates, allow-list items, and duplicates fail
  with stable error codes
- A/B semantically identical fixtures produce byte-identical canonical output
  and digests
- meaningful threshold/order/date/coverage/seed/robustness mutations change the
  contract digest
- no pre-existing M3 mechanism file changes
- synthetic-only boundary is demonstrated

## Stop conditions

- `M4_STAGE4A1_MAIN_MOVED`
- a new dependency is required
- proven M3 core must be rewritten
- deterministic cross-platform identity cannot be achieved
- real data or outcome is read
- required CI job fails

## Commit and push requirements

- Keep implementation and test/governance changes reviewable in a small number
  of commits.
- Push only the feature branch with ordinary push after local validation.
- Do not merge, force-push, or proceed beyond merge review.

## Boundary declarations

- `REAL_DATA_READ = NO`
- `REAL_OUTCOME_READ = NO`
- `NETWORK_ACQUISITION = NO`
- `REAL_HYPOTHESIS_EXECUTION = NO`
- `M4B = NOT_STARTED`

