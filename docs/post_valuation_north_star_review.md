# Post-valuation North-Star Review: PetroChina risk-veto evidence

Date: 2026-08-02
Scope: M2 Stage 2H only; PetroChina (`601857.SH`), FY2021-FY2025 annual-report evidence
and bounded event search from 2021-01-01 through 2026-07-31. This review does not
authorize ROIC, scoring, Web, target price, recommendation, automatic trading or market-
mechanism work.

## Decision

```text
Stage 2H risk-veto evidence: ALLOWED
Next permitted vertical slice: bounded official governance, audit and risk-veto evidence
ROIC: NOT YET
Scoring: STILL NOT YET
Market mechanism: NOT STARTED
```

The decision is `ALLOWED` because the current value profile already has bounded PIT-aware
quality, capital-return, financial-safety, dividend and valuation layers, while its
`governance_risk`, `audit_risk` and `related_party_risk` fields remain explicitly
`not_evaluated`. The project North Star treats modified audit opinions, explicit going-
concern uncertainty, major discipline, material error/restatement, abuse of related-party
channels and realized material dilution as possible non-compensable risk-veto evidence.
The next slice therefore closes a directly visible value-assessment blind spot without
turning the profile into a score or recommendation.

## Qualitative comparison

High/medium/low express evidence and engineering fit only. They are not weights, scores,
thresholds, grades or investment conclusions.

| Candidate | North-Star contribution | Direct ability to change research priority | Official evidence boundedness | Methodology disagreement | PIT/version complexity | Existing infrastructure reuse | Selection state |
|---|---|---|---|---|---|---|---|
| Risk-veto evidence | high | high | high | medium | high | high | selected; `ALLOWED` |
| ROIC | high | high | medium | high | high | medium | blocked; NOPAT/invested-capital boundary not frozen |
| Remaining dividend evidence gaps | medium | medium | medium | medium | high | high | later; finite exchange retrieval gaps remain explicitly disclosed |
| Market-mechanism MVP | high | medium | medium | high | high | medium | separate later module; not a value-profile substitute |

## Required answers

### Which missing capability can most directly change whether PetroChina remains worth researching?

Bounded risk-veto evidence can change research priority most directly. A verified modified
opinion, explicit going-concern material uncertainty, registered major discipline, material
prior-period error, controlling-shareholder pledge trigger, abusive/non-market related-party
channel, or completed material dilution could invalidate an otherwise attractive value
profile. Conversely, a bounded unmodified-opinion and no-trigger result can narrow the risk
question without claiming that the company is safe.

### Is the official evidence bounded and obtainable?

Yes, with finite limits: the five annual reports and their audit-report sections define the
annual-report scope; CSRC/SSE official regulatory searches and issuer/exchange disclosure
systems define the event scope; official pledge, related-party and capital-change notices
define the event families. Search systems can be unavailable or incomplete for individual
documents, so each category will retain a search register and use `missing_evidence` when
the required evidence or hash verification is unavailable. A bounded negative result will
only be represented as `not_observed_within_bounded_evidence` after the registered search
completes.

### Can the work reuse current Evidence/Event/PIT/reproducibility contracts?

Yes. Source evidence will retain true source types, locator hashes and real content
SHA-256 values. Risk events will use deterministic versioned IDs, explicit event dates and
PIT `available_at`; corrections will supersede rather than overwrite. Formal mode will
reuse the Stage 2G.2 path-independent cache resolver, artifact manifest/checksum verifier,
clean-clone capsule and Ubuntu/Windows workflow. Raw PDFs, HTML and API responses remain
outside Git under an explicitly supplied cache root.

### Does the stage risk becoming an unbounded news search or subjective governance score?

It would if it used generic news, hidden thresholds, ordinary transactions as abuse, or
LLM judgment as the classifier. The stage is cut to pre-registered risk IDs, named official
systems, exact date ranges, bounded query terms, explicit candidate rejection reasons,
transparent project thresholds where no universal legal threshold exists, and
`score_eligible=false` for every output. Routine inquiries, key audit matters, normal
accounting-policy/common-control recasts and proposed financing remain non-veto boundaries.

### Why does ROIC remain blocked or why should it supersede this stage?

ROIC remains blocked. NOPAT, tax normalization, operating leases, minority interests,
excess cash and invested-capital boundaries are not one reconciled contract. Starting ROIC
now would broaden the project into a high-disagreement derived metric while the current
profile has an unresearched risk-veto blind spot that can change research priority more
directly.

### Why does market mechanism remain separate from value assessment?

Market mechanism tests explain price/flow/liquidity relationships and require hypotheses,
controls, sample definitions and out-of-sample checks. They cannot replace evidence about
an issuer's audit opinion, regulatory status, related-party terms or completed share-count
changes. The mechanism MVP remains a later consumer of a stable value profile and is not
started by this stage.

## Protected boundaries

- No numerical weighting, governance score, traffic light, star rating or recommendation.
- All risk outputs use only `observed`, `not_observed_within_bounded_evidence`,
  `not_evaluated` or `missing_evidence`.
- Missing evidence is not a negative conclusion and is never zero-filled.
- Official evidence is classified by its true source system; a designated disclosure
  platform is not relabeled as issuer, exchange or regulator.
- The default DB, stash, protected historical baselines and untracked `agent/goals/`
  directory remain outside the change scope.

## Gate result

`ALLOWED`. Proceed to the mature-project and current-official-standards review, then freeze
the risk-veto methodology and trigger rules before evaluating PetroChina.
