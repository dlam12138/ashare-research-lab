# PetroChina post-dividend North Star review

Date: 2026-08-01
Scope: Stage 2G valuation profile only; no ROIC, scoring, Web, or market-mechanism work.

## Decision

Valuation is the next permitted vertical slice after dividend correction. The five-year base already contains quality/cash-flow evidence, ROE/ROA, financial safety, and corrected dividend announcement/payment evidence. A PIT valuation layer answers how the observed market price relates to the latest information available at each trade date and makes comparability limits visible.

ROIC remains deferred because NOPAT and invested-capital definitions require unresolved operating-lease, minority-interest, and capital-base choices. Daily market-mechanism work remains later because it should consume an established value profile rather than substitute for one. No numeric weighting or ranking is introduced by this review.

## Protected boundaries

- Identity, `available_at`, period, and evidence gates remain authoritative.
- Dividend implementation announcement and payment are separate dates and separate metrics.
- The existing `stock_daily` model is reused; this stage does not create a parallel canonical market model.
- A-share price times combined A/H ordinary shares is never called canonical market capitalization. Any diagnostic is named `a_share_price_implied_total_ordinary_equity_value`.
- Missing or partial evidence is disclosed and is never converted to zero.

## Mature references reviewed

| Reference | Borrowed design | Why applicable | Not copied | Repository-specific cut |
|---|---|---|---|---|
| OpenBB provider architecture | provider → mapping → normalized model | separates acquisition from canonical fields | provider breadth and plugin surface | only existing Baostock/AKShare adapters |
| FinanceToolkit | reported inputs → derived measures | keeps valuation formulas transparent | portfolio analytics and opinion labels | six PIT observations only |
| Arelle | Fact/Context/Unit discipline | prevents period and unit leakage | full XBRL runtime | existing repository Fact identity/PIT rules |
| OpenLineage | run/input/output lineage | makes evidence and cache provenance inspectable | external lineage service | committed JSON lineage |
| Pandera / Great Expectations | declarative data checks | validates dates, units, duplicates, and ranges | framework dependency | existing test and runner assertions |

These references were reviewed against the repository North Star, prior capital-return review, and the existing financial-safety methodology. No framework is added and no existing identity or PIT rule is overridden.

## Result

Stage 2G proceeds with a transparent, PIT-safe value profile. It does not answer whether a security is cheap or expensive, does not set a target, and does not produce a trade recommendation. Percentiles are historical positions with explicit effective sample sizes only.
