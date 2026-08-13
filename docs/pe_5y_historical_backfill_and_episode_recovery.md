# Frozen-5Y historical backfill and episode recovery

## Purpose and boundaries

R4F.4A1 fills exactly four annual logical cells required to make the frozen
2021-08-02 through 2026-07-31 normalized-earnings history complete. It does
not expand the valuation-percentile window, read future realized EPS values,
calculate outcome errors, acquire Brent data, or authorize PE scoring.

The planning aliases `parent_equity` and `parent_net_profit` map respectively
to the existing canonical concepts `equity_attributable_to_parent` and
`net_profit_attributable_to_parent`. Only the canonical concepts enter Facts.

## Evidence and PIT method

The original facts come from SSE official annual-report disclosures. Formal
announcement dates come from SSE bulletin metadata, not URL paths, filenames,
or HTTP headers. Each pinned PDF is content-addressed. The 2017 annual-report
object reuses the committed R4F.3A SHA-256 identity.

The earliest relevant announcement is 2016-03-24, before the existing R4F.3A
calendar begins. A side-by-side baostock calendar therefore extends coverage
without superseding or modifying the old pin. Its complete overlap with the
old calendar is compared as an exact date set. New facts use the new calendar
for strict next-trading-day `effective_from`; existing facts retain their old
calendar provenance.

Comparative/restatement evidence is bounded to the 2015 through 2020 annual
reports. Direct comparatives match all four original values, so the result is
four logical cells, four Fact records, and zero restatement versions. No 2014
or earlier economic fact is acquired.

## Borrowed designs and repository-specific cuts

`references_reviewed`:

- XBRL fact semantics: concept, entity, period/context, and unit jointly
  identify the meaning of an accounting fact.
- W3C PROV: versioned entities, derivation, revision lineage, provenance, and
  reproducibility.

`borrowed_designs` and `why_applicable`:

- Explicit concept/context/unit fields prevent annual profit, instant equity,
  scope, and filing-version collisions.
- Immutable source hashes, Fact IDs, supersession fields, and version chains
  preserve point-in-time selection and reproducibility.

`not_copied`:

- No XBRL parser, taxonomy engine, RDF, PROV-O runtime, or graph database.

`repository_specific_cuts`:

- The existing `FactIdentity`, `supersedes_fact_id`,
  `source_object_sha256`, and content-addressed cache conventions remain the
  implementation contract.
- The existing R4F.3 readiness engine is reused. The R4F.4A episode and outcome
  functions receive narrow window-generic helpers while their 3Y wrappers and
  committed outputs remain compatible.
- A stage-specific artifact manifest is not needed:
  `ARTIFACT_MANIFEST_NOT_REQUIRED_STAGE_LOCAL_ACQUISITION`.

## Result semantics

The backfill makes all 1211 frozen-window trade days ready. Re-derivation from
the 5Y daily/state series finds one regime already positive at the window
start, so it remains left-censored. The first observed date is not substituted
for an onset, and all formal anchor fields remain null. Consequently there are
zero valid onset-anchored episodes and zero protocol-valid mature +4Q/+8Q
episodes.

The data stage is trusted, but independent outcome validation is
`NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY`. The required action is
`STOP_FOR_NORTH_STAR_REVIEW`; automatic history extension is prohibited.

