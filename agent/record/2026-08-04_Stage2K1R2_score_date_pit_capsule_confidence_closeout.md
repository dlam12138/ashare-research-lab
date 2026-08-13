# Work record: M2 Stage 2K.1R2 — score-date PIT, capsule validation, percentile lineage and confidence-gate closeout

Status: `completed` — PASS (CI-backed; no production scores, no peer acquisition)

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `f00f85a3fec4b99ee29d66d5fd01159edefe3d3b`
- Task source: user directive (M2 Stage 2K.1R2 — Score-Date PIT, Capsule Validation, Percentile Lineage and Confidence-Gate Closeout)
- Module: value assessment (scoring addendum) / engineering governance

## Objective

Finite contract correction over Stage 2K.1R (not peer acquisition, not production
scoring). Fix the dual-clock PIT semantics, upstream capsule validation, percent
observation-set lineage, source-tier confidence, and confidence-gate sensitivity.
Preserve the honest `NOT_STABLE` / `SCORING_CONTRACT_GAPS_REMAIN` until the fixed
result independently proves otherwise. No peer acquisition, no production scoring,
no M3.

## Verified opening state (snapshot)

- Branch `feat/m2-value-assessment-mvp`; HEAD `f00f85a3fec4b99ee29d66d5fd01159edefe3d3b` == origin (ahead 0, behind 0).
- Intervening commits: `f00f85a` (docs 2K.1R CI PASS), `d3668a0`, `27bfed6`, `4414df5` (2K.1R feat), `b974de9`.
- Remotes: `origin` = `https://github.com/dlam12138/ashare-research-lab.git` (fetch+push).
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` (unchanged).
- Stash: `stash@{0}` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` (Stage 1B.4 record edit).
- Protected untracked: `AGENTS.md` SHA-256 `9ff6d76446348f54c845090ab56fbbc6a12e7a70425dff0cd79fbe75259a9ff7`; `agent/goals/`.
- Protected unstaged edit: `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md` (pre-existing wording edit).
- `.codex/` does NOT exist locally; `.claude/` and `.git/hooks/` are empty (no local Stop Hook file).
- Protected baseline 354 Fact / 102 Metric Result / 16 definitions verified by protected test suites.

## Known issues being addressed (from directive)

1. `score_date=2026-07-31` but risk evidence `available_at=2026-08-02`.
2. Validator treats future availability as a finding, not a failure.
3. Validator does not recompute artifact SHA-256 / record identity / value / unit / transform / score_input_id / capsule_digest.
4. Percentile inputs lack full observation-set identity.
5. Confidence contract registers source_tier but the engine does not execute it.
6. Confidence-threshold sensitivity actually mutates the coverage gate.
7. Stop Hook output does not pass JSON schema (no local `.codex/` hook file exists to fix).
8. `NOT_STABLE` / `SCORING_CONTRACT_GAPS_REMAIN` must be preserved unless the fixed result independently changes; no threshold relaxation.

## Scope

Sections 1–15 of the directive: dual-clock time contract, v2 capsule, upstream
resolver, fail-closed validator, percentile observation-set lineage, confidence
v2, confidence-gate sensitivity, Stop Hook documentation, rebuilt shadow/
confidence/sensitivity, acceptance, tests, validation gates, final report.

## Non-goals

- No peer data acquisition, no production scoring, no composite score/rank/
  recommendation/target price/position signal.
- No modification of the canonical value profile to write scores.
- No M3, no main merge, no PR/tag/release, no force push, no reset --hard, no git clean -fd.
- No modification of default DB, protected baselines, protected local files, or the
  pre-existing Stage 2I.2R wording edit. No stage of AGENTS.md / agent/goals/ / .codex/.
- No relaxing `stability_tolerance=1.0`; no adjusting scoring to force stability.

## Implementation plan

1. Freeze dual-clock time contract (`config/value_dimension_scoring_time_contract_v1.json` + doc).
2. Build v2 capsule (`m2_stage2k1r2_capsule.py` → `reports/petrochina_score_input_capsule_v2.json`).
3. Build upstream resolver (`m2_stage2k1r2_upstream.py`).
4. Rewrite fail-closed validator (v2 path).
5. Bind percentile observation-set lineage (contract + report).
6. Upgrade confidence v2 with executed source tiers.
7. Separate confidence-gate from coverage-gate sensitivity.
8. Document Stop Hook status (no local file to fix).
9. Rebuild shadow/confidence/sensitivity v3.
10. Write acceptance + old→new diff + manifest.
11. Write tests.
12. Run validation gates + CI + final report.

