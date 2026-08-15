# Work Record: M3 Stage 3B-R3 — Tier-1 Acquisition Unblock & Data Closeout

Status: IN_PROGRESS — PRE_OUTCOME_DATA_ACQUISITION_UNBLOCK

## Basic information

- Date: 2026-08-15
- Agent: Claude Code
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `2042e44` (full `2042e44e6d571e968febeb6389d93141bea389e9`)
- Task source: North-Star-authorized M3 Stage 3B-R3 execution instruction
- Module: mechanism validation / Tier-1 development inputs (data transport + readiness)
- Goal contract: `agent/goals/2026-08-15_m3_stage3br3_tier1_acquisition_unblock.md`

## Objective

Unblock the two remaining Tier-1 development inputs (`oil`, `petrochemical_industry`) that Stage
3B-R2 confirmed were unobtainable through a bounded, holdout-safe path, then re-compute joint Tier-1
readiness against the trusted `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` proxy. This stage is
DATA TRANSPORT + PROVENANCE + NORMALIZATION + READINESS only. No new research contract, no new
proxy/control design, no model implementation, and no real mechanism analysis.

## Scope

- Repair the Stage 3B-R2 Goal/work-record governance status drift to CLOSED.
- Add the R3 goal, work record, focused source-resolution ladder for oil and industry, bounded
  acquisition transports, R3 reports, acceptance, and focused tests.
- Add a bounded EIA Open Data API v2 transport with strict secret redaction and official route
  discovery, and a Shenwan official-source-resolution ladder.
- Reuse the already-tested R2 normalize/align/readiness logic; do not re-implement it.
- Commit and normally push logical commits to `feat/m3-mechanism-validation-mvp`.

## Non-goals

- Stage 3C or 3C-A implementation or analysis.
- Any mechanism/outcome statistic (crash-day, correlation, abnormal return, regression, gamma,
  p-value, CI, bootstrap, effect size, FDR, evidence level, index offset).
- Redesigning the primary market proxy, oil timing contract v2, or industry taxonomy.
- Modifying any frozen Stage 3A / 3B v1 / 3B-R1 / 3B-R2 artifact; replacing WTI/Shanghai
  crude/BZ=F or an industry ETF/CSI/THS proxy.
- Reading the sealed holdout; `download full history then filter`; PR/merge/force-push; default DB
  writes; committing raw data or secrets; M2/stash mutation.

## Starting state

