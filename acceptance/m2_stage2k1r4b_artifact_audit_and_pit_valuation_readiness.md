# M2 Stage 2K.1R4B — Artifact/Sensitivity Audit Patch and PIT Valuation Readiness Review

Status: `PASS` (CI-backed run `30907234491` on ubuntu + windows; no production scores, no peer acquisition, no M3)

## Objective

Two strictly separated parts:

- **Phase A (engineering patch):** (1) a real artifact manifest verifier that
  recomputes hashes; (2) `verify-artifacts` CLI wired to it with fail-closed exit
  codes; (3) a complete per-scenario sensitivity ledger v6.
- **Phase B (readiness review only):** review whether PIT historical PE/PB/PS is
  implementable. No valuation series, no downloads, no scoring expansion.

## Scope

- `src/ashare_research/scoring/artifact_manifest.py` (new real verifier)
- `src/ashare_research/scoring/sensitivity.py` (v6 ledger)
- `src/ashare_research/tools/m2_stage2k1r3_closeout.py` (verify-artifacts → real verifier)
- Tests: `tests/test_m2_stage2k1r4b_artifact_and_sensitivity_audit.py` (37),
  `tests/test_m2_stage2k1r4b_pit_valuation_readiness.py` (23)
- Docs: `docs/pit_valuation_denominator_readiness_review.md`
- Reports: `petrochina_dimension_scoring_sensitivity_v6.json`,
  `pit_valuation_denominator_readiness_matrix.json`,
  `m2_stage2k1r4b_artifact_verification.json`,
  `m2_stage2k1r4b_engineering_old_new_diff.json`, `m2_stage2k1r4b_decision.json`,
  `m2_stage2k1r4b_artifact_manifest.json`
- Acceptance: this file

## Non-goals

- No historical PE/PB/PS series, no valuation-percentile vNext, no new capsule, no
  production Metric Result, no peer database, no M3 artifact.
- No modification of scoring weights, thresholds, or valuation results.
- No relaxation of `stability_tolerance=1.0`; NOT_STABLE preserved.
- No modification of `market_observation_set.py` business semantics.
- No modification of the default DB, protected baselines, protected local files, or
  the pre-existing Stage 2I.2R wording edit.
- No `.codex/`, `.claude/`, or git hooks.

## Requirements status

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Real artifact manifest verifier (recomputes hashes) | DONE | `artifact_manifest.verify_artifact_manifest`; `normalize_lf`; 10 rules; `test_manifest_*` |
| 2 | LF-normalized SHA-256 + byte_size (unified helper) | DONE | `normalize_lf`; `test_normal_lf_consistency`, `test_normal_lf_preserves_other_bytes` |
| 3 | manifest_digest = SHA-256(canonical excluding manifest_digest) | DONE | `manifest_digest`; `test_manifest_digest_recomputable` |
| 4 | Verifier detects missing/tampered/duplicate/absolute/../schema | DONE | `test_manifest_{modified_bytes,modified_hash,modified_byte_size,missing_file,duplicate_path,absolute_path,parent_traversal,unsupported_schema,not_json_object}` |
| 5 | CLI verify-artifacts uses real verifier; `--manifest` arg | DONE | `test_cli_verify_manifest_*` |
| 6 | CLI exit codes 0/1/2 (never 3); `--output` preserves failure | DONE | `test_cli_verify_manifest_pass_exit_0`, `..._fail_exit_1`, `..._output_preserves_failure`, `..._missing_exit_2` |
| 7 | Sensitivity v6 full per-scenario ledger (6 classes) | DONE | `test_sensitivity_six_scenario_classes_all_present` |
| 8 | confidence_threshold counted in ledger/scenario_count/type_counts/confidence_block | DONE | `test_sensitivity_confidence_scenarios_counted` |
| 9 | missing_roic includes current_gap/synthetic_neutral/no_roic_component | DONE | `test_sensitivity_current_gap_roic_scenario_exists` |
| 10 | synthetic_neutral flags complete | DONE | `test_sensitivity_synthetic_roic_flags_complete` |
| 11 | summary recomputable from ledger; ledger_digest + validator | DONE | `test_sensitivity_summary_recomputable_from_ledger`, `test_sensitivity_tamper_fails_validation`, `test_sensitivity_digest_tamper_fails_validation` |
| 12 | scenario_id deterministic; unique ids | DONE | `test_sensitivity_scenario_ids_unique`, `test_sensitivity_same_input_a_b_digest_same` |
| 13 | stability_tolerance=1.0; NOT_STABLE preserved; gates independent | DONE | `test_sensitivity_tolerance_still_one`, `test_sensitivity_stability_not_stable_preserved`, gate independence tests |
| 14 | Phase B readiness: actual repo inventory | DONE | review doc + matrix (market close present, no total_market_cap/shares; financial annual-only; no quarterly TTM) |
| 15 | Route comparison + 4 approaches; close proxy rejected | DONE | review doc; `test_*` boundary tests |
| 16 | Final decision in allowed enum; PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED | DONE | matrix + decision JSON; `test_decision_*` |
| 17 | No series/scoring/peer/M3 generated | DONE | `test_no_historical_series_generated`, `test_no_production_score_generated`, `test_no_peer_acquisition_started`, `test_no_m3_started` |

## Judgment

- **Artifact manifest verification: TRUSTED** — hashes are recomputed over
  LF-normalized content; tampering is detected.
- **Manifest tamper rejection: TRUSTED** — modified bytes/hash/size fail.
- **CLI verify-artifacts exit semantics: TRUSTED** — 0/1/2, never 3.
- **Sensitivity scenario ledger: TRUSTED** — 6 classes, per-scenario records.
- **Sensitivity summary recomputation: TRUSTED** — `validate_sensitivity_ledger`
  recomputes the summary and digest from the ledger.
- **Sensitivity scenario classes: 6.**
- **Sensitivity stability: NOT_STABLE** (honest, unfabricated).
- **Historical close-price observation set: TRUSTED** (unchanged).
- **Historical PE-TTM PIT readiness: MISSING** (no quarterly net profit).
- **Historical PB PIT readiness: PARTIAL** (annual equity only, no MRQ).
- **Historical PS-TTM PIT readiness: MISSING** (no quarterly revenue).
- **3-year / 5-year valuation window: BLOCKED** (TTM denominators missing).
- **PIT announcement-date contract: PARTIAL** (draft, not implemented).
- **Restatement/supersession readiness: TRUSTED** (financial facts carry it).
- **Share-capital/market-cap route: UNRESOLVED** (recommendation MARKET_CAP).
- **PIT valuation decision: PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED.**
- **Valuation-attractiveness shadow: NON_PRODUCTION_AND_NOT_INTERPRETABLE.**
- **Production scoring: NOT CREATED. Peer acquisition: NOT ALLOWED.**
- **Stage 2K decision: SCORING_CONTRACT_GAPS_REMAIN. Market mechanism: NOT STARTED.**
- **Next-stage implementation: NOT STARTED.**

## Validation

(Covered in the work record's verification section; the full 26-gate order is run
before the final report.)

## Git state

- Branch: `feat/m2-value-assessment-mvp`; pushed to `origin`; CI run `30907234491`
  PASS on ubuntu + windows.
- Protected files (AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB, stash)
  untouched.
- No force push, no reset --hard, no git clean.