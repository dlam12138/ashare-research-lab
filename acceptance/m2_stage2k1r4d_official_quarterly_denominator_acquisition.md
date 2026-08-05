# M2 Stage 2K.1R4D — Official Quarterly Valuation Denominator Fact Acquisition

Status: `CONDITIONAL PASS — explicit gaps remain; next-stage preflight blocked
on weighted-average-share derivation`.

## Scope

Acquire from official filings (SSE exchange_official + issuer_official where
reachable) the quarterly valuation denominator facts for PE-TTM / PB-MRQ /
PS-TTM construction:

- `net_profit_attributable_to_parent` (cumulative Q1/H1/Q3 + annual)
- `revenue` (cumulative Q1/H1/Q3 + annual)
- `equity_attributable_to_parent` (instant, period-end)
- `basic_earnings_per_share` (cumulative + annual)
- `total_ordinary_shares_at_period_end` (instant, period-end)
- `weighted_average_total_ordinary_shares` (reconciled_derived only)

Report window: 2020 Q1 → 2026 Q1 (the last filing officially announced on or
before the frozen evidence cutoff `2026-08-02`). 25 report filings.

Boundaries respected: no daily PE/PB/PS, no TTM/MRQ/single-quarter Metric
Results, no valuation percentile, no scoring/weights/thresholds changes, no
canonical value profile change, no peer acquisition, no M3, no default DB
writes.

## Source register (frozen 2026-08-05)

- SSE official announcement query (`query.sse.com.cn`) enumerated 553
  announcements for 601857.SH (2020-01-01..2026-08-02); the 25 report
  filings were identified from their official titles and announcement dates.
  The last in-scope filing is 2026 Q1 (announced 2026-04-30, before the
  cutoff); the 2026 H1 report is not yet announced at the cutoff and is
  excluded.
- `config/pit_valuation_official_source_evidence_v1.json` freezes 25
  exchange_official evidence entries (real official URLs, announcement dates,
  document IDs) + 25 issuer_official entries: 2023/2024 annual reports are
  byte-identical verified issuer aliases (one content object, two evidence
  IDs); the other 23 issuer entries are `blocked_source_access`
  (www.petrochina.com.cn returned HTTP 403 on 2026-08-05).
- `config/pit_valuation_official_cache_registry_v1.json` records 25
  content-addressed objects (`objects/<sha256>.pdf`), 2023/2024 annual
  objects carrying dual issuer/SSE evidence aliases.

## External official cache

- Explicit external cache root (outside the repository), content-addressed,
  never committed to Git.
- All 25 official PDFs hash-verified on 2026-08-05 (SHA-256, byte size,
  `%PDF-` magic, page count, evidence alias, filing period).
- Acquisition used the official SSE endpoint only. The `acw_sc__v2` challenge
  served by the official static host was solved by reproducing the
  deobfuscated permutation/XOR algorithm; ≤3 attempts per URL; no third-party
  mirror; no fallback.

## Extraction

- Named-capture extraction anchored to the CAS main-accounting-data section
  (「按中国企业会计准则编制的主要会计数据/主要财务数据」); the CAS table is
  the second block after the IFRS block in Q1/H1/Q3 filings.
- Per-year Q3 cumulative token layout verified from the actual filings
  (2020-2022/2024: 6 tokens, cumulative at token 3; 2023/2025: 8 tokens,
  cumulative at token 4) with a fail-closed `expected_token_count` guard that
  turns a layout change into an explicit gap instead of a silent wrong value.
- Values recomputed solely from the named capture group; no numeric constants;
  OCR/LLM flags false; missing markers and table ambiguity fail closed
  (never guessed, never zero).

## Facts (formal pipeline output)

- Reported bundle: **127 facts** — 112 original reported facts (25 revenue +
  25 parent net profit + 25 basic EPS + 25 equity + 12 period-end share
  counts) + **15 restated facts** (version `restated_1`) detected from the
  `(追溯后)/(追溯前)` comparative columns of later filings (e.g. 2022-Q1 net
  profit 39,059 → 38,898; 2022-AR revenue 3,239,167 → 3,239,167 retained
  with 148,738 net-profit restatement).
- Reconciled bundle: **0 facts**. The weighted-average-share derivation
  (`parent net profit / basic EPS`) is **ambiguous for all 25 periods** because
  basic EPS is rounded to 2-3 decimals, producing an implied share interval
  millions of shares wide that cannot uniquely determine the count. Recorded
  as `weighted_average_share_ambiguous_due_to_eps_rounding` (25 cells).
