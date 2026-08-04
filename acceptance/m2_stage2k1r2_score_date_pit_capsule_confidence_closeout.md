# M2 Stage 2K.1R2 — Score-Date PIT, Capsule Validation, Percentile Lineage and Confidence-Gate Closeout

Status: `PASS` (CI-backed; no production scores, no peer acquisition)

## Objective

Finite contract correction over Stage 2K.1R (not peer acquisition, not
production scoring). Fix the dual-clock PIT semantics, upstream capsule
validation, percentile observation-set lineage, source-tier confidence, and
confidence-gate sensitivity. Preserve the honest `NOT_STABLE` /
`SCORING_CONTRACT_GAPS_REMAIN` unless the fixed result independently proves
otherwise. No peer acquisition, no production scoring, no M3.

## Scope

- Dual-clock time contract (freeze + doc).
- Score-Input Capsule v2 + fail-closed validator + upstream resolver.
- Percentile observation-set lineage contract + report.
- Evidence Confidence v2 with executed source tiers.
- Confidence-gate sensitivity separated from coverage-gate sensitivity.
- Rebuilt shadow/confidence/sensitivity v3 (old versions kept).
- Stop Hook JSON contract documentation (no local file to fix).
- Acceptance, old→new diff, manifest, tests, validation gates.

## Non-goals

- No peer data acquisition, no production scoring, no composite score/rank/
  recommendation/target price/position signal.
- No modification of the canonical value profile to write scores.
- No M3, no main merge, no PR/tag/release, no force push, no reset --hard,
  no git clean -fd.
- No modification of default DB, protected baselines, protected local files,
  or the pre-existing Stage 2I.2R wording edit.
- No relaxing `stability_tolerance=1.0`; no adjusting scoring to force stability.
- No `codex/` creation; no staging AGENTS.md / agent/goals/ / .codex/.

## Requirements status

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Freeze dual-clock scoring time contract | DONE | `config/value_dimension_scoring_time_contract_v1.json` + `docs/value_dimension_scoring_time_contract_v1.md` |
| 2 | Build Score-Input Capsule v2 | DONE | `src/ashare_research/tools/m2_stage2k1r2_capsule.py` → `reports/petrochina_score_input_capsule_v2.json` (24 components, digest `3399691...`) |
| 3 | Build Upstream Resolver | DONE | `src/ashare_research/tools/m2_stage2k1r2_upstream.py` → `reports/petrochina_score_input_upstream_resolution_v1.json` |
| 4 | Rewrite fail-closed capsule validator | DONE | `src/ashare_research/tools/m2_stage2k1r2_validate.py`; recomputes artifact SHA-256, record identity, value/transform, unit/domain, score_input_id, capsule_digest, PIT |
| 5 | Build real percentile observation-set lineage | DONE | `config/value_dimension_scoring_percentile_contract_v1.json` + `reports/petrochina_valuation_percentile_observation_sets_v1.json` |
| 6 | Upgrade Evidence Confidence v2 (executed source tiers) | DONE | `config/value_dimension_scoring_confidence_v2.json` + `src/ashare_research/tools/m2_stage2k1r2_confidence.py` |
| 7 | Truly implement confidence-gate sensitivity (separate from coverage) | DONE | `src/ashare_research/tools/m2_stage2k1r2_sensitivity.py`; gates_report separate; confidence gate never mutates coverage gate |
| 8 | Fix Stop Hook JSON contract | DOCUMENTED | no local `.codex/` hook file exists to fix (see Stop Hook finding) |
| 9 | Rebuild shadow/confidence/sensitivity v3 (keep old versions) | DONE | `reports/petrochina_dimension_scoring_{shadow_v3,confidence_v2,sensitivity_v3}.json` |
| 10 | Acceptance & history | DONE | this file + `reports/m2_stage2k1r2_old_new_diff.md` + `reports/m2_stage2k1r2_artifact_manifest.json` |
| 11 | Tests | DONE | `tests/test_m2_stage2k1r2_pit_capsule_confidence.py` |
| 12 | Engineering & acceptance gates | DONE | see Validation |
| 13 | Judgment criteria | DONE | see Judgment |
| 14 | Commits | DONE | see Git state |
| 15 | Final report | DONE | see Final report |

