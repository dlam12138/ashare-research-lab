# M2 Stage 2I.2 PetroChina minimum ROIC official-fact acquisition

Status: `SUPERSEDED BY STAGE 2I.2R`

Stage 2I.2R preserves this acceptance and all original artifacts for audit
history. Corrected capture, reconciliation, and executed-search outputs are
published under explicit `reports/*stage2i2r*` paths.

## Scope and safeguards

Stage 2I.2 executed only the 11 approved Plan v3 acquisition items for FY2024 duration, FY2023 opening and FY2024 closing. Official PDFs remain in an explicit external content-addressed cache. Formal extraction is offline and writes only an isolated canonical fact bundle/read model. The default DB, production metric registry, formula dependency graph, Plan v3 and PetroChina value profile are unchanged. No ROIC shadow, Metric Result, scoring or market-mechanism work ran.

## Official source identity and cache

Four official aliases resolve to two independently verified PDF content objects:

| FY | Official role | Document ID | Publication / PIT date | SHA-256 | Bytes | Pages |
|---:|---|---|---|---|---:|---:|
| 2023 | PetroChina issuer | `951707e943ab4b989219698aac0e29a1` | 2024-03-25 | `b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692` | 12,437,650 | 293 |
| 2023 | SSE | `601857_20240326_9CKZ` | 2024-03-26 | `b845502e533311280f89d59c2a92c67f94f2be17451e51e55f93a1d52abe6692` | 12,437,650 | 293 |
| 2024 | PetroChina issuer | `4ed3388fde7b4f4a922b2de43d6225d6` | 2025-03-30 | `15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba` | 11,167,845 | 280 |
| 2024 | SSE | `601857_20250331_9OUT` | 2025-03-31 | `15a2de01653ceefa46fdd18a02a127f434f06db02da9efb0b62c3a12a35a9bba` | 11,167,845 | 280 |

The issuer and SSE aliases happen to be byte-identical within each year; this was verified rather than assumed. During Stage 2I.2 preflight, direct re-fetches returned official edge-error pages. The exact prior official objects were therefore promoted from the independently hash-verified Stage 2H cache into the new external Stage 2I.2 cache. Formal mode has no repository-temp, Downloads, browser-cache or test-capsule fallback and re-verifies SHA-256, size, PDF signature and page count before extraction.

## Acquisition result

Plan coverage is complete: all 11 acquisition IDs and all 16 affected fact/year cells remain present. Nine cells produced trusted canonical economic facts; seven remain explicit gaps.

| Plan item | FY | Result | Raw source value/unit | Normalized `万元` | Exact CAS locator |
|---|---:|---|---|---:|---|
| `A-2024-finance-core` | 2024 | acquired | `12,552 - 5,165 = 7,387` RMB million | 738,700 | PDF 178 / printed 176, note 47 `财务费用`, exact finance-total/lease bridge |
| `A-2024-investment-income` | 2024 | acquired | 11,934 RMB million | 1,193,400 | PDF 115 / printed 113, consolidated income statement, `投资收益`, FY2024 |
| `A-2024-fair-value` | 2024 | acquired | 4,673 RMB million | 467,300 | PDF 115 / printed 113, `公允价值变动收益`, FY2024; note 50 detail reviewed |
| `A-2024-asset-disposal` | 2024 | acquired | 613 RMB million | 61,300 | PDF 115 / printed 113, `资产处置收益`, FY2024; note 53 detail reviewed |
| `A-2024-operating-tax` | 2024 | missing | no direct allocation | — | PDF 115 / printed 113 and PDF 180 / printed 178 plus full-report bounded search |
| `B-2024-lease-interest` | 2024 | acquired | 5,165 RMB million | 516,500 | PDF 178 / printed 176, note 47, `其中：租赁负债的利息支出` |
| `B-2023-2024-nci` | 2023 | acquired | 184,211 RMB million | 18,421,100 | FY2023 PDF 113 / printed 111, consolidated balance sheet, `少数股东权益` |
| `B-2023-2024-nci` | 2024 | acquired | 194,492 RMB million | 19,449,200 | FY2024 PDF 114 / printed 112, consolidated balance sheet, `少数股东权益` |
| `B-2023-2024-associate` | 2023/2024 | ambiguous scope | major associates separately disclosed; residual holdings combined with JVs | — | FY2023 PDF 158–161 / printed 156–159; FY2024 PDF 153–156 / printed 151–154 |
| `B-2023-2024-jv` | 2023/2024 | ambiguous scope | major JVs separately disclosed; residual holdings combined with associates | — | same long-term-equity note pages |
| `C-2023-2024-restricted-cash` | 2023 | acquired | 21.40 RMB 100 million | 214,000 | FY2023 PDF 154 / printed 152, note 7, USD-borrowing pledge purpose |
| `C-2023-2024-restricted-cash` | 2024 | acquired explicit absence | `无` (0) RMB 100 million | 0 | FY2024 PDF 149 / printed 147, note 7; source explicitly says no such pledged deposit |
| `C-2023-2024-non-operating-financial-assets` | 2023/2024 | missing | no exact non-operating-purpose plus linked-income proof | — | full official-report and financial-instrument/cash/investment-income bounded search |

