# Work record: M2 Stage 2K.1R4B — Artifact/Sensitivity Audit Patch and PIT Valuation Readiness Review

Status: `in_progress`

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `85e1390`
- Task source: user directive (M2 Stage 2K.1R4B — Artifact/Sensitivity Audit Patch and PIT Valuation Readiness Review)
- Module: value assessment (engineering closeout + PIT valuation readiness review)

## Verified opening state

- Branch `feat/m2-value-assessment-mvp`; HEAD `85e1390cc7d52c7ff49cf6ddc656fd44735c8266` == expected `85e1390`; no intervening commits.
- Remote: single `origin` (https://github.com/dlam12138/ashare-research-lab.git); ahead 0 / behind 0 vs origin.
- Worktree: single (root only).
- Stash: `stash@{0}` (Stage 1B.4 record edit) preserved, untouched.
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` (unchanged).
- 354 Fact baseline verified (`config/roic_canonical_fact_inventory_v2.json` fact_count=354); 102 Metric Result / 16 definitions baseline per prior acceptance (not re-derived in the default DB, which stores schema/metadata only; results live in output snapshots).
- Acceptance present: Stage 2K, 2K.1R, 2K.1R2, 2K.1R3, 2K.1R4A (Stage 2J closeout recorded in goal doc).
- Capsule v3 (`petrochina_score_input_capsule_v3`), shadow v5 (`petrochina_dimension_scoring_shadow_v5`), sensitivity v5 (`petrochina_dimension_scoring_sensitivity_v5`) current.
- Latest CI: run `30897901437` PASS on ubuntu + windows (Stage 2K.1R4A closeout).
- Protected local files all intact and untouched: `AGENTS.md`, `agent/goals/`, Stage 2I.2R pre-existing unstaged wording edit (`acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md` is `M` in git status).

## Task objective

Two strictly separated parts:

- **Phase A (engineering patch):** (1) implement a real `artifact_manifest.py` verifier
  that actually recomputes hashes; (2) fix `verify-artifacts` CLI to call it with
  fail-closed exit codes; (3) add a complete per-scenario sensitivity ledger v6.
- **Phase B (readiness review only):** review whether PIT historical valuation
  (PE/PB/PS) is implementable. No production valuation series, no downloads, no
  scoring expansion.

## Required starting points (recorded as instructed)

1. `verify-artifacts` currently only lists `artifact_logical_path` from the capsule
   `resolved_records` and returns `pass`; it does not recompute any hash.
2. Current manifest (`reports/m2_stage2k1r4a_artifact_manifest.json`) uses LF-normalized
   SHA-256 and `byte_size` = LF-normalized length.
3. Sensitivity v5 has six logic classes but no per-scenario ledger; summary is
   computed directly, not from a ledger.
4. `confidence threshold` is not part of the unified scenario count (only in the
   per-dimension `confidence_gate_sensitivity` summary).
5. Current market observation set is a close-price series (unadjusted), computed
   from the external verified cache; it has no historical PE/PB/PS.
6. Current historical PE/PB/PS PIT series is NOT implemented (Stage 2G valuation
   observations for PE/PB/PS are `missing_input` / `computed`, but the PE/PB/PS
   denominator series is not built).
7. `valuation_attractiveness` shadow is `NON_PRODUCTION_AND_NOT_INTERPRETABLE`
   (close-percentile only; not a PE/PB/PS percentile).
8. This round does NOT modify scoring weights, thresholds, or valuation results.

## Scope

- `src/ashare_research/scoring/artifact_manifest.py` (new)
- `src/ashare_research/scoring/sensitivity.py` (v6 ledger)
- `src/ashare_research/tools/m2_stage2k1r3_closeout.py` (verify-artifacts → real verifier)
- Tests: `tests/test_m2_stage2k1r4b_artifact_and_sensitivity_audit.py`,
  `tests/test_m2_stage2k1r4b_pit_valuation_readiness.py`
- Docs: `docs/pit_valuation_denominator_readiness_review.md`
- Reports: `petrochina_dimension_scoring_sensitivity_v6.json`,
  `pit_valuation_denominator_readiness_matrix.json`,
  `m2_stage2k1r4b_artifact_verification.json`,
  `m2_stage2k1r4b_engineering_old_new_diff.json`,
  `m2_stage2k1r4b_decision.json`, `m2_stage2k1r4b_artifact_manifest.json`
- Acceptance: `acceptance/m2_stage2k1r4b_artifact_audit_and_pit_valuation_readiness.md`

## Non-goals

- Do NOT build historical PE/PB/PS series, valuation percentile vNext, new capsule,
  production Metric Result, peer database, or M3 artifacts.
- Do NOT modify scoring weights, thresholds, or valuation results.
- Do NOT relax `stability_tolerance=1.0`; do NOT force STABLE.
- Do NOT modify `src/ashare_research/scoring/market_observation_set.py` business semantics.
- Do NOT modify the default DB, protected baselines, protected local files, or the
  pre-existing Stage 2I.2R wording edit.
- Do NOT create `.codex/`, `.claude/`, or git hooks.
- Do NOT stage/modify/rollback/clean protected files.

## STOP_HOOK_STATUS

`STOP_HOOK_STATUS=NOT_TRUSTED_EXTERNAL` (registered only; no `.codex/`, `.claude/`, or `.git/hooks` touched).

## Implementation plan

1. (this record) record opening state.
2. Phase A-1: implement `artifact_manifest.py` (normalize_lf, manifest_digest,
   verify_artifact_manifest, ArtifactManifestVerification).
3. Phase A-2: wire `verify-artifacts` CLI to the real verifier; add `--manifest`.
4. Phase A-3: add sensitivity v6 ledger (SensitivityScenario, 6 classes,
   confidence_threshold in count, current_gap/synthetic_neutral/no_roic_component,
   ledger_digest, validate_sensitivity_ledger).
5. Phase A tests.
6. Phase B: write readiness review + matrix (actual repo inventory), freeze
   candidate definitions + PIT time-selection contract, compare 4 approaches, choose
   readiness decision.
7. Phase B evidence tests.
8. Acceptance + reports + manifest.
9. Run full verification order (26 gates); final report.

## Actual operations

1. Verified opening state (branch `feat/m2-value-assessment-mvp`, HEAD `85e1390`,
   DB `4a71d3c7`, stash `stash@{0}`, protected AGENTS.md / agent/goals/ /
   Stage 2I.2R edit intact; CI `30897901437` PASS).
2. Created work record (this file).
3. Phase A-1: implemented `src/ashare_research/scoring/artifact_manifest.py`
   (`normalize_lf`, `manifest_digest`, `verify_artifact_manifest`,
   `ArtifactManifestVerification`). Verified against the R4A manifest (11 files,
   pass). Confirmed the CLI now detects the modified `m2_stage2k1r3_closeout.py`
   as a hash mismatch (proving the verifier is real).
4. Phase A-2: wired CLI `verify-artifacts` to the real verifier; added `--manifest`
   (defaults to the current stage's committed manifest). Exit codes 0/1/2 (never 3);
   `--output` preserves the real failure exit code.
5. Phase A-3: added sensitivity v6 ledger to `sensitivity.py` (`SensitivityScenario`,
   `build_sensitivity_v6`, `_summary_from_ledger`, `ledger_digest`,
   `validate_sensitivity_ledger`). Six scenario classes incl. confidence_threshold
   and missing_roic (current_gap/synthetic_neutral/no_roic_component). Generated
   `reports/petrochina_dimension_scoring_sensitivity_v6.json`.
6. Wrote `tests/test_m2_stage2k1r4b_artifact_and_sensitivity_audit.py` (37 tests).
7. Phase B: wrote `docs/pit_valuation_denominator_readiness_review.md` and
   `reports/pit_valuation_denominator_readiness_matrix.json` from the actual repo
   inventory (market close present, no total_market_cap/shares; financial annual-only,
   no quarterly → TTM not constructible; share timeline total-ordinary non-canonical).
   Decision: `PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED`; route UNRESOLVED
   (recommendation MARKET_CAP).
8. Wrote `tests/test_m2_stage2k1r4b_pit_valuation_readiness.py` (23 tests).
9. Wrote acceptance + decision JSON + old-new diff + artifact manifest + artifact
   verification report.
10. Ran the verification gates (see Verification).

## Verification

- `pytest tests/test_m2_stage2k1r4b_artifact_and_sensitivity_audit.py tests/test_m2_stage2k1r4b_pit_valuation_readiness.py -q` → **60 passed**.
- Prior-stage scoring tests (R4A/R3/R2/2K.1R/2K/2J) → **140 passed**.
- Protected Stage 2F/2G/2H/2I tests → **132 passed**.
- Identity tests → **34 passed**.
- Sensitivity A/B → same `ledger_digest` and `scenarios`; `validate_sensitivity_ledger` → pass.
- Manifest verification A/B → pass, same digest.
- `pytest tests/ -q` (full suite) → **1243 passed, 2 warnings**.
- `ruff check src/ tests/` → All checks passed.
- `compileall` + import → OK.
- `git diff --check` → no whitespace errors (only a CRLF→LF warning, expected).
- Secret/path/pollution scan on new files → clean; no hardcoded absolute paths.
- Default DB hash `4a71d3c7…` (unchanged); 354 Fact baseline intact; stash + single
  worktree preserved; protected files untouched.
- Cross-directory portability → manifest verify from a different cwd with absolute
  paths → pass.

## Result

- Phase A-1/A-2: real artifact manifest verifier implemented; tampering detected;
  CLI exit codes 0/1/2 verified.
- Phase A-3: sensitivity v6 ledger with all six scenario classes; confidence
  scenarios counted; summary recomputable from the ledger; `validate_sensitivity_ledger`
  passes; NOT_STABLE preserved; tolerance 1.0.
- Phase B: PIT valuation readiness reviewed against the actual repo; decision
  `PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED`; route UNRESOLVED (recommendation
  MARKET_CAP); no valuation series built.
- Status: `completed` (CI-backed PASS).

## Remaining issues

- Historical PE/PB/PS PIT series is NOT implemented (by design this round).
- No production score, no peer acquisition, no M3.
- CI run `30907234491` PASS on ubuntu + windows (clean-clone jobs).

## Final files and Git state

- Branch: `feat/m2-value-assessment-mvp`; pushed to `origin`; CI run `30907234491`
  PASS on ubuntu + windows.
- New/modified files: `src/ashare_research/scoring/artifact_manifest.py` (new),
  `src/ashare_research/scoring/sensitivity.py` (v6), `src/ashare_research/tools/m2_stage2k1r3_closeout.py`,
  two test files, review doc, matrix JSON, decision JSON, old-new diff, v6 report,
  artifact manifest, artifact verification, acceptance, work record.
- Protected files untouched: AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB,
  stash.
- No force push, no reset --hard, no git clean.