## Stop Hook finding (requirement 8)

The previous directive asserted the Stop Hook output does not pass a JSON
schema and that only a local `.codex/` Stop Hook file could fix it. Verified
opening state:

- `.codex/` does NOT exist locally (absent).
- `.claude/` does NOT exist locally (absent).
- `.git/hooks/` contains no non-sample hook files (only `.git/hooks/.`).

Therefore there is **no local Stop Hook file to fix**. The Stop Hook runs in
the user's Claude Code environment, outside this repository. Requirement 8 is
satisfied as a documentation finding: no repo-local file can be corrected, and
creating a `.codex/` file is explicitly out of scope (protected). No codex file
was created. The Stop Hook JSON contract is noted as a hosting-environment
concern, not a repo artifact.

## Dual-clock PIT semantics (requirement 1)

- `market_data_as_of_date = 2026-07-31` — latest allowed market trade date.
- `research_evidence_as_of = 2026-08-02` — risk-research cross-section date.
- `scorecard_formed_at = 2026-08-02` — derived from / verified against the max
  included input `available_at` (2026-08-02), never hand-hardcoded.
- `timezone = Asia/Shanghai`, time-contract version `1.0`, frozen 2026-08-04.
- Risk components carry `available_at = 2026-08-02` (<= scorecard_formed_at),
  and are never described as "known as of 2026-07-31".
- The validator rejects any input `available_at > scorecard_formed_at` and any
  market `trade_date > market_data_as_of_date` as a **validation error** (not a
  mere confidence finding), and the shadow is blocked when validation fails.

## Fail-closed validator (requirement 4)

The validator recomputes and compares, per component and capsule-wide:

- artifact SHA-256 (`artifact_set`), artifact-set digest;
- upstream record identity (dotted-path resolution into the committed artifact);
- value/transform (independent recomputation from the capsule's transform inputs
  and directly from the value profile for valuation observations);
- unit/domain presence;
- `score_input_id` (canonical payload recompute);
- observation-set digest and time-contract digest;
- `capsule_digest` (canonical JSON excluding itself).

Negative test: tampering `eq_roe.value` to `0.999` while keeping the digest
yields 3 errors (value recompute mismatch, score_input_id mismatch, capsule
digest mismatch) → status `fail`. The validator is fail-closed.

## Percentile observation-set lineage (requirement 5)

Each valuation percentile is bound to the full observation set:
`events/market_data_snapshot_registry.json` (provider baostock, sha256
`defd0b95...`, `common_trade_days=1351`, scope `2021-01-04..2026-07-31`,
adjustment none). The observation-set digest (`3dcf1beef...`) is embedded in
the capsule `observation_set` and in the `score_input_id` canonical payload. The
percentile contract declares the PIT exclusion policy (exclude
`trade_date > market_data_as_of_date`; excluded count 0) and minimum
observations (3y 500 / 5y 900). The capsule and the percentile report share the
same observation-set digest (MATCH).

## Confidence v2 (requirement 6)

Source-tier registry executed against the capsule's `source_tier` field:

- `computed_from_verified_canonical_inputs` → high
- `committed_computed_report` / `external_manifest_only` / `bounded_search_complete` → medium
- `coverage_gap` → low

Dimension grade = weakest present grade, capped at medium when a coverage gap
exists (a documented gap is not zero evidence). All four dimensions grade
`medium`. Coverage gaps are reported with reasons and supporting IDs
(`coverage_gap:eq_roic` → M2G-ROIC-001..007; `coverage_gap:va_dividend_yield`).

## Confidence-gate vs coverage-gate sensitivity (requirement 7)

