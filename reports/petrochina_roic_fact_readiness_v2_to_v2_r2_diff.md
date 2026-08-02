# ROIC readiness v2 → Stage 2I.1R2 corrected v2 diff

The historical v2 report at starting HEAD `7e9c04d` had 156 cells:
88 missing, 62 ready and six `not_applicable`. The corrected report has 186
cells: 106 missing, 68 ready, six partially ready and six not applicable.
Primary blocking cells change from 69 to 81 because the formula graph now
represents finance/lease composition and the non-operating-asset derivation
explicitly; secondary gaps still do not block the primary gate.

The six old `invested_capital.non_operating_asset_boundary` cells were a mixed
methodology/value role incorrectly presented as resolved/not-applicable. They
remain only as visible migration tombstones. Their replacement policy cells,
`policy.non_operating_asset_classification`, are `ready` because decision v1
has a resolved rule and digest. The separate amount cells,
`invested_capital.qualifying_non_operating_assets`, are `partially_ready`
because their canonical components are not all ready. Thus a frozen rule is
not mistaken for a ready monetary amount.

Plan v3 remains an 11-item minimum batch but replaces direct acquisition of
the finance composite and methodology choice with their actual direct
components/supporting facts. It adds lease interest, moves asset disposal to
primary A, moves other non-operating income/expense to non-blocking secondary,
and removes goodwill from the blocking batch. Validator digest:
`aedaebcaa5b85fd4bbfa39f77c2ac09a55c548cf2bb099cdc008271aa3340215`.
