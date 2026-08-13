# PE Cycle Context — Normalized Earnings Method Review

M2 Stage 2K.1R4F.2 — method preflight / evidence inventory (non-scoring)

## 1. Problem definition (frozen this stage)

This stage is **not** "is PetroChina at a cycle peak right now?" and it is
**not** "how do we give PE a score again?".

The formal question answered here is:

> For a cycle-sensitive issuer, what deterministic, PIT-safe
> normalized-earnings contract is sufficient to prevent a current low PE
> from mechanically receiving a high valuation score when current earnings
> are above sustainable / mid-cycle earnings?

This stage deliberately produces **no** investment conclusion of the form
`cycle_peak = true/false`, and no `cheap / undervalued / overvalued /
buy/sell / target price` output.  It only decides *whether a normalization
method is eligible to become the basis of a future PE cycle-context guard*.

## 2. References reviewed

### A. CFA Institute market-based valuation

- Borrowed: for cyclical companies, valuation should rest on **normalized
  earnings**, not trailing peak earnings; two canonical forms are reviewed
  here — (1) historical average EPS over a full cycle, and (2) average ROE
  applied to current book value per share.
- Borrowed: trailing fundamentals must be **PIT-lagged** — never read a
  future restatement back into an earlier as-of date.
- Not copied: analyst forecasts, forward EPS, consensus estimates, peer
  comparables, and any production recommendation are all out of scope.

### B. Damodaran — cyclical / commodity normalization

- Borrowed: averaging absolute earnings across a cycle distorts when the
  firm's scale (equity base, revenue) changes over time; a **relative**
  normalization (ROE on current book value) dampens that scale distortion.
- Borrowed: historical margins are a legitimate *diagnostic* of normal
  profitability, not a standalone valuation input.
- Not copied: no subjective "normal oil price", no DCF, no oil-futures-based
  earnings projection, and no sector averages (peer acquisition is not
  authorized this stage).

### C. MADR

- Borrowed: only its decision-documentation shape — Context, Decision
  Drivers, Considered Options, Decision Outcome, Consequences,
  Confirmation.  No MADR package/tooling is introduced.

## 3. Repository-specific cuts

- PIT visibility decided by `available_at <= as_of` **and**
  `effective_from <= as_of`; array order never decides visibility.
- Restatement resolution: latest visible `effective_from` wins; ties broken
  deterministically via `supersedes_fact_id`; an ambiguous tie **fails
  closed** (`NOT_TRUSTED_RESTATEMENT_AMBIGUITY`).
- Share scope: company-wide ordinary shares (A+H, constant 183,020,977,818,
  proof `r4d1-share-continuity-constancy-v1`); A-share-only denominators are
  rejected (Section 十五).
- All arithmetic `Decimal(str(...))`; no binary-float identity; no
  round-before-aggregation.
- No trimming / winsorizing / excluding "bad years" this stage — the
  average is a plain arithmetic mean over eligible observations, with a
  pre-frozen accounting-quality exclusion only (missing opening equity,
  nonpositive equity, nonpositive parent NP).

## 4. Observed history (from the committed fact bundles)

- Annual parent net profit / revenue / parent equity / basic EPS:
  **2020–2025** (`petrochina_pit_denominator_reported_fact_bundle_v1`,
  exchange_official tier).
- 2020 ROE is not eligible (no 2019-12-31 opening equity in-repo) →
  consecutive annual ROE observations: **2021–2025 = 5**.
- `full_cycle_coverage_status = NOT_PROVEN`: five fiscal years of data do
  not automatically equal one complete oil/earnings cycle, and no
  independent deterministic evidence in-repo proves full-cycle coverage.

## 5. Method option matrix (frozen conclusions)

