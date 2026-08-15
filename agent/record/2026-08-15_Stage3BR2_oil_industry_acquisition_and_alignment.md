# Work Record: M3 Stage 3B-R2 — Oil & Petrochemical Industry Acquisition, PIT Alignment & Tier-1 Closeout

Status: IN_PROGRESS — PRE_OUTCOME_TIER1_DATA_CLOSEOUT

## Basic information

- Date: 2026-08-15
- Agent: Claude Code
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `b7c8bec` (full `b7c8becc69fc1e7647fa23b7444cbbbeaf8f0364`)
- Task source: user-authorized M3 Stage 3B-R2 execution instruction
- Module: mechanism validation / Tier-1 development inputs
- Goal contract: `agent/goals/2026-08-15_m3_stage3br2_oil_industry_acquisition_and_alignment.md`

## Objective

Complete the two remaining Tier-1 inputs (`oil`, `petrochemical_industry`) and establish a
development-period PIT-safe alignment for the joint Tier-1 date set consistent with the trusted
`SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` market proxy. This stage performs a formal pre-outcome timing
supersession for the Stage 3B v1 oil publication-timestamp overspecification, builds the oil /
industry / alignment modules and a bounded acquisition CLI, and produces an honest Tier-1 readiness
verdict. No mechanism/outcome result is computed.

## Scope

Stage 3B-R2 timing resolution + oil contract v2, source registry, development input manifest, data
coverage, tier-1 readiness, oil/industry/alignment modules, bounded acquisition CLI, focused tests,
acceptance, commits, push, and CI closeout.

## Non-goals

Stage 3C implementation or analysis; crash-day / correlation / abnormal-return / regression /
bootstrap / evidence-level results; rebuilding industry-ex-target; fetching all Shenwan constituents;
Tier-2/3 acquisition; modifying any frozen Stage 3A/3B v1/3B-R1 artifact; default DB writes;
large raw-data commits; M1/M2 refactors; PR or merge.

## Starting state

