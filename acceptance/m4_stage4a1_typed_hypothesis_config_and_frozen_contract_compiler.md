# M4 Stage 4A.1 Acceptance — Typed Hypothesis Config & Frozen Contract Compiler

## Verdict

`PASS — READY_FOR_M4A1_MERGE_REVIEW`

## Scope accepted

This slice implements a synthetic-only typed hypothesis configuration and a
pure compiler to a separate immutable `FrozenMechanismContract`.

- Typed config implemented: `HypothesisConfig` and nested frozen specs.
- Strict validation implemented, including stable error codes.
- Unknown root and nested fields rejected fail-closed.
- Factor, condition, analysis, bootstrap, identity, and evidence allow-lists
  enforced.
- Canonical decimal normalization is finite, plain notation, zero-normalizing,
  and free of binary-float JSON identity.
- Ordered controls and robustness entries are preserved; duplicates fail.
- Frozen contract uses immutable dataclasses and tuples.
- Canonical UTF-8 JSON serialization has fixed separators, sorted keys,
  `ensure_ascii=false`, and one final newline.
- Config and contract digests reuse `model_digest.canonical_digest`.
- Synthetic A/B fixtures have exact semantic, dict, byte, and digest identity.
- Threshold, control order, date, coverage, seed, and robustness mutations all
  change the contract digest.

## Explicit exclusions

- No real market data, target symbols, provider calls, or network acquisition.
- No real outcome, regression, bootstrap, robustness, holdout, or hypothesis
  execution.
- No dataset adapter, analysis plan builder, executor, or execution CLI.
- No M4-B registry, literature, anomaly, portfolio, recommendation, M5, or M6.

## Evidence

- Implementation contract: `reports/m4_stage4a1_typed_config_and_compiler_contract_v1.json`
- Synthetic identity proof: `reports/m4_stage4a1_synthetic_compile_identity_v1.json`
- Focused tests: `tests/test_m4_stage4a1_typed_contract.py`
- Goal: `agent/goals/2026-08-25_m4_stage4a1_typed_hypothesis_config_and_frozen_contract_compiler.md`
- Work record: `agent/record/2026-08-25_Stage4A1_typed_hypothesis_config_and_frozen_contract_compiler.md`

## Architecture and stop

`M4_ARCHITECTURE = THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`

`M4-B = NOT_STARTED`

`REAL_HYPOTHESIS_EXECUTION = NOT_AUTHORIZED`

`STOP_FOR_M4A1_MERGE_REVIEW`

