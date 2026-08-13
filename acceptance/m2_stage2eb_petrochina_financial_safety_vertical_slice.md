# M2 Stage 2E-B：PetroChina 2021—2025 Financial Safety Vertical Slice

## Acceptance result

The offline vertical slice is accepted when the targeted and full test gates,
static checks, and repository invariants pass together. The runner emits no
interest coverage, ROIC, scoring, grade, or investment-advice output.

## Contract

- Rule 006 is additive and directly reconciles the six base safety concepts
  plus `current_portion_of_long_term_borrowings`,
  `current_portion_of_bonds_payable`, and
  `current_portion_of_lease_liabilities`. The aggregate
  `current_portion_of_interest_bearing_non_current_liabilities` is derived
  only by `DERIVE_INTEREST_BEARING_CURRENT_PORTION_001 v1`.
- Evidence is dual-source, CAS, consolidated, instant, and normalized to 万元.
- The five annual report dates are replayed through `AsOfQuery.get_latest_available()`.
- Four metrics are descriptive-only (`score_eligible=false`) and bind their
  declared direct input roles without substitution.
- Zero debt coverage is `undefined_no_debt`; a negative debt component is
  `not_comparable_negative_debt_component`; missing roles are `missing_input`.
- No synthetic average balance Fact, interest coverage metric, ROIC, or score is
  generated.
- The statement aggregate is retained as rejected audit evidence and never as
  an eligible canonical Fact. Each derived current-portion Fact has exactly
  three reconciled component input IDs and one derivation lineage row.

## Expected observed counts

The runner validates these from the rebuilt run-scoped stores and does not
hard-code production metric values:

- Facts: `contexts=11`, `facts=354`, `raw=232`, `reconciled=122`,
  `fact_links=58`, `lineage=354`, `audit=354`.
- Financial safety: `definitions=4`, `results=25`, `computed=25`,
  `insufficient=0`, `links=5`, `lineage=116`, `final_latest=20`,
  `final_computed=20`.
- Combined: `definitions=16`, `results=102`, `computed=98`, `insufficient=4`,
  `links=22`, `lineage=280`, `final_latest=80`, `final_computed=76`.
- Metric PIT latest: `0/16/32/48/64/80`.
- Metric PIT computed: `0/12/28/44/60/76`.
- Metric PIT historical insufficient: `0/4/4/4/4/4`.

The four revised canonical direct facts are FY2022 total liabilities and FY2023
total liabilities, full lease liabilities, and current lease component. The
old FY2023 current-portion aggregate change remains rejected audit evidence.
Its derived current-portion v1→v2 chain is expected; unchanged years must not
receive a fake version. All five annual debt-composition proof statuses are
`proven` from dual-source note components and an aggregate-plus-excluded-row
tie-out.

## Evidence and invariants

The implementation uses only the committed evidence JSON contracts during the
formal run. Cached PDFs were used only for preflight evidence verification and
are not read by the runner. Stage 2D-B/C/D/E artifacts, Rule 001—005 behavior,
the frozen 201-Fact foundation, prior 77 Metric Result IDs and semantics, the
default database, and stash are preserved. The final repository check also
requires no DB/PDF/PNG artifacts to enter the change set and a clean worktree.
