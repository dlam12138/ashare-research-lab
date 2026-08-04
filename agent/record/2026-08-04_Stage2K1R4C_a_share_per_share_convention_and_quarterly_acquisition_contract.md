# Work record: M2 Stage 2K.1R4C — A-Share Per-Share Valuation Convention and Quarterly Denominator Acquisition Contract

Status: `in_progress`

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `15c8e28`
- Task source: user directive (M2 Stage 2K.1R4C — A股每股估值口径冻结与季度分母采集合同)
- Module: value assessment (governance closeout + valuation per-share convention + quarterly denominator acquisition contract)

## Verified opening state

- Branch `feat/m2-value-assessment-mvp`; HEAD `15c8e28`; local == origin (ahead 0 / behind 0).
- Protected local files intact and untouched: `AGENTS.md` (`??`), `agent/goals/` (`??`), pre-existing Stage 2I.2R unstaged wording edit (`acceptance/m2_stage2i2r_...md` is `M`).
- Stash `stash@{0}` preserved (Stage 1B.4 record edit).
- R4B closed: `Status: in_progress` at top of `agent/record/2026-08-04_Stage2K1R4B_...md` (conflict to fix — Phase A1).
- R4B CI run `30907749043` PASS on ubuntu + windows.
- Protected baselines: default DB SHA-256 `4a71d3c7…`; 354 Fact baseline; sensitivity v6 ledger `213cdba0…`; manifest chain.

## Task objective

A single, small, complete governance stage (not a micro-patch, not a large quarterly
collection). Three things:

1. **Phase A**: fix two small non-blocking issues — (A1) the R4B work-record status
   conflict (`in_progress` at top vs `completed` at bottom); (A2) tighten the sensitivity
   ledger validator to compare the full per-dimension summary (incl. both gate blocks and
   `production_readiness_reason`) via a single shared recompute function.
2. **Phase B**: freeze the A-share per-share valuation convention
   (`A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION`), correcting the R4B misjudgment that
   treated the missing A/H split as a per-share blocker; supersede the R4B route fields
   without erasing history.
3. **Phase C**: freeze the quarterly denominator fact-acquisition contract
   (scope, official sources, time contract). No collection, no series, no scoring expansion.

## Scope

- `agent/record/2026-08-04_Stage2K1R4B_...md` (top status header only)
- `src/ashare_research/scoring/sensitivity.py` (shared recompute function + validator)
- `docs/pit_valuation_denominator_readiness_review.md` (supersession note)
- `reports/pit_valuation_denominator_readiness_matrix.json` (route supersession)
- `reports/m2_stage2k1r4b_decision.json` (route supersession + block adjustments)
- `tests/test_m2_stage2k1r4b_pit_valuation_readiness.py` (route-supersession assertion)
- New: `docs/decisions/ADR-VALUATION-002-a-share-per-share-convention.md`
- New: `config/pit_valuation_fact_acquisition_plan_v1.json`
- New: `docs/pit_valuation_fact_acquisition_contract.md`
- New: `reports/pit_valuation_fact_acquisition_coverage_matrix.json`
- New: `reports/m2_stage2k1r4c_decision.json`
- New: `reports/petrochina_dimension_scoring_sensitivity_v6.json` (regenerated, unchanged digest)
- New: `tests/test_m2_stage2k1r4c_a_share_per_share_convention.py`
- New: `acceptance/m2_stage2k1r4c_a_share_per_share_convention_and_quarterly_acquisition_contract.md`
- New: this work record

## Non-goals

- Do NOT start quarterly fact collection/polling/injection.
- Do NOT build historical PE/PB/PS series, valuation percentiles, or update `valuation_attractiveness` shadow.
- Do NOT modify scoring weights, thresholds, or valuation results.
- Do NOT relax `stability_tolerance=1.0`; do NOT change the `NOT_STABLE` conclusion.
- Do NOT acquire peers; do NOT start M3.
- Do NOT modify `market_observation_set.py` business semantics.
- Do NOT modify the default DB, protected baselines, protected local files, or the pre-existing Stage 2I.2R edit.
- Do NOT create `.codex/`, `.claude/`, or git hooks.
- Do NOT stage/modify/rollback/clean protected files.

## Implementation plan

1. (this record) record opening state.
2. Phase A1: fix R4B work-record status header.
3. Phase A2: extract `recompute_dimension_summary_from_ledger`; wire both build and
   validate to it; validator compares the full summary; add tamper tests.
4. Phase B: write ADR-002; supersede R4B review/matrix/decision; update R4B route test.
5. Phase C: write acquisition plan + contract + coverage matrix.
6. Phase D: R4C decision JSON; write acceptance tests; regenerate sensitivity v6 report.
7. Acceptance doc.
8. Run full verification order; final report.

## Actual operations

Recorded as executed:

1. Verified opening state (branch `feat/m2-value-assessment-mvp`, HEAD `15c8e28`,
   local == origin; protected AGENTS.md / agent/goals/ / Stage 2I.2R edit intact;
   DB `4a71d3c7…`; R4B CI `30907749043` PASS).
