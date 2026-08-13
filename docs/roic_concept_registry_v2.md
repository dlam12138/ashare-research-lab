# ROIC concept registry v2

Registry v2 is `config/roic_concept_registry_v2.json`. It explicitly inherits
the historical read-only v1 entries, applies listed migration overrides, adds
the split methodology/derivation roles, and is materialized and validated by
`roic_contracts.load_registry()`.

For every materialized role, formula membership, contribution, acquisition
behavior, parent inclusion, derivation components and decision linkage come
from the dependency graph. Registry validation rejects primary/secondary
overlap, component double contribution, sign drift, direct acquisition of a
derivation or methodology choice, and missing graph roles.

## Migration

The v1 registry remains unchanged as historical evidence. Its mixed
`invested_capital.non_operating_asset_boundary` role is retained in v2 only as
an excluded, not-applicable migration tombstone. It is replaced by:

- `policy.non_operating_asset_classification` — resolved methodology choice,
  no amount or unit, never acquired as a Fact;
- `invested_capital.qualifying_non_operating_assets` — monetary deterministic
  derivation from classified canonical Facts, never directly acquired.

The v1 direct `nopat.finance_cost_adjustment` role becomes a deterministic
composite. The new direct component
`nopat.finance_cost_excluding_lease_interest` and the existing
`nopat.lease_interest_expense` must both be ready before the parent is ready.
