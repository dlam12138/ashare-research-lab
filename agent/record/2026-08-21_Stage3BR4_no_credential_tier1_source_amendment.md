# Work Record: M3 Stage 3B-R4 — No-Credential Tier-1 Source Amendment & Acquisition

Status: CONDITIONAL_PASS — PRE_OUTCOME_TIER1_SOURCE_AMENDMENT_AND_ACQUISITION; STOP_FOR_NORTH_STAR_REVIEW

## Basic information

- Date: 2026-08-21
- Agent: Codex
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `8825c0e450dafa47f4b92bc4a3a83726c686b380`
- Task source: user-provided M3 Stage 3B-R4 execution instruction
- Module: mechanism validation / Tier-1 source amendment and acquisition
- Goal contract: `agent/goals/2026-08-21_m3_stage3br4_no_credential_tier1_source_amendment.md`

## Objective

Use no-credential bounded FRED public CSV transport for the unchanged EIA Brent economic variable;
formally amend the pre-outcome industry control to official CNI `399439`; acquire only development
data, normalize/alignment-test it, and determine Tier-1 readiness. No PetroChina mechanism analysis
and no Stage 3C/3C-A implementation are authorized.

## Scope and non-goals

Allowed: R4 contracts/reports/acceptance/tests/work record, minimal bounded FRED and CNI adapters,
offline A/B normalization/alignment/readiness, and factual R3 governance closeout.

Forbidden: frozen JSON mutation; any 2023+ read/write; full-history-then-filter; outcome-driven source
choice; statistical analysis; proxy reacquisition; default DB/M2/stash mutation; PR/merge/force-push;
Stage 3C/3C-A.

## Starting state

- Target M3 worktree `D:\量化分析-m3-stage3b` was clean at the required R3 final HEAD and 0/0 versus
  `origin/feat/m3-mechanism-validation-mvp`.
- User-facing M2 worktree `D:\量化分析` was on `feat/m2-value-assessment-mvp` at `241c180`, dirty;
  it is protected and not used for this task.
- `stash@{0}` was present and untouched.
- `data/research.duckdb` was absent in the target worktree.
- R3 acceptance is already `ACCEPTED`, while the R3 Goal and record still report `IN_PROGRESS`; this
  is a governance status drift to close with the first R4 governance change.
- Existing R3 transports are EIA-keyed oil and a Shenwan source ladder; R4 will add separate source-
  accurate adapters and preserve all R3 frozen JSON hashes.

## Implementation plan

1. Reconcile North-Star/R3 state, create R4 contract and close R3 governance drift.
2. Inspect current AKShare CNI implementation before real acquisition; implement raw-byte bounded
   FRED and CNI adapters with fail-closed holdout handling.
3. Add R4 normalization/alignment/readiness CLI and reports, using the frozen R1 market proxy.
4. Add focused synthetic fixture tests before any real network request.
5. Run contract tests, then one bounded development-only acquisition per source if transport proofs
   pass; generate reports and acceptance without research outputs.
6. Run full validation, independently inspect final Git/protected state, and stop for North-Star review.

## Decision log

- Work in the existing isolated M3 worktree to preserve the dirty M2 worktree and protected stash.
- Oil source identity is unchanged: EIA remains the economic source and FRED is distribution transport;
  this is not a new oil factor.
- CNI `399439` is fixed as the new primary before any outcome result. It is research-purpose compatible
  but not semantically identical to Shenwan Petroleum & Petrochemicals; `000928` remains a future-only
  secondary robustness candidate and is not acquired.
- Raw-byte bounded proof is a hard gate. A response that contains holdout content is rejected before
  normalization; local filtering cannot make it safe.

## Actual operations

1. Verified the required isolated M3 baseline: branch `feat/m3-mechanism-validation-mvp`, HEAD
   `8825c0e450dafa47f4b92bc4a3a83726c686b380`, remote `0/0`, clean worktree; confirmed M2 worktree
   remains dirty but unchanged, `stash@{0}` remains present, and default DuckDB is absent.
2. Re-read North-Star, project governance, R3 Goal/acceptance/record, frozen contracts/reports, and
   current mechanism code/tests. Confirmed R3 acceptance was ACCEPTED while its Goal/record were
   IN_PROGRESS; synchronized both to `CLOSED — USER-INPUT/SOURCE-GAP ACCEPTANCE` with R3 HEAD
   `8825c0e...` and CI `31880528110 PASS`.
3. Added the R4 Goal and record before implementation, plus the source amendment, oil v3 transport
   contract, CNI industry v2 contract, source registry, development manifest, coverage/readiness/
   joint reports, acceptance, and focused tests. Updated README's factual M3 status.
