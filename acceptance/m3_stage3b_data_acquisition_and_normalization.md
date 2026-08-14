# M3 Stage 3B — Data Acquisition and Normalization Acceptance

Status: PASS — fail-closed data-gap acceptance

## Verdict and decision

- Governance verdict: **PASS** for the authorized Stage 3B fail-closed path.
- Decision: `M3_STAGE3B_REQUIRED_INPUT_GAPS_REMAIN`.
- Primary proxy: `M3_PRIMARY_PROXY_NOT_TRUSTED`.
- Holdout: `M3_HOLDOUT_REMAINS_SEALED`.
- Next stage: `M3_STAGE3C_NOT_ALLOWED`.
- Stop: `STOP_FOR_NORTH_STAR_REVIEW`.

This is not a trusted-input completion. It is an accepted refusal to manufacture or substitute the
primary proxy after bounded acquisition proved that complete strict inputs had not been obtained.

## Frozen semantics

Stage 3A's three accepted JSON contracts remain exact-byte unchanged. Stage 3B addenda freeze:

- pre-2020-07-22 and from-2020-07-22 SSE Composite methodology regimes separately;
- physical exclusion of `601857.SH`;
- total-market-cap/issued-share weighting with official-divisor-equivalent continuity;
- no SSE Composite, equal-weight, survivorship, current-constituent, or future-information fallback;
- adjusted target analysis return versus unadjusted index-contribution return;
- simple market price return;
- EIA Europe Brent Spot Price FOB with release-time availability before 15:00 CST;
- explicit Shenwan `801016` to `801960` taxonomy transition;
- exact bootstrap block formula and positive-decision semantics without statistical execution.

Official methodology evidence:

- SSE 2007 new-listing rule: `https://www.sse.com.cn/market/sseindex/diclosure/c/c_20150911_3984926.shtml`
- SSE 2010 factbook formula/maintenance: `https://www.sse.com.cn/aboutus/publication/factbook/documents/c/10170572/files/36d0635dee474838943e931bcc04c3df.pdf`
- SSE/CSI 2020 amendment: `https://www.sse.com.cn/market/sseindex/diclosure/c/c_20200619_5130635.shtml`
- SSE/CSI methodology effective 2020-07-22: `https://www.sse.com.cn/market/sseindex/diclosure/c/10077926/files/2b34d5d25e34437db3518a0d6059d7c8.pdf`

## One-shot bounded acquisition

External root: not committed; recorded only as an external Stage 3B capsule. Every request was
bounded at `2022-12-31`; no 2023+ market outcome was requested, read, or normalized.

- Trade calendar: 2,953 calendar rows, 1,970 open dates, 2014-12-01..2022-12-31.
- `601857.SH` unadjusted daily: 1,970 rows, 23 warm-up + 1,947 development rows.
- `601857.SH` qfq daily: 1,970 rows, 23 warm-up + 1,947 development rows.
- Baostock dated-snapshot feasibility: four regime/boundary dates, 17,479 raw rows.
- CNINFO issued-share feasibility: A/H (`601857`), A (`600000`), and B (`900901`) samples,
  171 raw rows, all requests ending 2022-12-31.
- Raw acquisition manifest SHA-256:
  `35d83fef930ed3a50c9e917059fb69f1ec2cd4194235ea3f753f76a88ecd774b`.

Raw inputs remain external and immutable. Git contains only contracts, relative logical paths,
hashes, schemas, row/date coverage, code, tests, and acceptance evidence.

## Primary proxy fail-closed finding

The strict primary proxy was not constructed because the acquired inputs do not establish all of:

1. complete daily official index eligibility for every 2015-2022 date (the dated Baostock endpoint
   mixes stocks, indices, and other securities and exposes trade status/name, not official index
   membership under the applicable regime);
2. complete applicable issued-share history for every eligible A/B/CDR security;
3. complete official corporate-action reference prices and divisor-continuity inputs across the
   full period.

The sampled CNINFO data are useful feasibility evidence and include A/B/H share fields, but three
issuers cannot prove full-market coverage or exact index-calculation semantics. No current-universe
backfill, free-float substitution, turnover inference, equal weighting, or direct `000001` fallback
was used.

Because the acquisition order required primary proxy completion before oil and industry, network
acquisition stopped at this hard gate. Oil and petrochemical industry remain explicitly not acquired
for Stage 3B rather than silently changing sources or continuing after a blocking Tier-1 input.

## Offline reproducibility

The acquired usable subset was normalized twice with no further network access:

- offline audit A/B SHA-256:
  `db0b0908b80bcb0bac2654eb9e883d4fb07b2542d90296bf3e7d1a71613dbd27`;
- calendar A/B exact bytes: identical;
- target qfq A/B exact bytes: identical;
- target unadjusted A/B exact bytes: identical;
- all raw manifest hashes reverified before both offline runs.

## Scope proof

- No holdout outcome acquisition/read/normalization.
- No crash-day count, return relationship, correlation, positive probability, abnormal return,
  regression coefficient, p-value, interval, bootstrap output, effect size, or evidence grade.
- No funding-actor or intent claim.
- No Stage 3C module, scipy/statsmodels dependency, PR, merge, or default DB write.
- No Stage 3A mutation and no protected M2 worktree/stash mutation.

## Local validation

- PowerShell-resolved focused Stage 3B suite: **22 passed**.
- Stage 3A + Stage 3B + living M2 status boundary: **45 passed**.
- Full offline suite after updating two stale living-status assertions: **1965 passed, 3 skipped**;
  two pre-existing pandas date-parser warnings remain.
- `ruff check src/ tests/`: PASS.
- `python -m compileall -q src tests`: PASS.
- `git diff --check`: PASS.
- Stage 3A exact-byte SHA gate: PASS.
- Default `data/research.duckdb`: absent before and after.

## Remote CI

- Implementation/acceptance tip: `f6d155282296c61d071d15ccf5651692e9c366a4`.
- GitHub Actions run: `31765256230`.
- Ubuntu clean-clone, static, contract, capsule, full-suite, and identity-envelope job: PASS.
- Windows clean-clone, static, contract, capsule, full-suite, and identity-envelope job: PASS.
- Cross-platform provenance-gated identity comparison: PASS.
- Only upstream GitHub Actions Node.js 20 deprecation annotations remain.

## Closure semantics

Closure is conditional on the required GitHub checks attached to the governance-closeout commit
reaching PASS. The CI run identifier is external evidence and is not required to be embedded into
the same commit. Once those checks pass, no follow-up CI-evidence-only commit is required.

Stage 3C remains prohibited regardless of CI success and requires a separate North-Star review and
authorization.
