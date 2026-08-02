# Rule007 source-pair contract v3

Rule007 metric eligibility is exact: one independently extracted
`issuer_official` source plus one independently extracted `exchange_official`
source with exact locators, real content hashes, compatible scope/currency and
matching values. `designated_disclosure_platform` is never the exchange side.

| Evidence state | Pair | Rule007 eligible | Metric input | Note |
|---|---|---:|---:|---|
| `issuer_exchange_rule007_eligible` | issuer + exchange | yes | yes | exact eligible pair |
| `issuer_plus_designated_platform_verified` | issuer + designated platform | no | no | designated platform is separate evidence |
| `exchange_plus_designated_platform_verified` | exchange + designated platform | no | no | not an independent issuer/exchange pair |
| `designated_platform_only` | designated platform only | no | no | evidence gap |
| `issuer_only` | issuer only | no | no | missing exchange official |
| `exchange_only` | exchange only | no | no | missing issuer official |

The declarative mapping lives in
`ashare_research.reproducibility.rule007.RULE007_PAIR_REGISTRY`. Candidate
records are all validated, sorted by announcement date, announcement identity
and evidence ID, and recorded as selected or rejected. Equal-content duplicates
are deterministic; contradictory candidates are a hard error. Same-content PDF
mirrors remain recorded but cannot be represented as independent compilations.

Raw Facts retain their own source payload values and source IDs. Reconciled
Facts reference exactly the two eligible raw Fact IDs. Event-ledger values are
cross-checks only.