4. Inspected installed AKShare `1.18.79` `index_hist_cni` source. It calls the official
   `http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat` endpoint with
   `indexCode`, `startDate`, `endDate`, and `frequency` in one response; date bounds reach the server
   and are not local full-history filtering.
5. Implemented `acquisition_fred_public.py` and `acquisition_cni.py`. Both inspect raw response bytes
   for date bounds before parsing, reject holdout content, preserve immutable raw SHA-256, validate
   identity/schema/numeric values, and expose offline normalization. CNI null closes remain gaps;
   non-empty malformed values fail closed. Added CNI simple close-to-close returns without splice or
   forward fill. Added `m3_stage3br4_data.py` CLI for probe/acquire/normalize/align/readiness/reports/run.
6. Pre-network gate passed: R4 focused tests plus Stage 3A/B/R1/R2/R3 boundary tests passed `123`;
   after subsequent actual-schema coverage and README checks, the focused set passed `136`.
7. Real bounded acquisition used external root `D:\m3_stage3br4_external_20260821` and reused the
   frozen R1 external root `D:\m3_stage3br1_external_20260815`; no default DB or Git raw cache was
   used. The first FRED request exposed the actual `observation_date` header (parser compatibility
   fix); the first CNI response exposed comma-formatted closes and a null close (numeric/null-gap
   fixes). No failed response was written as raw; the final accepted raw caches are development-only.
8. Final accepted FRED raw cache: 2,057 rows, SHA
   `185080c6937d09b1dc3a2db46746a8e9bbdac5d17d8165596e9211fcc45e2d53`, raw date max `2022-12-30`.
   Final accepted CNI raw cache: 1,949 valid rows, SHA
   `c80a609c6dc1ff461b6010f0b1ebcd2230095f466af4f257be91d74faf9afee6`, raw date max `2022-12-30`.
9. Offline A/B normalize and align were run once per source cache. All five canonical outputs were
   identical between A/B. Joint structural readiness is 1,902 valid dates from `2015-03-16` to
   `2022-12-30`; gaps are market 68, industry 22, oil 2. No mechanism statistic was run.
10. Fixed CSV round-trip restoration for boolean/list readiness fields so report gap reason counts
    remain `MARKET_PROXY_INVALID=68`, `INDUSTRY_INVALID=22`, `OIL_INVALID=2`. Regenerated all R4
    dynamic reports with bounded proof, source inspection, ranges, hashes, A/B digests, and coverage.

## Data and method

- Development end: `2022-12-31`; holdout start: `2023-01-01`.
- Oil: `DCOILBRENTEU`, Europe Brent Spot Price FOB, daily, USD/barrel, strict-prior anchor, max age
  7 calendar days.
- Industry: CNI `399439`, CNI Oil & Gas Index / 国证石油天然气指数, simple close-to-close price return.
- Market proxy: frozen R1 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`.
- No mechanism statistic or restricted research result is permitted.

## Validation

- `pytest -q tests/test_m3_stage3br4_no_credential_tier1_source_amendment.py ... tests/test_m2_stage2j_conditional_closeout.py`: PASS, `136 passed`.
- `pytest -q`: PASS, `2056 passed, 3 skipped, 2 warnings`.
- `ruff check src/ tests/`: PASS.
- `python -m compileall -q src tests`: PASS.
- `git diff --check`: PASS.
- Frozen SHA audit: Stage 3A `3`, Stage 3B v1 `5`, R1 `5`, R2 `6`, R3 `6`: PASS.
- R4 JSON parse and restricted-output scan: PASS.
- Raw-byte bounded proof: FRED and CNI max observation date `2022-12-30`; normalized/aligned/readiness
  max dates are before `2023-01-01`; no credentials or default DB: PASS.
- Offline A/B canonical identity: PASS for oil, CNI industry, both aligned outputs, and readiness.
- Protected-state audit: M2 worktree, stash, and origin branches preserved.

## Result and outstanding issues

Result is a conditional pre-outcome PASS: both Tier-1 sources are trusted and joint readiness is
ready, so only the Stage 3C-A pipeline-lock implementation is allowed by the R4 gate. Stage 3C real
analysis remains prohibited and the task stops for North-Star review. Shenwan is deferred as the
historical source-gap evidence requires; no robustness candidate was acquired.

No unresolved data blocker remains for the R4 Tier-1 development inputs. The external raw cache is
intentionally outside Git and must remain immutable if reused. Two parser-compatibility corrections
were made during acquisition; the final bounded raw proofs and all offline identity checks passed.

## Final Git state

To be filled after the R4 commit and final branch/origin review. No push, PR, merge, tag, or Stage 3C
start is authorized by this record before explicit North-Star review.
