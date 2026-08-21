# Goal Contract: M3 Stage 3B-R3 — Tier-1 Acquisition Unblock & Data Closeout

Status: CLOSED — USER-INPUT/SOURCE-GAP ACCEPTANCE

R3 final HEAD: `8825c0e450dafa47f4b92bc4a3a83726c686b380`
R3 final CI: `31880528110` PASS

## Frozen stage envelope

- Stage: `M3_STAGE3BR3`
- Type: `PRE_OUTCOME_DATA_ACQUISITION_UNBLOCK`
- Market proxy contract: `FROZEN`
- Oil timing contract v2: `FROZEN`
- Industry regime contract: `FROZEN`
- Development: `<= 2022-12-31` only
- Holdout `>= 2023-01-01`: `SEALED`
- Stage 3C real analysis: `NOT AUTHORIZED`
- Stage 3B-R2 final-tip CI must PASS before Stage 3B-R3 work begins.

## Baseline

- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `2042e44` (full `2042e44e6d571e968febeb6389d93141bea389e9`)
- Working tree: isolated M3 worktree `D:\量化分析-m3-stage3b`, clean
- Original M2 worktree: protected, `feat/m2-value-assessment-mvp` at `241c180`, dirty, unused
- Protected stash: `stash@{0}` (Stage 1B.4 record edit), untouched
- Default `data/research.duckdb`: absent in the isolated worktree
- Stage 3B-R2 final-tip CI `31877910646`: `completed`/`success`; Windows clean-clone = success,
  Ubuntu clean-clone = success, identity-compare = success. **GATE PASS.**
- Stage 3A / Stage 3B v1 / Stage 3B-R1 frozen artifacts: SHA-256 verified unchanged.
- Market proxy v2 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`: TRUSTED where the 0.99 gate passes
  (2015-03-16 → 2022-12-30, 1,902 OK / 68 gap).

## Objective

This stage unblocks the two Tier-1 development inputs (`oil`, `petrochemical_industry`) that
Stage 3B-R2 confirmed were not obtainable through a bounded, holdout-safe path, and re-computes the
joint Tier-1 readiness. It is **DATA TRANSPORT + PROVENANCE + NORMALIZATION + READINESS** — not a new
research contract, not a new proxy/control design, not model implementation, and not real analysis.
If a source still cannot be acquired without reading 2023+ in this environment, report the precise
code and the exact unblock condition; never substitute a non-frozen proxy and never read the holdout.

## Scope

- Fix the Stage 3B-R2 Goal/work-record governance status drift (ACCEPTED vs IN_PROGRESS) to CLOSED.
- Add the Stage 3B-R3 goal, work record, source-resolution, oil/industry development manifests,
  data coverage, tier-1 readiness v2, joint input manifest, acceptance, and focused tests.
- Add a bounded EIA Open Data API v2 transport (`acquisition_eia.py`) with secret-from-environment
  handling, official route discovery, response validation, and fail-closed codes.
- Add a Shenwan official-source-resolution ladder (`acquisition_shenwan.py`): Route A (official
  bounded transport), Route B (existing development-only official capsule), Route C (manual official
  development capsule), Route D (same-series third-party transport, last resort).
- Add a Stage 3B-R3 acquisition CLI reusing the tested R2 normalize/align/readiness logic.
- Commit and normally push logical commits to `feat/m3-mechanism-validation-mvp`.

## Forbidden scope

- Modify any Stage 3A / Stage 3B v1 / Stage 3B-R1 / Stage 3B-R2 frozen artifact (JSON reports stay
  byte-identical). The only historical markdown edits allowed are the R2 Goal status, the R2
  work-record status/final-CI closeout, and README factual status.
- Read, acquire, parse, summarize, or analyze any date 2023-01-01 or later.
- `download full history then filter to 2022` for any source.
- Substitute WTI / Brent futures / Shanghai crude / BZ=F / commodity ETF for the frozen Brent control.
- Substitute an industry ETF / CSI energy / THS sector / current-classification backfill for the
  frozen Shenwan industry control.
- Any mechanism inference listed in the execution instruction (crash-day, correlation, abnormal
  return, regression, gamma, p-value, CI, bootstrap, effect size, FDR, evidence level, index offset).
- Write the default DB; commit raw secrets or raw/large data; create a PR; merge main; force-push;
  alter protected M2 state, stash, tags, branches, or artifacts.

## Secret handling (hard rules)

- API key is read only from the process environment via `os.environ.get("EIA_API_KEY")`.
- Never write the key to source, `.env`, Goal, work record, acceptance, manifest, test snapshot, or
  any log; never echo it in a shell; never place it in argv; never save a key hash.
- HTTP requests are constructed in Python; every exception/debug output passes through secret
  redaction. Manifests store only `auth_method = ENVIRONMENT_API_KEY`,
  `api_key_present = bool`, `endpoint_template = REDACTED`.

## Upstream constraints

- FRED `DCOILBRENTEU` is an `OPTIONAL_SECONDARY_DISTRIBUTION_CROSSCHECK` (its underlying source is
  EIA), not a primary acquisition gate. If EIA official bounded acquisition + identity + coverage +
  deterministic normalization all pass, oil can be TRUSTED without FRED; FRED unreachability is
  `FRED_CROSSCHECK_UNAVAILABLE_NON_BLOCKING`.
- Do not re-run the same unbounded SWS trend endpoint expecting a different result. Resolve the
  industry source through the ladder defined above; a bounded path or a verified development-only
  immutable capsule is required.

## Required reports

- `reports/m3_stage3br3_source_resolution_v1.json`
- `reports/m3_stage3br3_oil_development_manifest_v1.json`
- `reports/m3_stage3br3_industry_development_manifest_v1.json`
- `reports/m3_stage3br3_data_coverage_v1.json`
- `reports/m3_stage3br3_tier1_readiness_v2.json`
- `reports/m3_stage3br3_joint_input_manifest_v1.json`

## Required tests

- Secret redaction: API key absent => precise fail-closed code; key never appears in logs,
  exceptions, reports, manifests, or snapshots; redacted endpoint is stable.
- Bounded acquisition: EIA request requires explicit end <= 2022-12-31; missing end rejected;
  end >= 2023 rejected; wrong series identity rejected; wrong units rejected; duplicate date
  rejected; malformed numeric rejected; FRED absence non-blocking when EIA authoritative path is
  trusted.
- Industry ladder: known unbounded SWS endpoint remains rejected; AKShare full-history-then-filter
  rejected; official development capsule accepted; unproven mirror rejected; cross-taxonomy return
  rejected.
- Stage 3A / Stage 3B v1 / Stage 3B-R1 / Stage 3B-R2 frozen SHA unchanged; no restricted outputs;
  real input manifest cannot contain 2023+.

## Stop conditions

- Stop for North-Star review after final-tip CI evidence; do not begin Stage 3C and do not begin
  Stage 3C-A.
- If oil or industry cannot be made TRUSTED, report the precise gap code(s) and the exact unblock
  condition; never substitute a non-frozen proxy or read the holdout to force a PASS.