Every extracted amount retains raw text, raw numeric string, raw sign, raw unit, Decimal normalized value, conversion multiplier, sign rule, exact page/table/row/column locator, source-excerpt hash, Context, canonical Fact Identity, source lineage, `available_at`, fact version and restatement fields. RMB million uses multiplier 100 to `万元`; `亿元` uses multiplier 10,000. Arithmetic uses Decimal precision 28 and `ROUND_HALF_EVEN`.

`finance_cost_adjustment` remains exactly `finance_cost_excluding_lease_interest + lease_interest_expense = 738,700 + 516,500 = 1,255,200 万元`; only the composite parent may enter the later formula. No tax proxy, NCI zero default, associate/JV residual, restricted-cash deduction, non-operating-asset inference, float or manual plug was created.

## PIT, versions and reconciliation

Issuer and SSE evidence reconcile by value, unit, currency, CAS consolidated scope, period and semantics. FY2023 NCI (RMB 184,211 million) and restricted cash (RMB 2,140 million / 21.40 hundred-million) are unchanged in the FY2024 comparative disclosures; those comparisons are recorded as corroboration, not artificial economic versions. No supersession edge was needed, and no cross-context, backward-time or disconnected chain was created.

## Readiness and decision

The isolated slice adds 27 source/lineage records representing nine reconciled economic facts; the protected committed inventory remains unchanged. The frozen readiness engine moves nine Plan cells to ready. Seven Plan cells remain blocking: FY2024 direct operating tax; FY2023/FY2024 complete separate associate balances; FY2023/FY2024 complete separate JV balances; and FY2023/FY2024 officially proven non-operating financial assets. Derived finance-cost composition becomes ready, but the whole evidence gate remains `BLOCKED_WITH_EXPLICIT_GAPS`.

The correct Stage 2I.2 decision is therefore:

`ROIC_FACT_GAPS_REMAIN`

Stage 2I.3 is not allowed and shadow remains not run.

## Reproducibility and engineering gates

- External cache: 2 content objects / 4 official aliases, trusted.
- Offline formal A/B: identical 12-artifact sets; artifact-set SHA-256 `363f53a2e906cadfb464a3116cc212b629daf94af67fd2d01848b6d155806de9`.
- Stage 2I/2I.1R/2I.1R2/2I.2 targeted tests: 42 passed; Fact Identity/version/restatement: 102 passed; ROE/ROA/financial-safety: 59 passed; Stage 2G/2H regressions: 47 passed.
- Main-worktree full pytest: 1009 passed, 2 pre-existing pandas warnings; Ruff, compileall and import gates passed.
- Independent clean clone at implementation HEAD `55cfabff940c762594bee99bd53dcf801c410615`: Ruff, compileall/import and full pytest passed (1009 passed, 2 pre-existing pandas warnings); a second offline formal A/B also matched all 12 artifacts.
- Implementation CI run `30774724811` passed Windows job `91567941973` and Ubuntu job `91567941984`, including static gates and the full offline suite. The report-only closeout commit is accepted only after the same two-platform workflow passes; that run is recorded in the final handoff.
- Default DB SHA-256 remained `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` from start through final local verification.
- Protected 354 Fact / 102 Metric Result / 16 definition baseline is unchanged. Inventory, Plan v3, registry and dependency-graph hashes remain `4deb1a8f...e041`, `f33e5e8a...4782`, `62399df8...f3a1` and `59f8b0dd...4d02`; the stash is unchanged and untracked `agent/goals/` remains preserved.

## Final gate

```text
M2 Stage 2I.2: CONDITIONAL PASS
Official source identity: TRUSTED
Official cache verification: TRUSTED
Plan v3 acquisition coverage: COMPLETE
Exact locator and extraction lineage: TRUSTED
Unit/sign normalization: TRUSTED
Canonical Fact/Context identity: TRUSTED
PIT/restatement lineage: TRUSTED
Finance-cost/lease composition evidence: READY
Direct operating-tax evidence: MISSING
NCI and associate/JV scope evidence: PARTIAL
Non-operating-asset supporting evidence: PARTIAL
Post-acquisition readiness: BLOCKED_WITH_EXPLICIT_GAPS
Shadow feasibility: NOT RUN
Production ROIC Metric/Result: NOT CREATED
PetroChina value profile: UNCHANGED
Stage 2I.2 decision: ROIC_FACT_GAPS_REMAIN
Scoring: STILL NOT YET
Market mechanism: NOT STARTED
Next-stage implementation: NOT STARTED
```