## Decision log

- **Dual-clock time contract**: freeze 4 explicit time points
  (`market_data_as_of_date=2026-07-31`, `research_evidence_as_of=2026-08-02`,
  `scorecard_formed_at=2026-08-02`, timezone Asia/Shanghai) replacing the single
  ambiguous `score_date` (kept as legacy). Rationale: a scorecard is a research
  snapshot formed at one point using market data as of an earlier cutoff and
  research evidence as of a later cutoff. Alternative: keep single `score_date`
  — rejected because it conflates market cutoff with formation time.
- **Fail-closed validator**: any validation error (not a mere finding) blocks
  the formal shadow scorecard. Future `available_at` / `trade_date` are errors,
  not findings. Rationale: time-contract rule 4. Alternative: keep the v1
  finding-only behavior — rejected because it allowed a future-dated scorecard.
- **Score-Input Capsule v2**: upgrade to typed `upstream_refs` (record_id +
  source_evidence_ids), Decimal string values, and canonical `score_input_id`
  (excludes paths/cwd/formatting; includes artifact SHA-256, records, source
  evidence, transform, value, unit, observation-set digest, time-contract
  digest). Rationale: bind identity to inputs, not to filesystem layout.
- **Percentile observation-set lineage**: bind every valuation percentile to the
  full observation set (`market_data_snapshot_registry.json`, provider baostock,
  sha256 `defd0b95...`, 1351 rows, PIT exclusion 0). Shared digest
  `3dcf1beef...` between capsule and percentile report. Rationale: remove
  unidentifiable percentile inputs.
- **Confidence v2**: execute the source-tier registry against each component's
  `source_tier` (not just document it). Dimension grade = weakest present grade,
  capped at medium when a coverage gap exists (a documented gap is not zero
  evidence). Rationale: fail-closed aggregation while avoiding spurious "low"
  for a single missing component.
- **Confidence-gate vs coverage-gate**: Stage 2K.1R bug (confidence-threshold
  scenario mutated `minimum_coverage_gate`) fixed. v3 sensitivity evaluates the
  executed confidence v2 grade against confidence thresholds independently of
  the coverage gate. Rationale: the two gates answer different questions.
- **Stop Hook**: `.codex/` absent, `.claude/` absent, `.git/hooks/` empty → no
  local repo file to fix. Documented as a hosting-environment concern; no
  `codex/` file created (protected).

## Actual operations

1. Verified opening state (HEAD `f00f85a` == origin, DB `4a71d3c7...` unchanged,
   stash `cb568efd` intact, protected files intact).
2. Created `agent/record/2026-08-04_Stage2K1R2_score_date_pit_capsule_confidence_closeout.md`.
3. Freeze `config/value_dimension_scoring_time_contract_v1.json` + doc
   `docs/value_dimension_scoring_time_contract_v1.md`.
4. Built `m2_stage2k1r2_capsule.py` (24 components, typed upstream refs, Decimal
   values, observation-set lineage, canonical `score_input_id`, capsule digest).
   Verified values match Stage 2K (ROE 0.1014, asset_liability 0.3637,
   cash_coverage 0.5833, payout 0.5468, PE 12.89).
5. Built `m2_stage2k1r2_validate.py` (fail-closed; recomputes artifact SHA-256,
   record identity, value/transform, unit/domain, score_input_id, capsule digest,
   PIT). Tamper test (eq_roe → 0.999) → 3 errors, fail.
6. Built `m2_stage2k1r2_upstream.py`; resolves all 24 components against
   committed artifacts → PASS.
7. Built percentile contract + `reports/petrochina_valuation_percentile_observation_sets_v1.json`
   (digest `3dcf1beef...` matches capsule).
8. Built `config/value_dimension_scoring_confidence_v2.json` +
   `m2_stage2k1r2_confidence.py` (executed source tiers; 4× medium).
9. Built `m2_stage2k1r2_sensitivity.py` (confidence-gate separated from
   coverage-gate; NOT_STABLE preserved).
10. Built `m2_stage2k1r2_shadow.py` (fail-closed v3; scores match Stage 2K).
11. Wrote acceptance, old→new diff, artifact manifest (19 files).
12. Wrote `tests/test_m2_stage2k1r2_pit_capsule_confidence.py` (28 tests).
13. Fixed ruff (73 → 0) via wrapping long lines and SIM102/B007/unit-diet fixes.

