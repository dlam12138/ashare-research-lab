# M2 Stage 2H PetroChina Risk-Veto Evidence Acceptance

Date: 2026-08-02
Symbol: `601857.SH`
Methodology: `risk_veto_methodology_v1`
Formal as-of date: `2026-08-02`

## Verdict

**CONDITIONAL PASS — no veto trigger observed within the bounded evidence; two
explicit evidence gaps remain.**

The two gaps are `missing_evidence`, not negative conclusions:

1. The historical CSRC/SSE regulator and discipline result universe was not fully
   retrievable in the bounded search.
2. The historical fund-occupation/related-guarantee search is not fully complete
   beyond annual-report disclosures.

`score_eligible` is `false`. This report does not start ROIC, scoring, Web,
target-price, recommendation, automatic-trading or market-mechanism work.

## North-Star gate

`docs/post_valuation_north_star_review.md` records **ALLOWED**. The direct change
is bounded official risk-veto evidence for the existing PetroChina profile. The
review keeps missing evidence explicit, reuses Stage 2G.2 reproducibility
infrastructure, and leaves ROIC and market-mechanism capabilities outside this
stage.

## Frozen methodology

The eight evaluated risk IDs are:

| Risk ID | Final status |
|---|---|
| `modified_audit_opinion` | `not_observed_within_bounded_evidence` |
| `going_concern_material_uncertainty` | `not_observed_within_bounded_evidence` |
| `formal_regulatory_investigation_or_major_discipline` | `missing_evidence` |
| `material_error_restatement` | `not_observed_within_bounded_evidence` |
| `controlling_shareholder_pledge_risk` | `not_observed_within_bounded_evidence` |
| `material_related_party_transaction_risk` | `not_observed_within_bounded_evidence` |
| `controlling_shareholder_fund_occupation_or_related_guarantee` | `missing_evidence` |
| `repeated_equity_financing_or_material_dilution` | `not_observed_within_bounded_evidence` |

Frozen boundaries include: KAMs are not modified opinions; ordinary accounting-
policy and common-control restatements are not error risk; ordinary related-party
transactions are not abuse; proposed financing is not realized dilution; and
routine inquiries are not major discipline. The project pledge thresholds are
internal evidence-gate thresholds, not legal conclusions.

Every evidence/event/observation record carries a deterministic versioned contract,
source types, PIT `available_at`, extraction/classification inputs, warnings and
`score_eligible: false`. Every risk has a bounded-search register. The official
annual-report ledger contains 10 records and the cache registry resolves 8 unique
content-addressed PDF objects.

## Implementation and reuse

- `src/ashare_research/risk_veto/contracts.py` freezes validation, IDs, PIT filtering
  and trigger classification.
- `src/ashare_research/tools/petrochina_risk_veto_vertical_slice.py` provides explicit
  `acquisition-preflight`, offline formal, synthetic test-capsule, artifact verification
  and run comparison modes.
- Stage 2G.2 `MarketSnapshotResolver`, artifact manifest/checksum verifier and
  clean-clone gate are reused; no parallel resolver or artifact system is introduced.
- The value profile and Markdown report now present Stage 2H statuses without turning
  missing evidence into a negative conclusion.

Standards/design review and repository-specific cuts are recorded in
`docs/risk_veto_methodology_v1.md`, including CSRC/SSE, Ministry of Finance audit
standards, OpenBB, OpenLineage and Arelle references.

## Verification evidence

- Official cache acquisition preflight: `pass`, 8 content hashes verified, network
  not used, default DB not mutated.
- Real-input formal run: `conditional_pass`; 8 observations, 0 observed triggers,
  2 missing-evidence observations; artifact verification `pass`.
- Two real-input runs: identical logical artifact digest
  `f0fdfbd97b4dada30d447d6fa139ab2f7785f8fdbb63e0cce934d1fa22d6aedd`.
- Two synthetic capsules: identical logical artifact digest
  `8b47e1681d7bc8f8f8ec0fdb328953689db853944365c8a114c92eefc6077dbd`; trigger,
  correction/supersedes and PIT tests pass.
- Focused Stage 2H plus Stage 2G.2 regression: `24 passed`.
- Full offline suite: `957 passed, 2 warnings`; warnings are pre-existing pandas
  date-format warnings in `tests/test_quality.py`.
- Final formal report: `reports/petrochina_risk_veto_report.json`; final run logical
  digest `d12aec768955c7d8bf0ed839045a9f3b53c596822390a05f4df0931241a4f61c`.
- Hosted CI workflow [30742074822](https://github.com/dlam12138/ashare-research-lab/actions/runs/30742074822)
  on commit `197b94b4cbf05fa1ae4acc36d471df942f807e28` completed successfully. Both
  `clean-clone (ubuntu-latest)` and `clean-clone (windows-latest)` passed the Stage
  2G.2 gates, Stage 2H contract/synthetic gates and the full offline suite.

## Protected state

The default DB remains unchanged at SHA-256
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`. The protected
baseline remains `354 Fact / 102 Metric Result / 16 definitions`. The pre-existing
stash remains present, and `agent/goals/` remains untracked and unmodified by the
implementation.

Final clean-clone and remote Ubuntu/Windows CI gates are complete; no additional
research scope is opened by this acceptance.
