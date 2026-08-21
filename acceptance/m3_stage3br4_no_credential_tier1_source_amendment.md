# M3 Stage 3B-R4 — No-Credential Tier-1 Source Amendment & Acquisition

Status: ACCEPTED — PRE-OUTCOME SOURCE AMENDMENT AND TIER-1 ACQUISITION

## Verdict

`M3_STAGE3BR4_PRE_OUTCOME_SOURCE_AMENDMENT_ACCEPTED`

Decision set:

- `M3_MARKET_PROXY_V2_TRUSTED`
- `M3_OIL_CONTROL_V3_TRUSTED`
- `M3_CNI_OIL_GAS_INDUSTRY_CONTROL_V2_TRUSTED`
- `M3_SHENWAN_INDUSTRY_CONTROL_DEFERRED_NON_BLOCKING`
- `M3_TIER1_DEVELOPMENT_INPUTS_READY`
- `M3_HOLDOUT_REMAINS_SEALED`
- `M3_STAGE3CA_PIPELINE_LOCK_IMPLEMENTATION_ALLOWED`
- `M3_STAGE3C_REAL_ANALYSIS_NOT_AUTHORIZED`
- `STOP_FOR_NORTH_STAR_REVIEW`

No PetroChina mechanism/outcome statistic was calculated.

## Amendment reconciliation

Oil keeps the economic variable `Europe Brent Spot Price FOB`, FRED series `DCOILBRENTEU`, and
underlying economic source U.S. EIA. Only distribution transport changed from the authenticated EIA
API path to the no-credential FRED public graph CSV. The strictly-prior Brent observation-date rule,
same-calendar-day prohibition, seven-calendar-day stale-anchor gate, simple return semantics, and
missing-value policy remain frozen.

The original Shenwan `801016 SW2014 -> 801960 SW2021` primary was not automatically bounded. Before
any outcome was read, R4 fixed the official CNI Oil & Gas Index `399439` as the new primary
implementation `CNI_OIL_GAS_399439_PRICE_RETURN_V2`. This is not an assertion that CNI equals Shenwan:
semantic equivalence is `NOT_EXACT`, while research-purpose equivalence is `ACCEPTABLE_PRE_OUTCOME`.
The choice used industry meaning, official identity, free bounded transport, development coverage,
continuity, and reproducibility—not any PetroChina result. `000928 中证能源` is registered only as a
future secondary robustness candidate and was not acquired.

Official CNI identity lineage:

- code/name: `399439`, 国证石油天然气指数 / CNI Oil & Gas Index, short name 国证油气;
- publisher: Shenzhen Securities Information Co., Ltd. / CNI;
- publication date: `2014-12-30`;
- current methodology lineage: adjusted free-float market-cap weighting, semiannual review, and
  official constituent/weight-cap rules;
- 2022 revision: official announcement `2022-11-01`, effective `2022-11-08`; historical levels were
  not manually spliced or rebased.

Official references: [CNI factsheet](https://www.cnindex.com.cn/html2pdf/preview/jj_399439.pdf),
[CNI methodology](https://www.cnindex.com.cn/docs/gz_399439.pdf), [2014 release](https://www.cnindex.com.cn/zh_information/notices_news/2014/201412/P020191213350049547779.pdf),
and [2022 revision announcement](https://www.cnindex.com.cn/zh_information/notices_news/2022/202201/t20220118_17939.html).

## Acquisition and coverage evidence

Development window: warm-up `2014-12-01`, development `2015-01-01..2022-12-31`; holdout
`>= 2023-01-01` remained sealed.

Oil:

- transport: FRED public graph CSV, no API key;
- raw SHA-256: `185080c6937d09b1dc3a2db46746a8e9bbdac5d17d8165596e9211fcc45e2d53`;
- raw range: `2014-12-01..2022-12-30`; raw rows: `2057`;
- normalized rows: `2057`; aligned valid/gap rows: `1969 / 1`;
- maximum observed anchor age: `3` calendar days;
- offline A/B normalized digest: `61b16ae4ac40e430aff9dba2436ff3345f93697982a5b4ac0be7f64caf68a427`;
- raw-byte bounded proof passed; no `2023+` date token was present.

Industry CNI 399439:

- transport: official `hq.cnindex.com.cn` bounded endpoint, source-inspected through AKShare
  `index_hist_cni`; request parameters reached the server and the adapter is single-response, not
  local full-history filtering;
- raw SHA-256: `c80a609c6dc1ff461b6010f0b1ebcd2230095f466af4f257be91d74faf9afee6`;
- raw range: `2014-12-01..2022-12-30`; valid raw/normalized rows: `1949`;
- aligned valid/gap rows: `1948 / 22`;
- offline A/B normalized digest: `4c3b9aea6c4322e500c94c4974291b0cd7192128541dcb7e572d83ebb89a7ff`;
- raw-byte bounded proof passed; one null close was retained as a missing-data gap, never converted to
  zero; no `2023+` date token was present.

Market proxy: frozen R1 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` was reused, with `1902` valid rows and
`68` preserved gap rows. It was not reacquired.

Joint structural readiness:

- market valid: `1902`;
- oil valid: `1968`;
- industry valid: `1948`;
- joint valid: `1902`;
- first/last joint valid date: `2015-03-16..2022-12-30`;
- gap reasons: `MARKET_PROXY_INVALID=68`, `INDUSTRY_INVALID=22`, `OIL_INVALID=2`.

These are coverage/alignment facts only. No return of PetroChina, crash indicator, abnormal return,
correlation, regression, p-value, confidence interval, bootstrap, effect size, sensitivity, or other
mechanism result is present.

## Validation and protected state

- pre-network contract/transport/boundary gate: `123 passed`;
- R4 focused tests: `11 passed`;
- `ruff check src/ tests/`: PASS;
- `python -m compileall -q src tests`: PASS;
- offline A/B: PASS, all normalized/aligned/readiness canonical digests identical;
- frozen Stage 3A/B/R1/R2/R3 hashes: PASS;
- raw/normalized/aligned data and reports contain no observation on or after `2023-01-01`;
- restricted-output scan: PASS;
- default `data/research.duckdb`: absent/unchanged;
- protected M2 worktree and `stash@{0}`: unchanged;
- no PR, merge, tag, force-push, or Stage 3C implementation.

Final branch/HEAD, local/origin synchronization, commit list, and final CI run IDs are recorded in
the R4 work record after commit and independent final review.

## Stop

`STOP_FOR_NORTH_STAR_REVIEW` — pipeline-lock implementation may proceed only after explicit review;
Stage 3C real analysis was not authorized or started.
