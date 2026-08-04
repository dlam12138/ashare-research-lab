# ADR-ROIC-001: strict-evidence ROIC non-computability

- Status: `accepted`
- Date: `2026-08-04`
- Decision code: `ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT`
- Target: PetroChina (`601857.SH`)
- Target period: FY2024 duration with FY2023 opening and FY2024 closing balances
- Supersedes: the open-ended post-acquisition question after Stage 2I.2R; it
  does not erase any historical acceptance or source ledger

## Context

The frozen `value_evaluation_methodology_roic_v1` contract requires a
scope-matched consolidated operating NOPAT numerator and average invested-
capital denominator. Plan v3 has logical digest
`aedaebcaa5b85fd4bbfa39f77c2ac09a55c548cf2bb099cdc008271aa3340215`.
The corrected Stage 2I.2R formal artifact digest is
`90632b11b4784a019f8765237fe0d4bafcf1b8a80ff5c681a57fba3798da2483`;
its committed internal packet digest is
`cb35113e81016ac9de2cd966b48174af425cfdb2aeb3fc5a0341afbe6cd1e57f`.

Stage 2I.2R acquired nine of 16 fact/year cells. Seven remain explicit:

- FY2024 direct operating-tax expense;
- complete separate associate balances for FY2023 and FY2024;
- complete separate joint-venture balances for FY2023 and FY2024;
- officially proven non-operating financial assets for FY2023 and FY2024.

All seven executed searches are complete over the registered verified FY2023 /
FY2024 CAS annual-report objects. A different URL, mirror, or translation of
the same report is not a new source class.

## Decision

ROIC is `not_computable_under_strict_evidence_contract`. No numeric ROIC,
estimated ROIC, shadow result, production Metric, or Metric Result is created.
The value profile exposes this exact status and the seven canonical gap IDs.

## Why the gaps are hard blockers

- Operating tax is an independent NOPAT contribution. Total current/deferred
  tax, a statutory rate, or an effective tax rate does not establish direct
  tax on the frozen operating-profit bridge.
- The reports separately disclose major associates and joint ventures but
  combine individually immaterial residual holdings. Assigning the combined
  residual would require an unsupported split or plug, so opening and closing
  denominator scope cannot match the frozen income/capital treatment.
- Financial-asset classes and income lines do not provide exact official
  non-operating-purpose plus linked-income proof. Deducting them would weaken
  the denominator boundary and can mismatch numerator exclusions.
- Ending invested capital cannot replace the opening balance; restricted cash
  cannot be treated as freely deductible; and missing facts cannot be zero.

## Rejected alternatives

### Continue the same official-source search

Rejected now because no finite high-probability current official-source batch
was identified. Re-searching identical annual-report content cannot change the
evidence universe.

### Tax-rate proxy

Rejected because it applies an assumed tax relationship to a numerator whose
operating/non-operating bridge has its own frozen scope. A plausible rate is
not direct official evidence.

### Associate/JV residual allocation

Rejected because no official rule allocates the combined immaterial balance.
Any split, including a proportional or income-based split, is a methodology
choice and can break numerator/denominator scope matching.

### Unsupported non-operating-asset deduction

Rejected because asset class alone does not prove non-operating purpose or the
linked income treatment. All-cash or broad financial-asset deductions are also
forbidden.

### Manual plug or weaker scope

Rejected because it would hide the evidence gap, violate missing-is-not-zero,
and make the result incomparable with the frozen method.

### Block M2 indefinitely

Rejected because the remaining trusted M2 dimensions are independently usable
when the ROIC limitation is explicit. Indefinite blocking adds no evidence.

## Consequences

- `shadow_status=not_run`.
- `production_metric_created=false` and no production ROIC Metric Result.
- `score_eligible=false`; scoring remains `SCORING_DEFERRED_BY_DESIGN`.
- Existing trusted ROE and ROA results are unchanged and are not substitutes
  for ROIC.
- The value profile must not contain a ROIC number, a null interpreted as zero,
  proxy, traffic light, score, ranking, target price, or recommendation.
- This is an evidence limitation. It is not evidence that PetroChina has poor
  capital returns and does not establish that the company is undervalued.
- Conditional M2 closeout may permit only
  `M3_NORTH_STAR_PREFLIGHT_ALLOWED`; M3 implementation is not started here.

## Reopen conditions

ROIC may be reconsidered only when at least one occurs:

1. a newly published issuer/exchange official document directly resolves a
   hard blocker;
2. a new audited annual report separately discloses the missing role;
3. a separate North-Star Review approves a new methodology; or
4. a genuinely new official source class is identified and passes source and
   evidence preflight.

Any reopening must still determine whether all other hard blockers remain and
must preserve PIT, Fact Identity, unit, period, Context, scope, lineage, and
restatement contracts.

## Insufficient reopen triggers

The following do not reopen this decision: a third-party terminal number, a
website estimate, an LLM allocation, a reasonable-looking tax rate, a
calculable residual, a mirror/translation/alternate URL of an already-searched
report, or a score that wants a value.

## Traceability

- North-Star review: `docs/post_roic_north_star_review.md`
- Canonical gaps: `M2G-ROIC-001` through `M2G-ROIC-007` in
  `reports/m2_explicit_gap_ledger.json`
- Stage 2I.2R acquisition result:
  `reports/petrochina_roic_stage2i2r_acquisition_result.json`
- Executed search evidence:
  `reports/petrochina_roic_stage2i2r_bounded_search_result_v2.json`
- Stage 2I.2R delivery manifest:
  `reports/petrochina_roic_stage2i2r_delivery_manifest.json`

## Supersession

This ADR remains `accepted` until a later decision record explicitly marks it
`superseded` and identifies the qualifying new evidence or separately approved
methodology. Silent replacement by a profile field or metric is prohibited.