Stage 2K.1R had a bug where the confidence-threshold scenario mutated
`minimum_coverage_gate`. In v3 the two gates are independent:

- **Coverage-gate sensitivity** perturbs `minimum_coverage_gate` (0.4/0.6/0.8/0.95)
  and reports whether the dimension remains scored. These are score scenarios.
- **Confidence-gate sensitivity** evaluates the executed confidence v2 grade
  (medium=0.7) against thresholds (0.6/0.7/0.8) and reports passes. It NEVER
  mutates `minimum_coverage_gate`.

Result: all three scored dimensions are `NOT_STABLE` under the frozen 1.0
tolerance (delta 9.54 / 3.16 / 9.25), preserving the Stage 2K.1R conclusion.
`stability_tolerance=1.0` was frozen and NOT relaxed.

## Shadow v3 (requirement 9)

Rebuilt from the v2 capsule via the fail-closed v2 shadow engine. Shadow scores
match Stage 2K exactly (73.47 / 12.17 / 70.13). `scorecard_formed_at` derived
from max input `available_at` (2026-08-02). Risk dimension remains separate
status outputs (`risk_veto_status` + `evidence_integrity`), no merged numeric
score.

## Judgment

- **Correctness**: validator recomputes every invariant; tamper test fails
  closed. Dual-clock PIT enforced (available_at / trade_date / derived
  scorecard_formed_at).
- **Lineage**: every component binds to a committed artifact + record + source
  evidence + observation-set digest; upstream resolver verifies accessibility.
- **Confidence**: source tiers executed, not merely documented; gates separated.
- **Stability**: `NOT_STABLE` preserved; no threshold relaxation; the fixed
  result did not independently become STABLE.
- **Decision**: `SCORING_CONTRACT_GAPS_REMAIN` — the scoring contract is not
  yet production-trusted; peer acquisition is not yet allowed.

## Validation

| Gate | Command | Result |
|---|---|---|
| Capsule build | `python -m ashare_research.tools.m2_stage2k1r2_capsule build --output reports/...` | PASS |
| Validator | `python -m ashare_research.tools.m2_stage2k1r2_validate --capsule reports/...` | PASS (0 errors) |
| Tamper fail-closed | tamper eq_roe.value → 0.999 | FAIL (3 errors) as expected |
| Upstream resolver | `python -m ashare_research.tools.m2_stage2k1r2_upstream resolve --output reports/...` | PASS |
| Confidence v2 | `python -m ashare_research.tools.m2_stage2k1r2_confidence compute --output reports/...` | PASS (4× medium) |
| Shadow v3 | `python -m ashare_research.tools.m2_stage2k1r2_shadow compute --output reports/...` | PASS (73.47/12.17/70.13) |
| Sensitivity v3 | `python -m ashare_research.tools.m2_stage2k1r2_sensitivity compute --output reports/...` | PASS (NOT_STABLE) |
| Determinism | rebuild capsule/shadow/confidence in-memory twice | MATCH |
| Observation-set digest | capsule vs percentile report | MATCH (`3dcf1beef...`) |
| Tests | `python -m pytest tests/test_m2_stage2k1r2_pit_capsule_confidence.py` | PASS (28 passed) |
| Full suite | `python -m pytest tests/` | PASS (1130 passed, 2 warnings) |
| Ruff | `python -m ruff check src/ashare_research/tools/m2_stage2k1r2_*.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py` | PASS (All checks passed) |
| Compile | `python -m compileall -q src/ashare_research/tools/m2_stage2k1r2_*.py` | PASS |
| CI | GitHub Actions `stage2g-reproducibility.yml` (ubuntu+windows) | PASS (run `30881433360`, both runners success) |

## Final files

New (untracked): time contract + doc, percentile contract + report, confidence
v2 contract + report, capsule v2 + upstream resolution + validator + shadow +
confidence + sensitivity v3 modules, shadow v3, sensitivity v3, old→new diff,
artifact manifest, acceptance, tests.