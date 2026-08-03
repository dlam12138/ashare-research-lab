# M2 Stage 2I.2 — PetroChina minimum ROIC official-fact acquisition

## Authoritative scope

- Contract: `agent/goals/2026-08-03_m2_stage2i2_petrochina_roic_official_fact_acquisition.md`.
- Scope is limited to the 11 approved Plan v3 acquisition items for FY2024 duration, FY2023 opening and FY2024 closing.
- This stage will not calculate shadow ROIC, mutate the production metric registry, create a ROIC Metric Result, write the default database, or alter the PetroChina value profile.

## Actual starting state

- Branch / HEAD: `feat/m2-value-assessment-mvp` / `89f4682dc4e8276d02c9d1958c09d18e2d530fe7`.
- Local, `origin/feat/m2-value-assessment-mvp`, and remote branch all resolve to the same HEAD; no intervening commits.
- Worktree: tracked files clean; only the pre-existing protected untracked `agent/goals/` directory is present.
- Stash: `stash@{0}: On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4 record edit before Stage 1C`.
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline: 354 Facts / 102 Metric Results / 16 definitions (acceptance/test baseline); default DB itself intentionally contains no production Metric tables and currently has 0 rows in `financial_facts`.
- Canonical inventory v2: 354 Facts / 122 eligible Facts / 11 Contexts; file SHA-256 `4deb1a8ff00bb0270bf4c1cddf1d8b08b05b748ffb1f99b5a1b5ddede1b1e041`; frozen snapshot digest `cb675690dd619d01534872c2bc98e9e0f6da80ff4f2ff586978d464c70fece57`.
- Plan v3 file SHA-256: `f33e5e8a2e24085e274e0ebf13d3b126092214bce916b87fd6259c26e7964782`; logical plan digest `aedaebcaa5b85fd4bbfa39f77c2ac09a55c548cf2bb099cdc008271aa3340215`.
- Registry v2 file SHA-256: `62399df8849c3b3f7b89042470c06de4a07a3788a8f2c4e503498a720e05f3a1`.
- Dependency graph v1 file SHA-256: `59f8b0dd97f311dd2a6410f271996be7fbb1448166987bd706ce399ccb7d4d02`.
- Readiness v2 file SHA-256: `7608393802e199c992d69354b2026dcada42702c2566f850c00877e876b92669`; frozen report digest `0f0bf2d53202419d871bc086c23a45513d658907e4dc3a30da755069cc0adc9d`.
- Plan v3 coverage file SHA-256: `3188ce6e6593d33ca643fb43fae81edfd7a75cb0adcbf89d652544a783b17b44`; preflight validator `PASS`, 38 blocker/year cells covered, acquisition `ALLOWED`.
- Stage 2I.1R2 acceptance: accepted with acquisition required; only Plan v3 acquisition is allowed.
- Latest remote CI at start: GitHub Actions run `30753052343` for the starting HEAD passed Ubuntu job `91510386513` and Windows job `91510386521`.

## Approved acquisition IDs

1. `A-2024-finance-core`
2. `A-2024-investment-income`
3. `A-2024-fair-value`
4. `A-2024-asset-disposal`
5. `A-2024-operating-tax`
6. `B-2024-lease-interest`
7. `B-2023-2024-nci`
8. `B-2023-2024-associate`
9. `B-2023-2024-jv`
10. `C-2023-2024-restricted-cash`
11. `C-2023-2024-non-operating-financial-assets`

## Pre-acquisition unresolved inputs and source preflight

- All 11 approved items are unresolved in the frozen readiness inventory; missing cells must remain explicit and must never become zero or plugs.
- Registered issuer and SSE annual-report URLs exist for FY2023 and FY2024. Existing Stage 2H evidence records report identical issuer/exchange content aliases for each year, but Stage 2I.2 will independently acquire and verify the official URLs and will not assume identical hashes.
- Direct operating tax and non-operating financial-asset purpose linkage are expected hard-search areas. If exact direct official evidence is absent, the affected cells will remain `missing_official_fact` and shadow will remain prohibited.