## Verification

- `python -m ashare_research.tools.m2_stage2k1r2_capsule build` → PASS.
- `python -m ashare_research.tools.m2_stage2k1r2_validate` → PASS (0 errors).
- Tamper fail-closed → FAIL (3 errors) as expected.
- `python -m ashare_research.tools.m2_stage2k1r2_upstream resolve` → PASS.
- `python -m ashare_research.tools.m2_stage2k1r2_confidence compute` → PASS (4× medium).
- `python -m ashare_research.tools.m2_stage2k1r2_shadow compute` → PASS (73.47/12.17/70.13).
- `python -m ashare_research.tools.m2_stage2k1r2_sensitivity compute` → PASS (NOT_STABLE).
- Determinism: capsule/shadow/confidence rebuilt in-memory twice → MATCH.
- Observation-set digest: capsule vs percentile report → MATCH (`3dcf1beef...`).
- `python -m pytest tests/test_m2_stage2k1r2_pit_capsule_confidence.py` → 28 passed.
- `python -m ruff check src/ashare_research/tools/m2_stage2k1r2_*.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py` → All checks passed.
- `python -m compileall -q src/ashare_research/tools/m2_stage2k1r2_*.py` → OK.
- `git diff --check` → clean.
- Full suite `python -m pytest tests/` → **1130 passed, 2 warnings** (exit 0).
- CI (GitHub Actions `stage2g-reproducibility.yml`, ubuntu+windows): run
  `30881433360` → **both matrix runners success** (ubuntu 2m22s, windows 4m17s).
  Only non-blocking Node.js deprecation annotations.

## Result

- All 15 Stage 2K.1R2 requirements implemented (Stop Hook documented as no-local-file).
- Decision: `SCORING_CONTRACT_GAPS_REMAIN` — frozen sensitivity is NOT_STABLE
  under the 1.0 tolerance; the scoring contract is not yet production-trusted;
  peer acquisition is not yet allowed.
- Fail-closed validator confirmed by tamper test.
- Confidence-gate and coverage-gate separated; NOT_STABLE preserved with no
  threshold relaxation.
- Validation: **PASS** — focused 28 tests, full suite 1130 passed, ruff clean,
  compileall OK, determinism MATCH, observation-set digest MATCH, and
  Ubuntu/Windows CI all success. Final gate satisfied.
- Pushed `feat/m2-value-assessment-mvp` to origin (`f00f85a..243d222`, 6 commits)
  to trigger CI; CI passed. No main merge, no tag, no force push, no release.

## Final files and Git state

- New (committed): `src/ashare_research/tools/m2_stage2k1r2_{capsule,validate,upstream,confidence,shadow,sensitivity}.py`,
  `config/value_dimension_scoring_time_contract_v1.json`,
  `config/value_dimension_scoring_percentile_contract_v1.json`,
  `config/value_dimension_scoring_confidence_v2.json`,
  `docs/value_dimension_scoring_time_contract_v1.md`,
  `reports/petrochina_score_input_capsule_v2.json`,
  `reports/petrochina_score_input_upstream_resolution_v1.json`,
  `reports/petrochina_valuation_percentile_observation_sets_v1.json`,
  `reports/petrochina_dimension_scoring_confidence_v2.json`,
  `reports/petrochina_dimension_scoring_shadow_v3.json`,
  `reports/petrochina_dimension_scoring_sensitivity_v3.json`,
  `reports/m2_stage2k1r2_old_new_diff.md`,
  `reports/m2_stage2k1r2_artifact_manifest.json`,
  `acceptance/m2_stage2k1r2_score_date_pit_capsule_confidence_closeout.md`,
  `tests/test_m2_stage2k1r2_pit_capsule_confidence.py`.
- Commits: `d764caf` (time contract + capsule + upstream), `db70641` (validator +
  percentile lineage), `556e12b` (confidence + sensitivity + shadow), `d743934`
  (acceptance docs), `f948105` (tests), `243d222` (final validation results).
  HEAD `243d222`; pushed to origin (`f00f85a..243d222`).
- Branch `feat/m2-value-assessment-mvp`. Working tree has only the protected
  `m2_stage2i2r` edit (M) and protected `AGENTS.md`/`agent/goals/` (untracked).
- Protected files (AGENTS.md, agent/goals/, pre-existing Stage 2I.2R edit, stash,
  default DB) untouched. No `codex/` created.