- M3 worktree `D:\量化分析-m3-stage3b` on `feat/m3-mechanism-validation-mvp` at `2042e44`, clean.
- M2 worktree `D:\量化分析` protected on `feat/m2-value-assessment-mvp` at `241c180`, dirty, unused.
- Protected stash `stash@{0}` (Stage 1B.4 record edit) present, untouched.
- No `data/research.duckdb` in the isolated worktree.
- Stage 3A / Stage 3B v1 / Stage 3B-R1 frozen SHA-256 re-verified unchanged (see validation).
- Stage 3B-R2 final-tip CI `31877910646` PASS (Windows/Ubuntu clean-clone + identity-compare).
- Market proxy v2 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` TRUSTED (1,902 OK / 68 gap, 2015-03-16 →
  2022-12-30).
- `EIA_API_KEY` absent from the current process environment (checked redacted).
- AKShare `index_hist_sw` confirmed to call the unbounded `index_publish/trend/` endpoint with only
  `swindexcode`+`period`; no server-side date bounds exist in any of the three SWS endpoint families
  present in AKShare (`trend/`, `details/timelines/`, `index_analysis_report/`).
- No official Shenwan development capsule exists in the repo, `tmp/`, or the
  `%USERPROFILE%\.codex\external-cache\ashare-research\` root.

## Implementation plan

1. Repair R2 governance status drift; create R3 goal and work record (record-first).
2. Implement `acquisition_eia.py` (bounded EIA API v2 transport, secret redaction, route discovery)
   and `acquisition_shenwan.py` (official-source-resolution ladder).
3. Add Stage 3B-R2/R3 frozen hashes to `contracts.py`; extend the package guard with the new
   transport modules.
4. Add the Stage 3B-R3 acquisition CLI reusing the tested R2 normalize/align/readiness logic.
5. Attempt the bounded acquisition (oil gated on env key; industry via the source-resolution
   ladder) and generate the six R3 reports reflecting the honest state.
6. Add focused R3 tests (secret redaction + bounded acquisition + industry ladder + frozen hashes).
7. Run all local gates, commit/push, wait for CI, and independently review.

## Decision log

- The EIA API key is read only from the process environment and never persisted; with no key the oil
  step reports `OIL_EIA_API_KEY_REQUIRED` and the transport is left fully implemented and tested so
  that only the bounded oil acquisition step needs rerunning once the user sets the key.
- FRED `DCOILBRENTEU` is a secondary distribution of EIA and is `OPTIONAL_SECONDARY_DISTRIBUTION_
  CROSSCHECK`; FRED unreachability is `FRED_CROSSCHECK_UNAVAILABLE_NON_BLOCKING` and never blocks oil
  when the EIA authoritative bounded path is trusted.
- The SWS source-resolution ladder is followed in order (A official bounded transport, B existing
  official capsule, C user-provided official development capsule, D same-series third-party
  transport). No bounded SWS transport, no existing capsule, and no user-provided capsule exists in
  this environment, so industry is reported `INDUSTRY_OFFICIAL_DEVELOPMENT_CAPSULE_REQUIRED` unless a
  bounded path or capsule is proven.
- No mechanism/outcome statistic is executed at any point this stage.

## Actual operations

1. Verified the Stage 3B-R2 final-tip CI gate: `gh run view 31877910646` → `completed`/`success`,
   headSha `2042e44e6d571e968febeb6389d93141bea389e9`; Windows + Ubuntu clean-clone and
   identity-compare all success.
2. Confirmed the M3 worktree `D:\量化分析-m3-stage3b` on `feat/m3-mechanism-validation-mvp` at
   `2042e44`, clean; M2 worktree `D:\量化分析` protected at `241c180`, dirty, untouched; `stash@{0}`
   preserved; no `data/research.duckdb` in the isolated worktree.
3. Re-read the North-Star docs, `AGENTS.md` (M2 worktree copy), Stage 3A / 3B v1 / 3B-R1 / 3B-R2
   contracts, R2 goal/acceptance/record, and the existing mechanism source and tests; re-verified
   the frozen Stage 3A / Stage 3B v1 / Stage 3B-R1 SHA-256 values unchanged.
4. Established the R3 environmental facts:
   - `EIA_API_KEY` is absent from the current process environment (checked redacted, never printed).
   - AKShare `index_hist_sw` calls `index_publish/trend/` with only `swindexcode`+`period`; the
     three SWS endpoint families in AKShare (`trend/`, `details/timelines/`,
     `index_analysis_report/`) all ignore server-side date bounds.
   - No official Shenwan development capsule exists in the repo, `tmp/`, or the
     `%USERPROFILE%\.codex\external-cache\ashare-research\` root.
5. Created the R3 Goal contract and this work record (record-first); repaired the R2 Goal and R2
   work-record governance status drift to CLOSED with final HEAD/CI closeout evidence.
6. Implemented `src/ashare_research/mechanism/acquisition_eia.py` (bounded EIA Open Data API v2
   transport: environment-only key, official route discovery, server-side bounded request,
   response validation, secret redaction) and `acquisition_shenwan.py` (official source-resolution
   ladder: Route A official bounded transport, Route B existing capsule, Route C user-provided
   official development capsule, Route D same-series third-party transport).
7. Added Stage 3B-R2/R3 frozen hashes to `contracts.py` and extended the Stage 3A package guard
   with the two new transport modules.
8. Implemented `src/ashare_research/tools/m3_stage3br3_data.py` (bounded acquisition CLI reusing
   the tested R2 normalize/align/readiness logic).
9. Ran `acquire-oil` (reports `OIL_EIA_API_KEY_REQUIRED`; no raw file written) and
   `acquire-industry` (reports `INDUSTRY_OFFICIAL_DEVELOPMENT_CAPSULE_REQUIRED` with the ladder
   codes) and generated the six R3 reports reflecting the honest `NOT_ACQUIRED`/`NOT_READY` state.
10. Added the focused Stage 3B-R3 test suite (tests/test_m3_stage3br3_tier1_acquisition.py, 29
    tests) covering secret redaction, bounded acquisition, the industry ladder, and frozen hashes.
11. Ran ruff (auto-fixed then manual line-length fixes), compileall, the focused R3/R2/Stage3
    boundary tests (112 passed), the M2 Stage 2J closeout wording test (13 passed), and the full
    test suite.
12. Wrote the acceptance document and this work-record closeout; updated the README factual status.

## Data & method

- Oil: Europe Brent Spot Price FOB (EIA RBRTE), USD/barrel, daily; alignment
  `STRICTLY_PRIOR_BRENT_OBSERVATION_DATE` (frozen v2), 7-day anchor staleness gate, no override.
  Transport: EIA Open Data API v2, environment-only key, server-side bounded
  `2014-12-01` .. `2022-12-31` (warm-up + development), never reads 2023+. FRED DCOILBRENTEU is an
  optional secondary-distribution cross-check (non-blocking).
- Industry: Shenwan Petroleum and Petrochemicals Industry Price Index, `801016` (SW_2014, through
  2021-12-10) and `801960` (SW_2021, from 2021-12-13); within-regime simple price returns;
  `2021-12-13 INDUSTRY_TAXONOMY_TRANSITION_GAP`; missing closes fail closed (no forward-fill).
- Joint readiness: intersection of the three Tier-1 valid dates; no forward-fill; coverage only.
- Holdout: `>= 2023-01-01` sealed; never requested/read/parsed/stored/analyzed.

## Validation

- Focused Stage 3B-R3 tests: 29 passed.
- Stage 3B-R2 + Stage 3A + Stage 3B v1 + Stage 3B-R1 boundary tests: 83 passed.
- M2 Stage 2J closeout wording test: 13 passed (README `No real mechanism inference` phrase intact).
- `ruff check src/ tests/`: PASS. `python -m compileall -q src tests`: PASS.
  `git diff --check`: PASS.
- All 6 Stage 3B-R3 reports parse; no restricted research outputs; holdout sealed; no real 2023+
  date (only the frozen `2021-12-10` / `2021-12-13` regime boundaries and the development
  `<= 2022-12-31` bound); no default `data/research.duckdb` in the isolated worktree.
- Frozen Stage 3A (3) / Stage 3B v1 (5) / Stage 3B-R1 (5) / Stage 3B-R2 (6) SHA-256: unchanged.
- Stage 3B-R3 frozen SHA-256 (6 reports): verified against `contracts.py`.
- Full `pytest -q` (with worktree `src` on `PYTHONPATH`): PASS (see final counts).
- Protected state: branch `feat/m3-mechanism-validation-mvp`; `stash@{0}` preserved; no
  `data/research.duckdb`; M2 worktree untouched.

## Result

- **Verdict:** `M3_STAGE3BR3_TIER1_SOURCE_GAPS_REMAIN` (both Tier-1 controls remain not acquired
  through a bounded, holdout-safe path in this environment). Decision set:
  `M3_STAGE3BR3_OIL_AUTH_INPUT_REQUIRED`,
  `M3_STAGE3BR3_INDUSTRY_DEVELOPMENT_CAPSULE_REQUIRED`,
  `M3_TIER1_DEVELOPMENT_INPUTS_NOT_READY`, `M3_HOLDOUT_REMAINS_SEALED`,
  `M3_STAGE3C_NOT_ALLOWED`, `STOP_FOR_NORTH_STAR_REVIEW`.
- **implementation**: PASS (secret-redacted EIA v2 bounded transport, industry source-resolution
  ladder, Stage 3B-R3 acquisition CLI, offline tests green).
- **data acquisition**: NOT ACQUIRED — oil `OIL_EIA_API_KEY_REQUIRED`; industry
  `INDUSTRY_OFFICIAL_DEVELOPMENT_CAPSULE_REQUIRED`.
- **data trust**: NOT TRUSTED for oil/industry; joint Tier-1 NOT_READY; market proxy v2 TRUSTED.
- **research result**: NOT EXECUTED — no PetroChina mechanism/outcome statistic was computed.
- Completed: R2 governance repair; R3 goal/work record; bounded EIA transport; industry
  source-resolution ladder; Stage 3B-R3 CLI; six R3 reports; 29 focused tests; frozen Stage
  3A/3B-v1/3B-R1/3B-R2/3B-R3 hashes; README status; acceptance; full + boundary test suites green.

## Outstanding issues

- Oil: `EIA_API_KEY` is absent from the process environment. The bounded EIA transport is fully
  implemented and tested; set the key locally (never in chat, Goal, or Git) and rerun only the
  bounded oil acquisition step.
- Industry: no bounded SWS transport, no existing official capsule, and no user-provided official
  development capsule exist in this environment. Provide an official Shenwan development-only
  immutable capsule (`industry_801016.csv` + `industry_801960.csv`, only `<= 2022-12-31`, SHAs
  recorded), then rerun the industry ladder / offline normalize / align steps.
- Joint Tier-1 readiness remains NOT_READY until both controls are acquired and aligned.

## Next steps

- North-Star review of the source-gap verdict; provide the exact unblock inputs named in the
  acceptance (EIA_API_KEY for oil; official Shenwan development capsule for industry).
- Once both bounded inputs are available, run the acquisition + offline normalize (A/B) + align
  pipeline and refresh the Stage 3B-R3 readiness reports.
- Stage 3C and Stage 3C-A remain NOT ALLOWED until Tier-1 inputs are TRUSTED.

## Final file changes

- New: `agent/goals/2026-08-15_m3_stage3br3_tier1_acquisition_unblock.md`,
  `agent/record/2026-08-15_Stage3BR3_tier1_acquisition_unblock.md`,
  `acceptance/m3_stage3br3_tier1_acquisition_unblock.md`,
  `src/ashare_research/mechanism/acquisition_eia.py`,
  `src/ashare_research/mechanism/acquisition_shenwan.py`,
  `src/ashare_research/tools/m3_stage3br3_data.py`,
  `tests/test_m3_stage3br3_tier1_acquisition.py`,
  `reports/m3_stage3br3_source_resolution_v1.json`,
  `reports/m3_stage3br3_oil_development_manifest_v1.json`,
  `reports/m3_stage3br3_industry_development_manifest_v1.json`,
  `reports/m3_stage3br3_data_coverage_v1.json`,
  `reports/m3_stage3br3_tier1_readiness_v2.json`,
  `reports/m3_stage3br3_joint_input_manifest_v1.json`.
- Modified: `agent/goals/2026-08-15_m3_stage3br2_oil_industry_acquisition_and_alignment.md`
  (status → CLOSED), `agent/record/2026-08-15_Stage3BR2_oil_industry_acquisition_and_alignment.md`
  (status → CLOSED), `src/ashare_research/mechanism/contracts.py` (Stage 3B-R2/R3 frozen hashes),
  `tests/test_m3_stage3a_mechanism_preflight.py` (package guard includes the two transport modules),
  `README.md` (Stage 3B-R3 status).

## Final Git state

- Branch: `feat/m3-mechanism-validation-mvp`
- Commits (4, pushed to origin): close Stage 3B-R2 + authorize unblock (`aa2ba6f`); bounded Tier-1
  acquisition transports (`ffd30e6`); validate development data + joint readiness (`d9fd980`);
  close Stage 3B-R3 (`8991e64`).
- Working tree clean; protected `stash@{0}` preserved; no `data/research.duckdb`.
- Original M2 worktree untouched; no PR, no merge, no force push, no Stage 3C/3C-A, no holdout read.