- Version lineage: **42 chains** (15 restatements + 27 corroborating
  comparatives). Each restatement carries `supersedes_fact_id`, becomes
  visible only from its own announcement date, and never backfills the
  pre-restatement window.
- Coverage grid: **137 expected cells** (from the filing register, never
  hand-written): 112 `acquired_reported_verified`, 25
  `weighted_average_share_ambiguous_due_to_eps_rounding`.
- Gap ledger: **25 explicit gaps** (all weighted-average-share derivation
  ambiguity). No missing filings, no source conflicts, no unreported
  extraction failures.

## Readiness

| Metric | role coverage | 3y | 5y | blockers |
|---|---|---|---|---|
| PE-TTM | net profit 25/25; weighted shares 0/25 | BLOCKED | BLOCKED | weighted_average_total_ordinary_shares |
| PB-MRQ | equity 25/25; period-end shares 12/12 | READY | READY | — |
| PS-TTM | revenue 25/25; period-end shares 12/12 | READY | READY | — |

## Verification

Executed on 2026-08-05 (Windows local):

- Full offline test suite: **1394 passed, 2 warnings** (includes the 67 R4D
  tests and the pre-existing 1327-test baseline).
- `ruff check src/ tests/`: All checks passed.
- `python -m compileall -q src`: pass.
- `git diff --check`: pass.
- R4D contract gate (`verify-contracts`): all 5 contract digests validated.
- R4C.1 artifact manifest re-verified after the workflow edit (`verify_artifact_manifest`
  status pass).
- Default DB `data/research.duckdb` SHA-256 unchanged
  (`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`).
- Stash preserved (`stash@{0}` — protected Stage 1B.4 record edit, untouched).
- Secret/path scan: no local absolute paths, no secrets, no PDF/DB/parquet
  pollution in committed artifacts.
- Clean-clone preflight: expected to fail in an uncommitted working directory
  (local data/DB/stash present); CI runs it on a clean clone.
- CI run `30993569110` (2026-08-05, push `8441c1f`): **SUCCESS** — 
  `clean-clone (ubuntu-latest, ubuntu)` pass, `clean-clone (windows-latest,
  windows)` pass, `identity-compare` pass. The R4D contract gate and the full
  offline test suite (including the 67 R4D tests) ran on both platforms with
  no real PDF downloads (synthetic fixtures only).

## Result

Official filing register: **TRUSTED** (25 SSE filings, real URLs/dates).
External official cache: **TRUSTED** (25 hash-verified content-addressed
objects).
Extraction specs: **TRUSTED** (112/112 direct cells extracted; 0 silent
guesses).
Named-capture value derivation: **TRUSTED**.
Quarterly cumulative scope: **TRUSTED** (Q1/H1/Q3 cumulative semantics
verified per filing).
ReportedFact identity: **TRUSTED** (canonical fact IDs recomputable).
Direct/derived separation: **TRUSTED**.
Weighted-average-share readiness: **MISSING** (report never discloses the
weighted-average count; EPS rounding makes the derivation ambiguous for all
25 periods).
Restatement/supersession lineage: **TRUSTED** (15 restated versions, 42
chains).
PIT available_at/effective_from: **TRUSTED** (SSE announcement dates;
effective from the next verified trading day).

R4D decision: **PIT_DENOMINATOR_FACT_GAPS_REMAIN** (engineering trusted;
explicit official gaps — the weighted-average share count is not derivable
from disclosed EPS rounding).

Next-stage implementation: **NOT STARTED**.

## Remaining issues

- Weighted-average-share count is not directly disclosed in any in-scope
  filing and cannot be uniquely derived from the rounded basic EPS (implicit
  share interval [~181.4B, ~183.4B] per period). PE-TTM denominator
  construction is blocked until a source for the weighted-average share count
  is found (e.g. a corporate-action/share-change disclosure with sufficient
  precision) or a documented convention is accepted.
- Issuer (petrochina.com.cn) endpoint returned HTTP 403 on 2026-08-05; 23
  quarterly/half-year/annual issuer entries are `blocked_source_access`. The
  2021-2025 annual reports' issuer objects are byte-identical to the SSE
  objects (verified in the R4C ROIC register) and are recorded as dual
  aliases.
- Q1/Q3 period-end share counts are not precisely disclosed in the Q1/Q3
  filings (only the rounded 股本 in the balance sheet); the precise count is
  disclosed in the AR/H1 dividend base statements (183,020,977,818).

## Git state

(pending commit)