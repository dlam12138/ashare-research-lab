# Canonical M2 explicit-gap ledger

Contract: `m2_explicit_gap_ledger_v1`

As of: `2026-08-04`

Status: `current`

This ledger consolidates current Stage 2F, Stage 2H, and Stage 2I gaps without
replacing or deleting their source ledgers. Counts are recomputed from source
selectors by the Stage 2J validator; the current result is 9 dividend + 2 risk
veto + 7 ROIC = 18 unique current gaps.

## Stage 2F dividend evidence

| Gap ID | Period | Source record | Missing reason | Recoverability |
|---|---|---|---|---|
| `M2G-DIV-001` | 2021 interim | `2021-interim-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-002` | 2021 final | `2021-final-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-003` | 2022 interim | `2022-interim-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-004` | 2022 final | `2022-final-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-005` | 2023 interim | `2023-interim-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-006` | 2023 final | `2023-final-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-007` | 2024 final | `2024-final-exchange` | Exact SSE payload challenged; issuer-only | `finite_new_official_source_available` |
| `M2G-DIV-008` | 2025 interim | `2025-interim-exchange` | Exact SSE payload challenged; latest yield inputs missing | `finite_new_official_source_available` |
| `M2G-DIV-009` | 2025 final | `2025-final-exchange` | Exact SSE payload challenged; latest yield inputs missing | `finite_new_official_source_available` |

Allowed future action is exact exchange-official payload verification. Issuer
copies, designated platforms, locator hashes, anti-bot bytes, mirrors,
translations, and zero fills cannot satisfy Rule007.

## Stage 2H risk-veto evidence

| Gap ID | Risk slot | Source record | Missing reason | Recoverability |
|---|---|---|---|---|
| `M2G-RISK-001` | Formal regulatory investigation or major discipline | `pc-search-regulatory-v2` | Historical CSRC/SSE result pagination was not fully retrievable | `finite_new_official_source_available` |
| `M2G-RISK-002` | Fund occupation or related guarantee | `pc-search-fund-occupation-v2` | Historical discipline universe was not fully retrievable beyond annual reports | `finite_new_official_source_available` |

Both remain `missing_evidence`, not negative conclusions. General search
results, incomplete pagination, ordinary balances, or absence inference are
prohibited fallbacks.

## Stage 2I ROIC evidence

| Gap ID | Acquisition / role / FY | Search record | Missing reason | Recoverability |
|---|---|---|---|---|
| `M2G-ROIC-001` | `A-2024-operating-tax` / operating tax / 2024 | `stage2i2r-search-01` | No direct operating-tax allocation | `not_separately_publicly_disclosed` |
| `M2G-ROIC-002` | associate investment / 2023 | `stage2i2r-search-02` | Complete associate/JV residual is combined | `requires_methodology_relaxation` |
| `M2G-ROIC-003` | associate investment / 2024 | `stage2i2r-search-03` | Complete associate/JV residual is combined | `requires_methodology_relaxation` |
| `M2G-ROIC-004` | joint-venture investment / 2023 | `stage2i2r-search-04` | Complete associate/JV residual is combined | `requires_methodology_relaxation` |
| `M2G-ROIC-005` | joint-venture investment / 2024 | `stage2i2r-search-05` | Complete associate/JV residual is combined | `requires_methodology_relaxation` |
| `M2G-ROIC-006` | non-operating financial assets / 2023 | `stage2i2r-search-06` | No official purpose and linked-income proof | `requires_methodology_relaxation` |
| `M2G-ROIC-007` | non-operating financial assets / 2024 | `stage2i2r-search-07` | No official purpose and linked-income proof | `requires_methodology_relaxation` |

No tax proxy, residual associate/JV split, unsupported non-operating-asset or
all-cash deduction, manual plug, scope weakening, or zero fill is allowed.

## Consequences

- No current gap blocks conditional M2 closeout when it remains canonical,
  traceable, score-ineligible, and non-zero-filled.
- All current gaps block scoring.
- They do not block a separate M3 North-Star preflight, but that permission does
  not start M3 implementation.
- ROIC remains `not_computable_under_strict_evidence_contract`; no numeric ROIC
  or performance conclusion follows from these gaps.
