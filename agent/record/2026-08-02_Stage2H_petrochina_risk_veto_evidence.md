# Work record: M2 Stage 2H PetroChina governance, audit and risk-veto evidence

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `adf9e92714744738dab9ad76f9e46176a48df4b1`
- Task source: `agent/goals/2026-08-02_m2_stage2h_petrochina_risk_veto_evidence.md`
- Module: value assessment / official evidence / reproducibility

## Task objective

Implement only the bounded, official, reproducible PetroChina risk-veto evidence layer
for FY2021-FY2025 annual reports and the 2021-01-01 through 2026-07-31 event-search
period, after completing the North-Star Review and proceeding only if it is `ALLOWED`.
The work must preserve missing evidence, PIT availability, deterministic versioned IDs,
the default DB, stash, protected baselines and the existing Stage 2G.2 reproducibility
infrastructure. ROIC, scoring, Web, target price, recommendations, automatic trading
and market-mechanism work are explicitly out of scope.

## Initial verified state

- `git status --short --branch`: branch is tracking `origin/feat/m2-value-assessment-mvp`
  with only the untracked user-provided `agent/goals/` directory.
- Expected branch and actual branch match: `feat/m2-value-assessment-mvp`.
- Expected HEAD and actual HEAD match: `adf9e92714744738dab9ad76f9e46176a48df4b1`.
- Local/origin relationship: tracking refs were equal at start; remote is
  `https://github.com/dlam12138/ashare-research-lab.git`.
- Worktree: the primary worktree is `D:/量化分析`; no additional worktree was listed.
- Stash: `stash@{0}` remains present with message
  `protect pre-existing Stage 1B.4 record edit before Stage 1C`.