- M3 worktree `D:\量化分析-m3-stage3b` on `feat/m3-mechanism-validation-mvp` at `b7c8bec`, clean.
- M2 worktree `D:\量化分析` protected on `feat/m2-value-assessment-mvp` at `241c180`, dirty, unused.
- Protected stash `stash@{0}` (Stage 1B.4 record edit) present, untouched.
- No `data/research.duckdb` in the isolated worktree.
- Stage 3A / Stage 3B v1 frozen SHA-256 re-verified unchanged (see validation).
- Market proxy v2 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` TRUSTED (1,902 OK / 68 gap, 2015-03-16 →
  2022-12-30).

## Risks identified

- Bounded, holdout-safe acquisition of Brent and Shenwan industry may be impossible in this
  environment: EIA keyless returns full history (ignores date params), EIA API v2 needs an
  unavailable key, FRED (stlouisfed.org) is unreachable, and the SWS official endpoint ignores date
  params and returns full history through 2026. If so, the honest outcome is the sanctioned input-gap
  verdict, never reading the holdout or substituting a non-frozen proxy.

## Implementation plan

1. Establish Goal contract and work record.
2. Freeze oil timing resolution + oil contract v2 (pre-outcome supersession).
3. Implement oil.py, industry.py, alignment.py, and the bounded acquisition CLI.
4. Attempt bounded acquisition; document source unavailability honestly.
5. Add focused tests; generate reports reflecting actual status.
6. Run all local gates, commit/push, wait for CI, and independently review.

## Decision log

- Operate in the isolated M3 worktree; preserve protected M2 state and stash.
- The oil alignment supersession is expressed only through new addendum artifacts; all v1/v2/R1
  frozen contracts stay byte-identical.
- If bounded acquisition is not provable without reading 2023+, the stage outputs the sanctioned GAP
  verdict; the pipeline/code/tests remain the deliverable and oil/industry are reported NOT TRUSTED.
- No mechanism/outcome statistic is executed at any point this stage.

## Actual operations

1. Verified the Stage 3B-R1 final-tip CI gate: `gh run view 31871858528` → `completed`/`success`,
   headSha `b7c8becc69fc1e7647fa23b7444cbbbeaf8f0364`; Windows + Ubuntu clean-clone and
   identity-compare all success.
2. Confirmed the M3 worktree `D:\量化分析-m3-stage3b` on `feat/m3-mechanism-validation-mvp` at
   `b7c8bec`, clean; M2 worktree `D:\量化分析` protected at `241c180`, dirty, untouched; `stash@{0}`
   preserved; no `data/research.duckdb` in the isolated worktree.
3. Re-read the North-Star docs, Stage 3A/3B/3B-R1 contracts, R1 acceptance/record, existing mechanism
   source and tests; re-verified the frozen Stage 3A and Stage 3B v1 SHA-256 values unchanged and
   computed the Stage 3B-R1 frozen SHA-256 values.
4. Probed the acquisition environment with bounded, holdout-safe requests:
   - EIA keyless `RBRTEd.htm` returns full history through 2026 and ignores `data=` params
     (`REJECT_SOURCE_PATH_FOR_SEALED_HOLDOUT`); it contains no bounded form/date-selector.
   - EIA Open Data API v2 requires an API key (`API_KEY_MISSING` 403); no key in the environment.
   - FRED (stlouisfed.org) is unreachable (connection reset / timeout) from this environment.
   - Shenwan SWS `index_publish/trend/` endpoint ignores start/end/begin date params and returns the
     full daily series (1999 → 2026-08-14) for `801016`/`801960`
     (`INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN`).
   - Conclusion: no bounded, holdout-safe acquisition path exists for either Tier-1 control here.
5. Created the Goal contract and this work record (record-first).
6. Frozen the oil timing supersession and oil contract v2
   (`reports/m3_stage3br2_oil_timing_resolution_v1.json`, `reports/m3_stage3br2_oil_contract_v2.json`).
7. Implemented `src/ashare_research/mechanism/oil.py` (strictly-prior Brent alignment, staleness gate,
   EIA/FRED source-consistency), `industry.py` (Shenwan regime/return construction), and
   `alignment.py` (joint Tier-1 readiness, coverage only).
8. Added Stage 3B-R1 frozen-hash verification to `contracts.py` and added `oil.py`/`industry.py`/
   `alignment.py` to the Stage 3A package-guard allowed set.
9. Implemented `src/ashare_research/tools/m3_stage3br2_data.py` (bounded acquisition probes that fail
   closed with precise codes, offline normalize/align, and report generation).
10. Ran `acquire-oil` and `acquire-industry` (both report NOT_ACQUIRED with the exact codes) and
    generated the four status reports (source registry, development input manifest, data coverage,
    tier-1 readiness) reflecting the honest `NOT_ACQUIRED`/`GAP` state.
11. Added the focused Stage 3B-R2 test suite (tests/test_m3_stage3br2_tier1_inputs.py, 31 tests).
12. Ran ruff, compileall, focused tests, and Stage 3A/3B/3B-R1 boundary tests; all green.
13. Wrote the acceptance document and this work-record closeout.

## Validation

- Focused Stage 3B-R2 tests: 31 passed.
- Stage 3A + Stage 3B v1 + Stage 3B-R1 boundary tests: 52 passed.
- `ruff check src/ tests/`: PASS. `python -m compileall -q src tests`: PASS.
  `git diff --check`: PASS.
- All 6 Stage 3B-R2 reports parse; no restricted research outputs; holdout sealed; no real 2023+
  data (only the declared `holdout_start` boundary constant shared with frozen Stage 3B v1).
- Frozen Stage 3A (3) / Stage 3B v1 (5) / Stage 3B-R1 (5) SHA-256: unchanged.
- Full `pytest -q` (with worktree `src` on `PYTHONPATH`): PASS (see final counts).
- Protected state: branch `feat/m3-mechanism-validation-mvp`; `stash@{0}` preserved; no
  `data/research.duckdb`; M2 worktree untouched.

## Result

- **Verdict:** `M3_STAGE3BR2_PRE_OUTCOME_TIER1_DATA_CLOSEOUT_ACCEPTED` (input-gap outcome).
  Decision set: `M3_STAGE3BR2_OIL_INPUT_GAP`, `M3_STAGE3BR2_INDUSTRY_INPUT_GAP`,
  `M3_TIER1_DEVELOPMENT_INPUTS_NOT_READY`, `M3_HOLDOUT_REMAINS_SEALED`, `M3_STAGE3C_NOT_ALLOWED`,
  `STOP_FOR_NORTH_STAR_REVIEW`.
- **implementation**: PASS (pre-outcome timing supersession, oil/industry/alignment modules, bounded
  acquisition CLI, offline tests green).
- **data**: NOT TRUSTED — oil and petrochemical_industry are `NOT_ACQUIRED` because no bounded,
  holdout-safe acquisition path is provable in this environment; the joint Tier-1 date set is
  `NOT_READY`.
- **research result**: NOT EXECUTED — no PetroChina mechanism/outcome statistic was computed.
- Completed: oil timing supersession (formal, pre-outcome); oil v2 contract; oil/industry/alignment
  modules; bounded acquisition CLI; source registry + manifest + coverage + readiness reports;
  frozen Stage 3A/3B-v1/3B-R1 artifacts byte-unchanged; focused + full + boundary test suites green.

## Outstanding issues

- Oil (Brent) and Shenwan industry have no bounded, holdout-safe acquisition path in this
  environment (EIA keyless is unbounded, EIA API v2 needs an unavailable key, FRED is unreachable,
  and the SWS endpoint ignores date bounds). Tier-1 inputs remain NOT READY until a bounded path is
  proven: an EIA API key, a reachable FRED bounded transport, or a verified development-only
  immutable source capsule.
- The 7-day oil staleness gate and the joint Tier-1 readiness table are implemented and tested but
  not yet populated with real development data.

## Next steps

- North-Star review of the input-gap verdict; establish a bounded Brent and Shenwan acquisition path.
- Once a bounded path is proven, run the acquisition + offline normalize + align pipeline and refresh
  the Stage 3B-R2 readiness reports.
- Stage 3C remains NOT ALLOWED until Tier-1 inputs are TRUSTED.

## Final file changes

- New: `reports/m3_stage3br2_oil_timing_resolution_v1.json`,
  `reports/m3_stage3br2_oil_contract_v2.json`, `reports/m3_stage3br2_source_registry_v1.json`,
  `reports/m3_stage3br2_development_input_manifest_v1.json`,
  `reports/m3_stage3br2_data_coverage_v1.json`,
  `reports/m3_stage3br2_tier1_readiness_v1.json`,
  `src/ashare_research/mechanism/oil.py`, `src/ashare_research/mechanism/industry.py`,
  `src/ashare_research/mechanism/alignment.py`,
  `src/ashare_research/tools/m3_stage3br2_data.py`,
  `tests/test_m3_stage3br2_tier1_inputs.py`,
  `acceptance/m3_stage3br2_oil_industry_acquisition_and_alignment.md`,
  `agent/goals/2026-08-15_m3_stage3br2_oil_industry_acquisition_and_alignment.md`,
  `agent/record/2026-08-15_Stage3BR2_oil_industry_acquisition_and_alignment.md`.
- Modified: `README.md` (Stage 3B-R2 status), `src/ashare_research/mechanism/contracts.py`
  (Stage 3B-R1 frozen hashes), `tests/test_m3_stage3a_mechanism_preflight.py` (package guard includes
  oil/industry/alignment).

## Final Git state

- Branch: `feat/m3-mechanism-validation-mvp`
- Commits (4, pushed to origin): contract/resolution supersession (`41572a1`); implementation
  (`5bf3710`); tests/acceptance (`e1ca4bb`); README wording fix (`a49608e`).
- The first final-tip CI(a) `31877611609` failed on the Ubuntu (and expected Windows) "Full offline
  test suite" because the README Stage 3B-R2 rewrite split the contiguous phrase `No real mechanism
  inference` across a line break, breaking the M2 closeout wording test
  `test_m2_stage2j_conditional_closeout.py`. Fixed by keeping the phrase on one line; the M2 closeout
  test passes locally (13 passed). Re-pushed as `a49608e`, new CI run `31877883936`.
- Working tree clean; protected `stash@{0}` preserved; no `data/research.duckdb`.
- Original M2 worktree untouched; no PR, no merge, no force push, no Stage 3C, no holdout read.