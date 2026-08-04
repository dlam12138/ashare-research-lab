# Work record: M2 Stage 2K.1R scoring input lineage, confidence and sensitivity closeout

Status: `conditional` (local validation PASS; CI final gate pending on push authorization)

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `b974de94bc9747e6c6c6cfeb7f4904ded643b57e`
- Task source: `agent/goals/2026-08-04_m2_stage2k1r_scoring_input_lineage_confidence_sensitivity_closeout.md`
- Module: value assessment (scoring addendum) / engineering governance

## Objective

Replace the manual Stage 2K shadow-input JSON with a deterministic score-input
capsule builder reading only committed canonical artifacts, bind every component
to stable upstream IDs, validate the capsule, bind valuation percentiles to
observation sets, separate score/coverage/confidence, reassess the risk
dimension, complete sensitivity, and rebuild the non-production shadow/sensitivity
A/B from the capsule. No production scores, no overall score, no peer acquisition,
no M3.

## Verified opening state (snapshot)

- Branch `feat/m2-value-assessment-mvp`; HEAD == origin == `b974de94bc9747e6c6c6cfeb7f4904ded643b57e`.
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Stash: `stash@{0}` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` (Stage 1B.4 record edit).
- Unstaged protected edit (pre-existing Stage 2I.2R wording): `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md` hash `b0d739f2cce41b574e6db071e05fbc1233d38c2cb273a16723a5b0502db0bb30`.
- Untracked protected: `AGENTS.md` `9ff6d764...`, `agent/goals/` (hashes captured).
- `.codex/` does NOT exist locally (listed as protected but absent; noted, not created).
- Protected baseline: 354 Fact / 102 Metric Result / 16 definitions (verified by protected test suites).
- Stage 2J and Stage 2K artifacts present and unchanged.

## Scope

- Capsule builder + validator + confidence contract + reassessed risk dimension
  + completed sensitivity + rebuilt shadow/sensitivity A/B.
- Stage 2K.1R acceptance, agent record, manifests, capsule/confidence/sensitivity
  reports, old->new diff.
- Focused Stage 2K.1R tests; preserve Stage 2K acceptance as history.

## Non-goals

- No peer data acquisition, no production scores, no canonical value-profile
  modification, no overall score/ranking/recommendation/target price.
- No M3 implementation, main merge, PR/tag/release, force push, hard reset.
- No modification of default DB, protected baselines, protected local files, or
  the pre-existing Stage 2I.2R wording edit.
- No `codex/` creation.

## Implementation plan

1. Verify opening state (done); snapshot protected files.
2. Map canonical committed upstream artifacts for all 19 components.
3. Build the score-input capsule builder (deterministic, reads committed artifacts).
4. Build the capsule validator.
5. Bind valuation percentiles to observation sets.
6. Define the confidence contract and separate score/coverage/confidence.
7. Reassess the risk dimension (semantic decision).
8. Complete sensitivity with machine-derived stability.
9. Rebuild shadow/sensitivity A/B from the capsule.
10. Write acceptance, record, manifests, reports, old->new diff.
11. Write focused tests.
12. Run full validation + CI; final report; stop.

## Decision log

- **Input source**: Replace `config/value_dimension_scoring_shadow_inputs_v1.json`
  (hand-maintained) with `reports/petrochina_score_input_capsule_v1.json` built by
  `m2_stage2k1r_capsule.py`, reading only committed canonical artifacts.
  Rationale: eliminates manual drift and silent fallback; every value binds to
  upstream artifact SHA-256 + contract + record. Alternative considered: extending
  the existing shadow-inputs JSON — rejected because it lacked artifact lineage.
- **Risk dimension**: retain `risk_and_evidence_integrity` but emit separate
  `risk_veto_status` + `evidence_integrity`, no merged numeric score. Rationale:
  a merged risk score can mask a serious veto. Alternative: migrate to
  `risk_and_research_integrity` — rejected because it would change the protected
  four-dimension set and the Stage 2K registry, which is out of scope.
- **Stability**: `stability_tolerance=1.0` is frozen and was NOT relaxed. The
  sensitivity result is machine-derived `NOT_STABLE` (delta > 1.0 under ±25%
  weight perturbation, and the 0.95 coverage gate exceeds achieved coverage).
  Rationale: relaxing the tolerance to force a pass would be modifying thresholds
  to obtain an expected conclusion (forbidden by the agent agreement). This is the
  concrete basis for `SCORING_CONTRACT_GAPS_REMAIN`.
- **Transform sensitivity**: frozen-transform alternatives mutate the shared
  `stage2k._ABSOLUTE_BREAKPOINTS` global; each scenario now snapshots and restores
  the pristine breakpoints so later scenarios are never contaminated (determinism bug fixed).

## Actual operations

1. Verified opening state (HEAD, DB hash, stash, protected files) — snapshot at
   `tmp/stage2k1r/protected_snapshot.txt`; all protected artifacts intact.
2. Mapped committed canonical upstream artifacts (annual/earnings_quality/
   financial_safety/net_profit/roe_roa_denominators/capex_cash/dividend_realization
   fixtures, dividend events, repurchase scan, market-data snapshot registry,
   value profile, gap ledger).
3. Built `m2_stage2k1r_capsule.py` (24 components, deterministic, digest
   `dab07d9f1f6c04a7bc45cb55a703a57f07610e5e74cd742f94aa7885150301cb`).
4. Built `m2_stage2k1r_validate.py` (0 errors, 4 PIT findings for risk metrics
   available_at 2026-08-02 > score_date 2026-07-31).
5. Bound valuation percentiles to observation sets (scope ends at score_date;
   provider_digest + sample counts).
6. Defined `config/value_dimension_scoring_confidence_v1.json` and built
   `m2_stage2k1r_confidence.py` (all four dimensions medium).
7. Reassessed risk dimension: separate statuses, no merged score.
8. Built `m2_stage2k1r_sensitivity.py` (full frozen scenario set, deterministic);
   fixed the global-breakpoint mutation bug.
9. Rebuilt shadow A/B from capsule (`m2_stage2k1r_shadow.py`): matches Stage 2K
   exactly (73.47/12.17/70.13).
10. Wrote acceptance, artifact manifest, old→new diff, and emitted the four reports.
11. Wrote `tests/test_m2_stage2k1r_scoring_input_lineage.py` (24 tests).
12. Repaired a stale user-site-packages editable `.pth` that pointed
    `ashare_research` at a tmp clean-clone; pointed it back to `D:\量化分析\src`.

## Verification

- `python -m pytest tests/test_m2_stage2k1r_scoring_input_lineage.py` → 24 passed.
- `python -m pytest tests/` (full suite, with `data/` present) → **1102 passed**, 2 warnings, exit 0. Re-run confirmed after final source fixes.
- `python -m ruff check src/ashare_research/tools/m2_stage2k1r_*.py tests/test_m2_stage2k1r_scoring_input_lineage.py` → All checks passed.
- `python -m compileall -q src/ashare_research/tools/m2_stage2k1r_*.py` → OK.
- Shadow/sensitivity A/B vs Stage 2K: MATCH (73.47/12.17/70.13).
- Sensitivity deterministic across runs (diff empty).
- Reports deterministic after source fixes (shadow/confidence/sensitivity MATCH; capsule report differs only by LF/CRLF + trailing newline formatting).
- Default DB `data/research.duckdb` still matches baseline `4a71d3c7...`.
- Protected suites (official/identity/pit/baseline): 42 passed.
- Clean-clone portability: committed `4414df5`, cloned into a fresh checkout, `test_m2_stage2k1r_scoring_input_lineage.py` → 24 passed. The legacy `test_official_*.py` baseline tests fail in a clean clone (12 failed + 63 errors) because they need the gitignored `data/raw/*`; this failure set is **identical at the parent commit `b974de9`** (also 12 failed + 63 errors), so it is pre-existing and not introduced by this stage.
- CI (GitHub Actions `stage2g-reproducibility.yml`, ubuntu+windows) requires a push; not executed locally without user authorization.

## Result

- All 6 numbered Stage 2K.1R requirements implemented.
- Decision: `SCORING_CONTRACT_GAPS_REMAIN` — the frozen sensitivity is NOT_STABLE
  under the 1.0 tolerance (machine-derived), so the scoring contract is not yet
  production-trusted; peer acquisition is not yet allowed.
- Completed: capsule builder/validator, confidence separation, risk reassessment,
  complete sensitivity, shadow/sensitivity A/B, acceptance, artifact manifest (11
  files), old→new diff, ADR, and 24 tests (all passing).
- Local validation: PASS (pytest/ruff/compileall/A-B/determinism/artifact
  verification/protected suites). CI final gate pending on user authorization to push.

## Remaining (final gate)

- CI (GitHub Actions) is pending on a push; the user must authorize pushing to run
  the Ubuntu/Windows clean-clone CI. Do NOT start M3 or acquire peer data.

## Final files and Git state

- New (committed): `src/ashare_research/tools/m2_stage2k1r_{capsule,validate,confidence,shadow,sensitivity}.py`,
  `config/value_dimension_scoring_confidence_v1.json`,
  `tests/test_m2_stage2k1r_scoring_input_lineage.py`,
  `reports/petrochina_score_input_capsule_v1.json`,
  `reports/petrochina_dimension_scoring_shadow_v2.json`,
  `reports/petrochina_dimension_scoring_confidence_v1.json`,
  `reports/petrochina_dimension_scoring_sensitivity_v2.json`,
  `reports/m2_stage2k1r_artifact_manifest.json`,
  `reports/m2_stage2k1r_old_new_diff.md`,
  `acceptance/m2_stage2k1r_scoring_input_lineage_confidence_sensitivity_closeout.md`,
  `docs/decisions/ADR-2026-08-04-stage2k1r-scoring-contract-gaps-remain.md`,
  `agent/record/2026-08-04_Stage2K1R_scoring_input_lineage_confidence_sensitivity_closeout.md`.
- Commits: `4414df5` (feat) and `27bfed6` (docs: record validation). No push, no tag, no main merge.
- Protected files not staged/committed: the pre-existing Stage 2I.2R acceptance wording
  edit, `AGENTS.md`, `agent/goals/`; stash `cb568efd` and default DB `4a71d3c7...` unchanged.
- Branch: `feat/m2-value-assessment-mvp`. Working tree has only the protected
  `m2_stage2i2r` edit (M) and protected `AGENTS.md`/`agent/goals/` (untracked).