- Default DB: `data/research.duckdb`, SHA-256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`, 4,468,736 bytes.
- Protected baseline: `354 Fact / 102 Metric Result / 16 definitions`, as recorded by
  the Stage 2G.2R closeout and protected-baseline tests. The current DuckDB file exposes
  the legacy storage schema; its `financial_facts` table has 0 rows and is not used as a
  substitute for the protected logical baseline.
- Current test collection: `952 tests collected`.
- Current profile hashes: `reports/petrochina_value_profile.json` SHA-256
  `82276fd86fae8ab6fce551dc9caa1ee9b8dc2a03ea4ece2e69a494de5e038` and
  `reports/petrochina_value_profile_2021_2026.md` SHA-256
  `6ead3854081030c98dc5ef7c674600a3ec44a3937b36fafa5326f599f41ca393`.
- Stage 2G.2 acceptance hash:
  `089ac50f2f02dfc83a64c8ef43fe17cf79c13106389da37899286041c18e5109`.
- Latest remote CI: workflow `Stage 2G reproducibility`, run `30731336859`, HEAD
  `adf9e92714744738dab9ad76f9e46176a48df4b1`, completed with `success` on 2026-08-02.
  The documented prior failures at older commits are not the current HEAD result.
- Existing explicit gaps: Stage 2G.2R records nine finite exchange-side evidence gaps;
  the current value profile leaves `governance_risk`, `audit_risk` and
  `related_party_risk` as `not_evaluated`; no Stage 2H risk evidence layer exists yet.

## Scope

The North-Star Review, frozen risk-veto methodology/config/input contract, one official
risk-document registry and search register, evidence/event/observation contracts,
deterministic formal engine, PetroChina vertical slice, value-profile integration,
portable test capsule, acceptance record, CI/reproducibility updates and final report
are in scope only after the gate permits implementation.

## Non-goals

Do not modify the default DB, delete or alter the stash, delete or stage `agent/goals/`,
rewrite protected historical baselines, merge main, force-push, create a tag/release, or
start ROIC, scoring, Web, target-price, recommendation, automatic-trading or
market-mechanism work.

## Plan

1. Finish the mandatory repository and source/standards review and write the North-Star
   Review; stop if it is `BLOCKED`.
2. Freeze risk methodology, trigger rules and input semantics before evaluating any
   PetroChina result.
3. Acquire or register exact official evidence with true source types, real content
   hashes, bounded-search coverage, PIT `available_at` and deterministic IDs.
4. Reuse Stage 2G.2 resolver, artifact verifier, clean-clone capsule and CI machinery
   for offline formal runs, value-profile integration and tests.
5. Validate locally and remotely, review protected state, commit coherent changes and
   push only when the contract's gates are satisfied; finish with the Stage 2H report.

## Actual operations

1. Completed the mandatory North-Star Review in
   `docs/post_valuation_north_star_review.md`. The gate decision is
   **ALLOWED**. The review selects bounded risk-veto evidence as the direct next
   capability, leaves ROIC blocked for missing NOPAT/invested-capital inputs, and
   keeps market-mechanism work separate.
2. Reviewed the official CSRC/SSE disclosure, related-party, pledge, fund-occupation
   and discipline references plus Ministry of Finance audit-opinion, KAM and
   going-concern standards. Reviewed OpenBB standardization, OpenLineage object and
   dataset-facet lineage, and Arelle fact/context/unit patterns. The repository-specific
   cuts and non-copied designs are frozen in `docs/risk_veto_methodology_v1.md`.
3. Frozen `risk_veto_methodology_v1` before the formal run. The code and ledgers use
   eight risk IDs, four statuses, explicit non-trigger boundaries, project-only pledge
   thresholds, five restatement classes, and `score_eligible: false`.
4. Registered 10 exact official issuer/SSE annual-report evidence records for FY2021-
   FY2025 with true source types, exact URLs, URL locator hashes, real content hashes,
   byte sizes, page counts, announcement dates, PIT `available_at`, page/section
   locators, extraction methods and relative content-addressed cache keys. The explicit
   acquisition preflight resolved and verified 8 unique PDF objects from the external
   cache because two issuer/exchange pairs share the same content hash.
5. Created the bounded-search ledger for all eight risks. The regulator/discipline
   universe and historical fund-occupation/guarantee search remain incomplete and are
   represented as `missing_evidence`; they are not negative findings.
6. Encoded annual audit, going-concern, pledge, related-party, financing and
   comparative-version inputs. FY2022's deferred-tax standard-transition change and
   FY2023's same-control combination recast remain outside material-error risk. KAMs,
   ordinary related-party activity, controller trust-account pledge exposure and the
   2025 share-issue authorization remain separately classified.
7. Added the deterministic vertical runner
   `src/ashare_research/tools/petrochina_risk_veto_vertical_slice.py`, reusing the
   Stage 2G.2 `MarketSnapshotResolver`, artifact manifest/checksum verifier and clean-
   clone gate. Formal mode is offline, run-scoped, PIT-aware and non-publishing by
   default; the explicit publish run generated `reports/petrochina_risk_veto_report.json`.
8. Integrated the eight observations into the value profile and README, added the
   methodology document, acceptance materials, focused tests and Ubuntu/Windows CI
   gates. The final formal run was `conditional_pass`, with no observed trigger and
   exactly two `missing_evidence` observations:
   `formal_regulatory_investigation_or_major_discipline` and
   `controlling_shareholder_fund_occupation_or_related_guarantee`.
9. Verification completed locally:
   - Stage 2H focused plus Stage 2G.2 regression: `24 passed`.
   - Full offline suite: `957 passed, 2 warnings` in 165.73 seconds. Warnings are the
     pre-existing pandas date-format warnings in `tests/test_quality.py`.
   - Two independent real-input formal runs: artifact logical digest
     `f0fdfbd97b4dada30d447d6fa139ab2f7785f8fdbb63e0cce934d1fa22d6aedd`; comparison
     `pass`.
   - Two independent synthetic capsules: artifact logical digest
     `8b47e1681d7bc8f8f8ec0fdb328953689db853944365c8a114c92eefc6077dbd`; comparison
     `pass`; trigger, correction and PIT tests pass.
   - Published final formal run `petrochina_stage2h_final`: artifact logical digest
     `d12aec768955c7d8bf0ed839045a9f3b53c596822390a05f4df0931241a4f61c`, artifact
     manifest SHA `e113bcc35d79c7dc5d1af8657f92c436ab46254672b339c5df3fd10285d1bc1f`.
10. Final generated artifact hashes before commit:
    - `reports/petrochina_risk_veto_report.json`: `1f9d71a1c599729207f9a800955f1a15a9797adf8610507bf710349dac57a60f`
    - `reports/petrochina_value_profile.json`: `4cc80c677fbfc7293bd85318a88e8fc84b756ebd84bcee71ec4b2bd6d95272e6`
    - `reports/petrochina_value_profile_2021_2026.md`: `af9f55aea26d680887ed7384f4e8151edcc15aa3b175488a34c9a1d1dfca258e`
    - `docs/risk_veto_methodology_v1.md`: `ba5a5cde7f8404cfab02958ca6a176245c468a4ebb345f1b61559e02f65ec961`
    - `docs/post_valuation_north_star_review.md`: `92a4a3060470757f93eec0b3cebe66977d1987d01b3b28c35199c7a1ea5288b`

## Final result

Pending final clean-clone gate, remote Ubuntu/Windows CI, coherent commit and push.