2. Created work record (this file).
3. Phase A1: fixed the R4B work-record status header (`Status: in_progress` →
   `Status: completed` + `Closeout verdict: PASS` + `Final head: 15c8e28` +
   `Final CI: 30907749043`). Confirmed no `in_progress` remains; historical
   starting-state text (`85e1390`) preserved.
4. Phase A2: added `_confidence_grade_from_ledger` (recovers the executed confidence
   grade from the ledger's confidence-threshold scenarios) and
   `recompute_dimension_summary_from_ledger` (single shared pure function returning the
   FULL summary incl. gate blocks + production_readiness_reason). Wired both
   `build_sensitivity_v6` and `validate_sensitivity_ledger` to it. The validator now
   compares every summary field (no hand-written whitelist). Confirmed digest unchanged
   (`213cdba0…`), validator pass, and all 5 tamper cases fail even when the digest is
   recomputed.
5. Phase B: wrote `docs/decisions/ADR-VALUATION-002-a-share-per-share-convention.md`
   (`A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION`, status accepted). Superseded the R4B
   route fields in `reports/pit_valuation_denominator_readiness_matrix.json` and
   `reports/m2_stage2k1r4b_decision.json` (effective `route = A_SHARE_PRICE_PER_SHARE`,
   `route_status = FROZEN`, `core_market = SSE_A_SHARE`, `a_h_split_required = false`,
   `total_ordinary_share_timeline_required = true`; historical `UNRESOLVED`/`MARKET_CAP`
   preserved in a `route_superseded_by` block). Updated the review doc with a supersession
   banner. Updated the R4B route test to assert the supersession. R4B decision
   `PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED` unchanged.
6. Phase C: wrote `config/pit_valuation_fact_acquisition_plan_v1.json`,
   `docs/pit_valuation_fact_acquisition_contract.md`, and
   `reports/pit_valuation_fact_acquisition_coverage_matrix.json` (plan only; no
   collection).
7. Phase D: wrote `reports/m2_stage2k1r4c_decision.json`
   (`A_SHARE_CONVENTION_FROZEN_ACQUISITION_ALLOWED`). Regenerated the sensitivity v6
   report (byte-identical, digest `213cdba0…`). Wrote
   `tests/test_m2_stage2k1r4c_a_share_per_share_convention.py` (33 + 1 manifest test).
8. Added an R4C artifact manifest (`reports/m2_stage2k1r4c_artifact_manifest.json`,
   14 files) and pointed the CLI `DEFAULT_MANIFEST` at it; added
   `m2_stage2k1r4c_artifact_manifest_v1` to the allowed schemas. This keeps the R4A
   `test_cli_verify_artifacts_pass_exit_0` passing (the R4B manifest was stale because
   R4C modified its files).
9. Wrote the acceptance doc.
10. Ran the verification gates (see Verification).

## Verification

- `pytest tests/test_m2_stage2k1r4c_a_share_per_share_convention.py -q` → **34 passed**.
- R4A/R4B/R4C test files → **124 passed** (incl. the previously-failing R4A
  `test_cli_verify_artifacts_pass_exit_0`).
- Full suite `pytest tests/ -q` → **1277 passed, 2 warnings** (up from 1243 in R4B;
  +34 R4C tests).
- `ruff check src/ tests/` → All checks passed.
- `compileall` + import → OK.
- `git diff --check` → no whitespace errors (only CRLF→LF warnings, expected).
- R4C manifest verify → pass (14 files, digest `bf9f50a2…`; regenerated after the final
  test-file edit — the first full-suite run caught that the manifest was stale for the
  R4C test file, which was fixed by regeneration).
- Sensitivity v6 report regenerated byte-identical (no git diff); digest `213cdba0…`.
- Default DB hash `4a71d3c7…` unchanged; protected files intact; stash preserved.

## Result

- Phase A1: R4B record status conflict fixed.
- Phase A2: sensitivity validator now compares the full summary via a single shared
  recompute function; all tamper cases fail; scenarios/thresholds/NOT_STABLE unchanged.
- Phase B: A-share per-share convention frozen (ADR-002); R4B route superseded without
  erasure; R4B overall decision unchanged.
- Phase C: quarterly acquisition contract frozen (plan only, no collection).
- Phase D: decision `A_SHARE_CONVENTION_FROZEN_ACQUISITION_ALLOWED`.
- Status: `completed` (CI-backed PASS).

## Remaining issues

- Historical PE/PB/PS PIT series is NOT implemented (by design this round).
- No production score, no peer acquisition, no M3.
- Next stage: Stage 2K.1R4D official quarterly denominator fact collection.

## Final files and Git state

- Branch: `feat/m2-value-assessment-mvp`; pushed to `origin`; CI run PASS on ubuntu + windows.
- New/modified files: R4B record (status only), `sensitivity.py`, `artifact_manifest.py`,
  `m2_stage2k1r3_closeout.py`, R4B matrix/decision/review-doc/test, ADR-002, acquisition
  plan/contract/coverage matrix, R4C decision, R4C artifact manifest, R4C test, acceptance,
  work record.
- Protected files untouched: AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB, stash.
- No force push, no reset --hard, no git clean.