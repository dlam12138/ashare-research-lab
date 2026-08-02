# Stage 2H.1R Risk-Veto Methodology v2 / v3 contracts

This is the frozen implementation contract for the Stage 2H.1R closeout. The v1
methodology and v1 ledgers remain historical records; the v2 methodology remains
the trigger baseline. Stage 2H.1R adds provenance and fixed-universe controls
without changing the eight risk IDs or their trigger boundaries.

## Frozen boundaries

- Key audit matters are not modified audit opinions.
- An explicit going-concern material uncertainty is required; a bounded absence
  is not a permanent absence claim.
- Only a formal investigation or major discipline can trigger the regulatory
  risk. Routine inquiries and generic search results are not major discipline.
- Accounting-policy changes, standard changes and common-control comparative
  recasts are not prior-period error risk.
- Ordinary related-party sales and purchases are not abuse without a separate
  non-market, approval-cap, or material non-operating-finance trigger.
- A proposed or authorized share issue is not completed financing or realized
  dilution.
- Missing evidence is represented only as `missing_evidence`; it is never a
  negative conclusion.

## Contracts

`risk_veto_methodology_v2` uses `bounded_search_register_v2`,
`risk_event_record_v3`, `risk_evidence_normalization_record_v1`,
`risk_veto_observation_v3`, `risk_universe_evaluation_v1`, and
`risk_evaluation_slot_v1`. Event input values are reconstructed from
field-level normalization records, not copied from an event-input summary.
Each event and observation separates `input_evidence_ids` from
`supplemental_evidence_ids`; only the input set participates in
`input_lineage_hash`. The public risk-universe evaluator emits exactly eight
slots even when no observation can be published.
Every evidence, search, event, normalization and observation record carries a
PIT `available_at` (observations additionally require
`conclusion_available_at`). IDs include the relevant version, identity and
lineage payload.

## Search-register PIT and supersession

Search-register visibility is selected using `available_at <= as_of` and
`coverage_end <= as_of`. A register revision can supersede only a same-risk
parent, must be later available, and must form one acyclic chain. Missing
parents, cross-risk links, reverse-time links, branches, cycles and coverage
that ends after the evaluation date fail closed.

Event versions use the same identity principle. A correction can supersede
only the same symbol/risk/semantic key, is visible only after its own
`available_at`, and resolves through the complete visible chain. Observation
IDs include active IDs, superseded IDs and applied supersession edges.

## Official evidence and cache

The path-independent v2 registry maps all ten evidence IDs to eight unique
content-addressed PDF objects. The real formal runner requires an explicit
official cache root and reuses the Stage 2G.2 `MarketSnapshotResolver` before
evaluation. It additionally verifies the full evidence-to-registry mapping,
object key, real content SHA-256 and byte size. Formal publication is blocked
unless cache verification, lineage, search PIT, event supersession and artifact
verification all pass.

## Scope exclusions

This stage does not begin ROIC, scoring, Web research, target price,
recommendation, automatic trading or market-mechanism work.