## Implementation log

### Official acquisition and offline extraction

- Created the explicit external cache `%USERPROFILE%\.codex\external-cache\ashare-research\stage2i2-petrochina-roic-v1`; no PDF, raw response or cache object is committed to the repository.
- Direct official re-fetches were bounded to three attempts and returned official edge-error payloads. The exact FY2023 and FY2024 official PDF objects were therefore promoted from the independently hash-verified Stage 2H cache, then re-verified in the Stage 2I.2 cache by content hash, byte size, PDF signature and page count.
- FY2023 object: SHA-256 `b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692`, 12,437,650 bytes, 293 pages. FY2024 object: SHA-256 `15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba`, 11,167,845 bytes, 280 pages.
- Issuer and SSE aliases were verified independently. They happen to have identical bytes within each year; identity was not assumed.
- Formal extraction ran completely offline from `objects/` and used exact CAS consolidated page/table/row/column locators. It preserved raw text/value/unit/sign, Decimal normalization and multiplier, sign policy, Context, canonical Fact Identity, source lineage, PIT availability, fact/restatement versions and supersession state.
- The isolated fact bundle contains 27 source/lineage records representing nine reconciled economic facts. No default-DB write, production registry mutation, ROIC Metric Result, shadow calculation or value-profile change occurred.

### Acquisition outcome

- All 11 approved acquisition items and all 16 affected year cells are retained in the result.
- Nine cells are acquired. Seven remain explicit blockers: FY2024 direct operating tax; complete separate associate and JV balances for FY2023/FY2024; and officially proven non-operating financial assets for FY2023/FY2024.
- `finance_cost_adjustment` is exactly `738,700 + 516,500 = 1,255,200 万元` and exists only as the composite parent for any later formula.
- Direct operating tax was not proxied; NCI was not defaulted; associate/JV residuals were not plugged; restricted cash was not treated as freely deductible; unproven financial assets remain included.
- Offline formal A/B produced identical 12-artifact sets with artifact-set SHA-256 `363f53a2e906cadfb464a3116cc212b629daf94af67fd2d01848b6d155806de9`.
- Post-acquisition readiness is `BLOCKED_WITH_EXPLICIT_GAPS`; shadow is `NOT_RUN`; decision is `ROIC_FACT_GAPS_REMAIN`.

### Verification

- Stage 2I/2I.1R/2I.1R2/2I.2 targeted suite: 42 passed.
- Fact Identity/version/restatement suite: 102 passed.
- ROE/ROA/financial-safety suite: 59 passed.
- Stage 2G/2H regression suite: 47 passed.
- Full pytest in the main worktree: 1009 passed, 2 pre-existing pandas date-parsing warnings, in 167.57 seconds.
- Independent clean clone at `55cfabff940c762594bee99bd53dcf801c410615`: Ruff passed; compileall/import passed; full pytest 1009 passed with the same 2 warnings; offline formal A/B matched all 12 artifacts.
- Default `data/research.duckdb` SHA-256 remains `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected inventory, Plan v3, registry and dependency graph match the opening hashes; the 354 Fact / 102 Metric Result / 16 definition baseline, stash and untracked goals are preserved.

### Commits, push and CI

- `b3e5c285cd7e43fdb1f98dacfacebe2b52086779` — `feat: add ROIC official-source acquisition registry`.
- `55cfabff940c762594bee99bd53dcf801c410615` — `feat: extract Plan v3 PetroChina ROIC facts`.
- Both implementation commits were pushed without force. GitHub Actions run `30774724811` passed Windows job `91567941973` and Ubuntu job `91567941984` at implementation HEAD `55cfabf`.
- The final report commit and its CI evidence are recorded in the final task handoff after the report-only push completes.

## Final Stage 2I.2 gate

`CONDITIONAL PASS` with decision `ROIC_FACT_GAPS_REMAIN`. Stage 2I.3 and shadow calculation remain prohibited.
