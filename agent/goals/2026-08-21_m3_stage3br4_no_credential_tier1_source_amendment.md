# Goal Contract: M3 Stage 3B-R4 — No-Credential Tier-1 Source Amendment & Acquisition

Status: IN_PROGRESS — PRE_OUTCOME_TIER1_SOURCE_AMENDMENT_AND_ACQUISITION

## Objective

Replace the blocked R3 oil transport with a no-credential, bounded FRED public CSV transport for
the unchanged EIA Brent economic variable, and formally amend the pre-outcome industry primary
control to the official CNI Oil & Gas Index (`399439`). Acquire only development-period data through
`2022-12-31`, normalize it deterministically, align it with the trusted R1 market proxy, and report
Tier-1 readiness without executing any PetroChina mechanism or outcome statistic.

## Frozen stage envelope

- Stage: `M3_STAGE3BR4`
- Type: `PRE_OUTCOME_TIER1_SOURCE_AMENDMENT_AND_ACQUISITION`
- Development end: `2022-12-31`
- Holdout start: `2023-01-01`; holdout: `SEALED`
- Real mechanism analysis: `PROHIBITED`
- Stage 3C implementation: `NOT YET AUTHORIZED`
- Stage 3C-A implementation: `NOT YET AUTHORIZED`

## Baseline

- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `8825c0e450dafa47f4b92bc4a3a83726c686b380`
- Remote synchronization at start: `0 ahead / 0 behind`
- Target worktree: `D:\量化分析-m3-stage3b`, clean
- Protected M2 worktree: `D:\量化分析`, dirty and untouched
- Protected stash: `stash@{0}`, untouched
- Default `data/research.duckdb`: absent in the target worktree
- R3 acceptance: `ACCEPTED`; R3 Goal/record governance status: to be synchronized to `CLOSED`

## Allowed scope

- R4 Goal, work record, source amendment, contracts, manifests, reports, acceptance, focused tests,
  bounded FRED/CNI transports, offline normalization/alignment/readiness, and factual R3 closeout.
- Minimal extension of the existing R3 CLI; no statistical pipeline.
- A single bounded network acquisition per source, with immutable raw bytes, hashes, and offline A/B
  reproducibility.

## Forbidden scope

- Any observation or artifact containing a date on or after `2023-01-01`.
- Any PetroChina mechanism/outcome statistic, regression, correlation, abnormal return, significance,
  sensitivity, chart, or quick sanity analysis.
- Modifying frozen Stage 3A, Stage 3B v1, Stage 3B-R1, Stage 3B-R2, or Stage 3B-R3 JSON artifacts.
- Treating CNI `399439` as identical to Shenwan `801016`/`801960`, or selecting it by outcome.
- Forward filling, fake zero returns, manual index splicing/rebasing, widening the oil stale gate, or
  substituting WTI, futures, ETFs, CSI/THS, or another industry proxy.
- Stage 3C/3C-A implementation, default DB writes, M2/stash/tag mutation, force-push, PR, or merge.

## Required behavior

- Oil economic variable remains Europe Brent Spot Price FOB, EIA `DCOILBRENTEU`; only distribution
  transport changes to FRED public graph CSV.
- FRED bounded proof inspects raw HTTP response bytes and rejects any `2023-` through `2026-` date.
- CNI identity is fixed pre-outcome: publisher Shenzhen Securities Information Co., Ltd. / CNI,
  code `399439`, 国证石油天然气指数 / CNI Oil & Gas Index, simple price-index return.
- CNI transport must be source-inspected and raw-byte bounded before development acquisition; an
  unbounded full-history response is rejected closed.
- R1 market proxy `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` is reused, not reacquired.
- Reports contain only provenance, coverage, hashes, gaps, readiness, and holdout/audit state.

## Required tests and validation

- Focused R4 synthetic transport/contract/holdout/frozen-hash/A-B/readiness tests.
- Existing Stage 3A/B/R1/R2/R3 boundary tests.
- `ruff check src/ tests/`; `python -m compileall -q src tests`; `git diff --check`; `pytest -q`.
- JSON parsing, restricted-output scan, no 2023+ content, no credentials, no default DB mutation, and
  protected-state checks.

## Acceptance criteria

- Oil is `M3_OIL_CONTROL_V3_TRUSTED` only if FRED identity, bounded raw response, normalization, and
  strictly-prior alignment all pass.
- Industry is `M3_CNI_OIL_GAS_INDUSTRY_CONTROL_V2_TRUSTED` only if official identity, bounded raw
  response, development coverage, and deterministic normalization pass; Shenwan remains deferred.
- Tier-1 is READY only when trusted market, oil, industry, and deterministic joint alignment exist.
- Holdout remains sealed and Stage 3C real analysis remains unauthorized.
- Final evidence independently records branch/HEAD, diff, tests, worktree/stash/remotes, frozen hashes,
  protected state, and any blockers; final verdict is `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

- Stop for North-Star review after R4 acceptance evidence and final validation.
- If either bounded transport is not proven or data is not trusted, report its exact fail-closed code;
  do not substitute another source or open a new stage automatically.

## Commit/push requirements

- Commit logical R4 changes on `feat/m3-mechanism-validation-mvp`.
- No direct push to `main`; no force-push, PR, merge, tag, or Stage 3C start.