| Option | Conclusion | Rationale (frozen) |
|---|---|---|
| A. CURRENT_PE_WITH_BINARY_PEAK_FLAG | **REJECT** | threshold arbitrary; single-period YoY cannot define a cycle; structural growth easily misread as a peak; not a mainstream normalized-earnings method |
| B. HISTORICAL_AVERAGE_EPS_FULL_CYCLE | **CONDITIONAL** — `BLOCKED_FULL_CYCLE_NOT_PROVEN` today | CFA-recognized; eligible only with `full_cycle_proven`; a plain 5y average must never be presented as a full-cycle average |
| C. AVERAGE_ROE_X_CURRENT_BVPS | **PRIMARY PROTOTYPE CANDIDATE** — `ELIGIBLE_FOR_PROTOTYPE` | CFA-recognized; relative normalization resists scale drift; deterministic from committed facts |
| D. NORMALIZED_MARGIN_X_CURRENT_REVENUE | **INDEPENDENT_DIAGNOSTIC** | margin normalization handles scale, but segment mix / tax / leverage / cost structure can shift; cross-check only, never the primary PE denominator |
| E. NORMALIZED_COMMODITY_PRICE_MODEL | **DEFER / REJECT_AS_PRIMARY** | requires choosing a "normal" oil price (injects analyst view); needs a new commodity-to-earnings model; no trusted deterministic mapping in-repo |
| F. SECTOR_AVERAGE_NORMALIZATION | **DEFER** | peer acquisition not authorized this stage |

## 6. Evidence contract frozen for the prototype (not yet scoring)

Contract id (prototype only): `pe_normalized_earnings_average_roe_v1`

Inputs (all PIT-visible, committed facts):

- annual parent net profit
- annual beginning parent equity
- annual ending parent equity
- current PIT parent equity (2026-03-31 MRQ)
- current PIT share count (2026-03-31 period-end, company-wide)

Per year (Decimal only):

```
average_equity_y = (begin_equity_y + end_equity_y) / 2
ROE_y           = parent_np_y / average_equity_y
```

`historical_average_roe` = arithmetic mean of eligible annual ROE
observations.  `current_BVPS = current PIT parent equity / current PIT
ordinary shares`.  `normalized_EPS_ROE = historical_average_roe ×
current_BVPS` — a diagnostic normalized EPS, **not** a formal scoring input.

History coverage is two separate fields:

- `history_coverage_ready` (>= 5 consecutive annual ROE observations) —
  **true** here;
- `full_cycle_proven` (independent deterministic evidence of a full cycle)
  — **false** here.

So `history_coverage_ready=true, full_cycle_proven=false` is a legal,
recorded state.  With fewer than 5 consecutive years the method would be
`BLOCKED_INSUFFICIENT_HISTORY`.

## 7. Why this stage does not unblock PE scoring

Even though `AVERAGE_ROE_X_CURRENT_BVPS` is computable today, this stage
leaves `pe_numeric_scoring_authorized = false` untouched.  This stage can
only demonstrate that the normalization method and input chain are suitable
to enter a prototype.  The next stage must still verify:

- PIT historical reconstruction;
- normalized-earnings identity;
- the normalized-PE definition;
- current vs historical behavior;
- deterministic A/B comparison;
- sensitivity;
- whether the peak/low-PE inversion is really removed.

**METHOD READY ≠ SCORING READY.**

## 8. Decision

`PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED` (PASS) — the
ROE-normalization evidence chain is eligible for a **prototype** stage;
PE numeric scoring remains blocked, and no production / overall score is
authorized.

## 9. Not produced this stage

- PE numeric score — **NO**
- valuation dimension numeric score — **NO**
- production score / overall score / recommendation / target price — **NO**
- registry v3 / policy v3 / shadow v7 / sensitivity v9 — **NO**
- any modification to registry v2 / policy v2 / shadow inputs v2 /
  capsule v5 / shadow v6 / sensitivity v8 — **NO**
- any arbitrary peak threshold (1.2 / 1.5 / 80th percentile) — **NO**
- `>1` described as "cycle peak" — **NO** (a pure math relation only)
