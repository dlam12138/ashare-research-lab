# PIT Valuation Fact Acquisition Contract

Date: `2026-08-04`
Symbol: `601857.SH` (PetroChina)
Stage: M2 Stage 2K.1R4C (contract only — **no collection, no injection**)
Convention: `A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION` (ADR-002)

This contract freezes the scope, sources, and point-in-time rules for the next
stage's official quarterly denominator fact acquisition. It is a **plan**, not a
collection. No fact is polled, downloaded, or injected this round.

## 1. Facts to acquire

### 1.1 PE-TTM — `net_profit_attributable_to_parent`

Coverage per fact: annual report, Q1 cumulative, H1 cumulative, Q3 cumulative, original
version, restated version, filing date, and `available_at`.

TTM construction:

```text
TTM(t) = latest annual value
       + current-year latest cumulative value
       - prior-year same-period cumulative value
```

Warm-up: a 5-year valuation window starting 2021-07-31 requires quarterly cumulative
data from **2020 Q1** onward.

### 1.2 PS-TTM — `revenue`

Same coverage and TTM rule as parent net profit.

### 1.3 PB-MRQ — `equity_attributable_to_parent`

Coverage per fact: Q1 quarter-end, H1 quarter-end, Q3 quarter-end, year-end, restated
version, and `available_at`.

### 1.4 Share capital — two distinct roles

```text
total_ordinary_shares_at_period_end       # PB / PS denominator
weighted_average_total_ordinary_shares     # PE denominator
```

Each records: effective date, report period, share-change announcement, buyback
cancellation, issuance, bonus share, rights issue, other company action, and official
evidence of no change. The dividend-DPS-basis share timeline must **not** be reused as
the valuation share contract.

## 2. Source scope

Limited to official sources:

1. PetroChina quarterly report
2. PetroChina half-year report
3. PetroChina annual report
4. SSE corresponding announcement
5. Share-change and corporate-action announcements

**Not used:** commercial-terminal direct transcription, third-party daily PE/PB/PS,
LLM inference, current-share-count backfill to all history, annual-value-effective-
before-report-end, H-share price, H-share FX.

## 3. Time contract

Every fact must carry:

```text
period_start
period_end
filing_date
available_at
effective_from
restatement_version
supersedes_fact_id
source_evidence_id
```

Frozen conservative effective rule:

```text
announcement-only date -> effective from the next trading day
```

Frozen restatement rule:

```text
before restatement: use the pre-restatement visible value
after restatement:  use the restated value
never backfill a restated value into the pre-restatement historical window
```

## 4. Boundary

- No collection, download, or injection this round.
- No historical PE/PB/PS series, no valuation percentile, no `valuation_attractiveness`
  update, no scoring weights/thresholds, no peer acquisition, no M3.
- The `close_percentile` observation set remains non-production and is never a
  valuation percentile.