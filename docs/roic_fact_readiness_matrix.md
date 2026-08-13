# PetroChina ROIC Fact-Readiness Matrix

This file defines the deterministic audit dimensions. The generated FY2020–FY2025
matrix is `reports/petrochina_roic_fact_readiness_2020_2025_v2.md` and its
machine-readable counterpart is
`reports/petrochina_roic_fact_readiness_2020_2025_v2.json`.

Each row must retain:

- analytical role and exact canonical concept ID;
- annual-report statement/note locator and source type;
- period type, scope, unit/currency;
- coverage for FY2020–FY2025;
- canonical Fact IDs and Context IDs where present;
- `available_at`, fact version, restatement/supersedes chain;
- verification status and whether the row is already present, derivable or
  acquisition required;
- methodology choice versus missing fact;
- missing reason and blocker severity.

## Status vocabulary

`ready`, `partially_ready`, `missing_official_fact`, `scope_mismatch`,
`period_mismatch`, `PIT_unavailable`, `restatement_unresolved`,
`methodology_unresolved`, `not_applicable`.

An approximate or nearby concept remains not ready. A methodology choice is not
reported as a missing official fact, and a missing official fact is not hidden
as a methodology choice.

## Candidate evidence gate

The primary operating-profit bridge is eligible for a shadow feasibility run only
if its selected year has all required numerator/adjustment/tax inputs, opening
and closing financing-view inputs, explicit scope matching, and PIT/version
lineage. Otherwise the runner must report `shadow_not_computable` with the exact
blockers and must not create a production Metric Result.
