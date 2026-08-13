# Work record: M2 Stage 2K.1R4A — Scoring Engineering Decomposition and Guard Closeout

Status: `complete`

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `e54f5b3`
- Task source: user directive (M2 Stage 2K.1R4A — Scoring Engineering Decomposition and Guard Closeout)
- Module: value assessment (scoring engineering / governance)

## Verified opening state

- Branch `feat/m2-value-assessment-mvp`; HEAD `e54f5b3` == expected; ahead 0 / behind 0 vs origin.
- Remote: single `origin` (https://github.com/dlam12138/ashare-research-lab.git).
- Worktree: single (root).
- Stash: `stash@{0}` (Stage 1B.4 record edit) preserved.
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` (unchanged).
- 354 Fact baseline verified (`config/roic_canonical_fact_inventory_v2.json` fact_count=354); 102 Metric Result / 16 definitions baseline documented in prior acceptance.
- Acceptance present: Stage 2K, 2K.1R, 2K.1R2, 2K.1R3 (Stage 2J closeout recorded in goal doc).
- Report digests (LF-normalized sha256): capsule v3 `ff260e80...`, shadow v4 `73bec859...`, confidence v3 `62076710...`, sensitivity v4 `d9d8636b...`.
- Latest CI: run `30891692756` PASS on ubuntu + windows (and `30891126248` PASS).
- Protected local files all intact: `AGENTS.md`, `agent/goals/`, Stage 2I.2R pre-existing unstaged wording edit.
- Task list cleared (per user instruction "清空任务清单"); `agent/goals/` NOT touched.

## Objective

Small engineering closeout. Fix exactly five problems:

1. `m2_stage2k1r3_closeout.py` mixes business logic into a thick CLI.
2. `validate` / `verify-artifacts` failure can still return exit 0.
3. The validator recomputes from upstream but does not require the capsule's
   `resolved_records` audit snapshot to match upstream.
4. Risk status outputs `clear` when there is no trigger but still missing evidence.
5. Sensitivity v4 lost the coverage / confidence / transform / missing-ROIC scenarios
   present in v3.

## Non-goals (explicitly not fixed this round)

- Historical PE/PB/PS PIT denominator series: NOT built.
- Historical valuation percentile method: NOT changed, NOT trusted.
- `valuation_attractiveness` shadow: NON_PRODUCTION_AND_NOT_INTERPRETABLE.
- Peer data, production scoring, composite score, weights/thresholds, canonical
  value profile writes, M3: all NOT touched.
- Must NOT use a fixed denominator / close percentile / same percentile to stand
  in for PE/PB/PS.
- The `external-cache observation set` is a close-price observation set; the
  PE/PB/PS historical percentile gap is left to an independent Stage 2K.1R4B
  readiness review.

## STOP_HOOK_STATUS

`STOP_HOOK_STATUS=NOT_TRUSTED_EXTERNAL` (registered only; no `.codex/`,
`.claude/`, or `.git/hooks` touched).

## Implementation plan

1. Create work record (this file).
2. Split `m2_stage2k1r3_closeout.py` into `src/ashare_research/scoring/`
   modules: `capsule.py`, `validator.py`, `confidence.py`, `shadow.py`,
   `sensitivity.py`; keep the CLI module path `m2_stage2k1r3_closeout.py`.
3. Enforce CLI fail-closed exit codes (build 0, validate pass 0 / fail 1,
   verify pass 0 / fail 1, contract/param/exception 2, external cache missing 3).
4. Add capsule audit snapshot consistency (authoritative recomputation + audit
   snapshot comparison; `capsule_snapshot_mismatch`).
5. Fix risk status semantics (finite enum; no `clear`; `no_trigger_with_missing_evidence`).
6. Restore full sensitivity scenarios (6 scenario classes) from v3 baseline.
7. Write acceptance, manifests, old-new diff, tests.
8. Run verification order + CI + final report.

## Expected final business decision (preserve unless independently proven)

- Stage 2K: `SCORING_CONTRACT_GAPS_REMAIN`
- Sensitivity: `NOT_STABLE` (or recomputed from real scenarios)
- Peer benchmark: `NOT ALLOWED`
- Production scoring: `NOT ALLOWED`
- M3: `NOT STARTED`
- Next stage: `PIT_VALUATION_READINESS_REVIEW_ALLOWED` max

## Decision log

- **Module decomposition**: business logic moved into
  `ashare_research.scoring.{capsule,validator,confidence,shadow,sensitivity}`.
  `capsule.py` holds the shared helpers and constants (`_load`, `_sha256_bytes`,
  `_canonical`, path constants, `time_contract_identity`, `_record_dict`,
  `score_input_id_for`, `_make_score_input`, `build_capsule`, `capsule_digest`);
  the other modules import from it. No circular imports (deps: validator ->
  capsule; confidence -> capsule; shadow -> capsule; sensitivity -> shadow +
  capsule + confidence). Chosen so the CLI stays thin and there is a single
  source of truth for the capsule/score-input construction.
- **Audit snapshot consistency**: the validator recomputes the authoritative
  record set (`_record_dict(r)` for each re-resolved record) and compares it to
  the capsule's `resolved_records` snapshot; any difference is
  `capsule_snapshot_mismatch` in `snapshot_errors`. The R3 test
  `test_validator_ignores_capsule_record_snapshot` (which asserted the buggy
  behavior) was replaced by `test_validator_rejects_audit_snapshot_mismatch`.
- **Risk status enum**: replaced the `clear` branch with a finite enum
  (`blocked_by_risk_veto`, `no_trigger_observed_with_missing_evidence`,
  `no_trigger_observed_within_bounded_evidence`, `not_trusted`). `complete_absence_claim`
  is always False. PetroChina = `no_trigger_observed_with_missing_evidence`.
- **Sensitivity v5**: ported the 6 scenario classes from the Stage 2K.1R2
  sensitivity v3 baseline (weight perturbation, leave-one-component-out,
  coverage-threshold, frozen transform alternatives, confidence-threshold,
  missing-ROIC). Confidence is read from the executed confidence v3 report
  (or derived from capsule source tiers when not passed). The coverage and
  confidence gates remain independent. `_capsule_to_inputs` gained a
  `score_scenario == "synthetic_neutral"` branch so the ROIC scenario can
  inject a synthetic value without changing the default ROIC-gap behavior.
- **CLI exit codes**: `EXIT_OK=0`, `EXIT_CHECK_FAIL=1` (validate/verify fail),
  `EXIT_CONTRACT_ERROR=2` (bad args / missing config / internal exception),
  `EXIT_EXTERNAL_CACHE_MISSING=3` (real observation set without cache root).

## Actual operations

1. Verified opening state (branch `feat/m2-value-assessment-mvp`, HEAD `e54f5b3`,
   DB `4a71d3c7`, stash `cb568efd`, protected AGENTS.md / agent/goals/ /
   Stage 2I.2R edit intact; CI `30891692756` PASS).
2. Created work record (this file).
3. Split the R3 `m2_stage2k1r3_closeout.py` into `scoring/capsule.py`,
   `validator.py`, `confidence.py`, `shadow.py`, `sensitivity.py`; rewrote
   `tools/m2_stage2k1r3_closeout.py` as a thin CLI (~170 lines) with fail-closed
   exit codes.
4. Added Capsule Audit Snapshot Consistency to `validator.py`.
5. Fixed risk status semantics in `shadow.py` (finite enum, no `clear`).
6. Restored the full 6 sensitivity scenario classes in `sensitivity.py` (v5).
7. Updated `tests/test_m2_stage2k1r3_true_upstream_capsule.py` (module imports +
   snapshot-mismatch now fails) and `tests/stage2k1r3/test_composite_tamper.py`
   (audit-snapshot now fails closed).
8. Wrote `tests/test_m2_stage2k1r4a_engineering_closeout.py` (31 tests, A-F).
9. Generated reports: lineage-validation v2, shadow v5, sensitivity v5,
   old-new diff, artifact manifest.
10. Wrote acceptance file.
11. Ran verification gates (see Verification).

## Verification

- `pytest tests/ -q` → **1183 passed** (full suite; includes the 31 new R4A tests
  and the 22 R3 tests; real-cache observation-set tests run because the committed
  baostock snapshot is present).
- `pytest tests/test_m2_stage2k1r4a_engineering_closeout.py -q` → **31 passed**.
- `pytest tests/test_m2_stage2k1r3_true_upstream_capsule.py -q` → **22 passed**.
- `python tests/stage2k1r3/test_composite_tamper.py` → **ALL PASS** (baseline +
  tamper of inputs/value/source_tier/score_input_id/capsule_digest/removed
  component/gap count all fail closed; tampered resolved_records snapshot fails
  closed with `capsule_snapshot_mismatch`).
- `ruff check src/ tests/` → **All checks passed**.
- CLI exit codes: `validate` 0, `build-capsule` 0, `verify-artifacts` 0,
  `build-market-observation-set` (no cache) 3, `build-shadow` 0, `build-sensitivity` 0.
- `git diff --check` → clean.
- Reports: lineage v2 pass (authoritative pass, audit pass, 0 errors); shadow v5
  risk status `no_trigger_observed_with_missing_evidence`; sensitivity v5 all
  `NOT_STABLE` (EQ 9.11, VA 3.16, VRC 29.0 deltas), 6 scenario classes, gates
  separated. Report digests (LF-normalized sha256): lineage v2 `c262bc86...`,
  shadow v5 `6a2db9ff...`, sensitivity v5 `6dfb8ef9...`.

## Result

- All five Stage 2K.1R4A problems are fixed and verified.
- Business conclusion preserved: `NOT_STABLE`, `SCORING_CONTRACT_GAPS_REMAIN`,
  peer acquisition `NOT ALLOWED`, production scoring `NOT ALLOWED`, M3 `NOT STARTED`.
- No production score, no peer acquisition, no M3.

## Final files and Git state

- Branch: `feat/m2-value-assessment-mvp`.
- Commit `d506b9d` pushed to `origin/feat/m2-value-assessment-mvp`; CI run
  `30897901437` PASS on ubuntu + windows.
- New/modified files: `src/ashare_research/scoring/{capsule,validator,confidence,shadow,sensitivity}.py`,
  `src/ashare_research/tools/m2_stage2k1r3_closeout.py`, two test files,
  `tests/stage2k1r3/test_composite_tamper.py`, acceptance, work record, five
  reports.
- Protected files untouched: AGENTS.md, agent/goals/, Stage 2I.2R edit, default
  DB, stash.
- No force push, no reset --hard, no git clean.