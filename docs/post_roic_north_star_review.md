# M2 Stage 2J post-ROIC North-Star review

Date: `2026-08-04`

Target: PetroChina (`601857.SH`)

Starting commit: `ecc150449e83804fa6b91f5a5660387946e22b80`

Decision: `M2_CONDITIONAL_CLOSEOUT_ALLOWED`

## Decision

Select `FREEZE_ROIC_NOT_COMPUTABLE_AND_CONDITIONALLY_CLOSE_M2`.

The Stage 2I.2R evidence is trusted: 9 of 16 Plan v3 fact/year cells were
acquired, seven remain explicit, the executed searches are complete over the
registered FY2023/FY2024 CAS annual-report objects, and the shadow gate remains
`ROIC_FACT_GAPS_REMAIN`. No current finite, high-probability official-source
batch can resolve all hard blockers. The available substitutes require at
least one forbidden act: proxy tax, residual associate/JV allocation,
unsupported non-operating-asset deduction, manual plug, or weaker numerator /
denominator scope matching.

This decision is an evidence boundary, not a conclusion about PetroChina's
capital-return performance. It produces no ROIC value and does not say ROIC is
zero, poor, not applicable, or complete.

## Verified review baseline

- Branch, local HEAD, fetched upstream and direct remote ref all resolved to
  `feat/m2-value-assessment-mvp` at
  `ecc150449e83804fa6b91f5a5660387946e22b80`.
- Default `data/research.duckdb` SHA-256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected inventory: 354 Facts, 122 metric-eligible Facts, 11 Contexts;
  protected accepted output baseline: 102 Metric Results and 16 definitions.
- Stage 2I.2R formal A/B artifact-set digest:
  `90632b11b4784a019f8765237fe0d4bafcf1b8a80ff5c681a57fba3798da2483`;
  committed internal packet digest:
  `cb35113e81016ac9de2cd966b48174af425cfdb2aeb3fc5a0341afbe6cd1e57f`.
- Stage 2I.2R manifest verification passed for all 16 entries after the
  repository's canonical LF normalization. Targeted baseline: `34 passed`.
- Latest opening-head CI is run `30863411552` at `ecc1504`: Ubuntu job
  `91850026057` and Windows job `91850026156` both passed.
- Protected untracked `AGENTS.md`, `agent/goals/`, the existing stash, and the
  pre-existing Stage 2I.2R acceptance wording edit are outside this decision.

## North-Star fit

Both project North-Star documents require an explainable value profile,
separate analytical dimensions, no future leakage, and no missing value
silently interpreted as zero. They prohibit turning incomplete evidence into a
black-box score, target price, or buy/sell conclusion. Conditional closeout
keeps the trusted value dimensions usable and makes the ROIC limitation more
visible than either an invented number or indefinite milestone ambiguity.

## Options considered

Qualitative labels are deliberately limited to `high`, `medium`, and `low`.
There is no numeric weighting or composite score.

### 1. `CONTINUE_ROIC_OFFICIAL_SOURCE_RESEARCH`

| Question | Assessment |
|---|---|
| Serves value assessment | `medium`: a directly disclosed blocker would help, but the already-registered source universe is exhausted. |
| Can materially change the PetroChina research conclusion | `low`: it could add one dimension, but does not invalidate trusted ROE/ROA, cash, safety, dividend, valuation, or risk evidence. |
| Finite new official source universe not already searched | `low`: no current issuer/exchange/audited document category with direct scope-matched disclosures was identified. |
| Clean-clone reproducibility with external verified evidence | `medium` if a genuinely new official document existed; currently there is no such input. |
| Leakage, proxy, residual, manual, or hidden-assumption risk | `high` if research is forced to manufacture a result from existing disclosures. |
| Preserves numerator/denominator scope matching | `low` for the available fallbacks. |
| Compatible with missing-is-not-zero | `medium` only if the result remains missing; repeated search adds no new evidence. |
| Delays M3 without realistic ROIC resolution | `high`. |
| Simpler honest alternative | Freeze non-computability with traceable gaps. |

A mirror, translated copy, issuer/exchange alias, or alternate URL for the same
annual report is not a new source class. A future audited report or genuinely
new official disclosure may trigger reconsideration, but it is not a finite
current acquisition batch.

### 2. `RELAX_ROIC_METHOD_AND_USE_PROXIES`

| Question | Assessment |
|---|---|
| Serves value assessment | `low`: it creates a number whose comparability and meaning are weaker than its presentation suggests. |
| Can materially change the research conclusion | `medium`, but only through assumption sensitivity rather than stronger evidence. |
| Finite new official source universe not already searched | `low`; this changes method, not evidence. |
| Clean-clone reproducibility with external verified evidence | `high` mechanically, but reproducibility would not make unsupported semantics trustworthy. |
| Leakage, proxy, residual, manual, or hidden-assumption risk | `high`. |
| Preserves numerator/denominator scope matching | `low`. |
| Compatible with missing-is-not-zero | `low`. |
| Delays M3 without realistic ROIC resolution | `medium`; it opens a new methodology campaign. |
| Simpler honest alternative | Keep the missing status explicit. |

Rejected fallbacks are: effective/statutory tax rates for direct operating tax;
residual associate/JV splits; deduction of cash or financial assets without
official operating-purpose and linked-income proof; manual plugs; and reduced
scope matching merely to emit a result.

### 3. `FREEZE_ROIC_NOT_COMPUTABLE_AND_CONDITIONALLY_CLOSE_M2`

| Question | Assessment |
|---|---|
| Serves value assessment | `high`: it preserves usable trusted dimensions and states the evidence boundary. |
| Can materially change the PetroChina research conclusion | `medium`: it prevents a capital-return claim rather than fabricating one. |
| Finite new official source universe not already searched | `low`, which supports freezing rather than another identical search. |
| Clean-clone reproducibility with external verified evidence | `high`: the status, source references, gaps, and digests are committed and verifiable without the default DB or network. |
| Leakage, proxy, residual, manual, or hidden-assumption risk | `low`. |
| Preserves numerator/denominator scope matching | `high`, because no mismatched calculation is emitted. |
| Compatible with missing-is-not-zero | `high`. |
| Delays M3 without realistic ROIC resolution | `low`; it permits only a separate M3 North-Star preflight. |
| Simpler honest alternative | This is the simpler honest alternative. |

### 4. `BLOCK_M2_INDEFINITELY_UNTIL_ROIC_EXISTS`

| Question | Assessment |
|---|---|
| Serves value assessment | `low`: it hides the usability of completed dimensions behind one non-computable dimension. |
| Can materially change the PetroChina research conclusion | `low` without new evidence. |
| Finite new official source universe not already searched | `low`. |
| Clean-clone reproducibility with external verified evidence | `high` for the blocked state, but it yields no additional analytical evidence. |
| Leakage, proxy, residual, manual, or hidden-assumption risk | `low`, but at the cost of indefinite milestone paralysis. |
| Preserves numerator/denominator scope matching | `high`. |
| Compatible with missing-is-not-zero | `high`. |
| Delays M3 without realistic ROIC resolution | `high`. |
| Simpler honest alternative | Conditional closeout with explicit gaps. |

## Seven-gap recoverability classification

The same registered annual reports were not searched again in Stage 2J. This
classification reads the executed Stage 2I.2R search records; it does not
download, extract, or enter a fact.

| Gap ID | Acquisition / role / FY | Documents already searched | Missing semantic requirement | Classification | New official category now available | Success probability | Bounded effort | Independently unblocks shadow | Other gaps still block |
|---|---|---|---|---|---|---|---|---|---|
| `M2G-ROIC-001` | `A-2024-operating-tax` / `tax.operating_tax_expense` / 2024 | FY2024 issuer and SSE aliases of CAS annual report; one verified content object; all pages | Direct operating-tax expense matched to operating-profit scope, not total tax or a rate | `not_separately_publicly_disclosed` | none identified | `low` | Wait for a newly published audited/official direct disclosure; no repeat search | no; numerator remains blocked | yes |
| `M2G-ROIC-002` | `B-2023-2024-associate` / `invested_capital.associate_investment` / 2023 | FY2023 and FY2024 issuer/SSE CAS annual-report objects; all pages | Complete separate associate balance including individually immaterial holdings | `requires_methodology_relaxation` | none identified | `low` | Separate official disclosure or independently approved new method | no; denominator scope remains incomplete | yes |
| `M2G-ROIC-003` | `B-2023-2024-associate` / `invested_capital.associate_investment` / 2024 | FY2024 issuer/SSE CAS annual-report object; all pages | Complete separate associate balance including individually immaterial holdings | `requires_methodology_relaxation` | none identified | `low` | Separate official disclosure or independently approved new method | no | yes |
| `M2G-ROIC-004` | `B-2023-2024-jv` / `invested_capital.joint_venture_investment` / 2023 | FY2023 and FY2024 issuer/SSE CAS annual-report objects; all pages | Complete separate JV balance including individually immaterial holdings | `requires_methodology_relaxation` | none identified | `low` | Separate official disclosure or independently approved new method | no; denominator scope remains incomplete | yes |
| `M2G-ROIC-005` | `B-2023-2024-jv` / `invested_capital.joint_venture_investment` / 2024 | FY2024 issuer/SSE CAS annual-report object; all pages | Complete separate JV balance including individually immaterial holdings | `requires_methodology_relaxation` | none identified | `low` | Separate official disclosure or independently approved new method | no | yes |
| `M2G-ROIC-006` | `C-2023-2024-non-operating-financial-assets` / `invested_capital.non_operating_financial_assets` / 2023 | FY2023 and FY2024 issuer/SSE CAS annual-report objects; all pages | Exact official non-operating-purpose classification with linked-income proof | `requires_methodology_relaxation` | none identified | `low` | Direct official purpose/income linkage or independently approved new method | no; denominator deduction is unsupported | yes |
| `M2G-ROIC-007` | `C-2023-2024-non-operating-financial-assets` / `invested_capital.non_operating_financial_assets` / 2024 | FY2024 issuer/SSE CAS annual-report object; all pages | Exact official non-operating-purpose classification with linked-income proof | `requires_methodology_relaxation` | none identified | `low` | Direct official purpose/income linkage or independently approved new method | no | yes |

Source search IDs are respectively `stage2i2r-search-01` through
`stage2i2r-search-07`. All seven have `search_completeness=complete` and stable
deterministic IDs in
`reports/petrochina_roic_stage2i2r_bounded_search_result_v2.json`.

## Scoring review

Decision: `SCORING_DEFERRED_BY_DESIGN`.

Only one issuer vertical slice exists; ROIC is not computable under the strict
contract; dividend and risk-veto evidence gaps remain; and the North Star calls
for independent dimensions. A score would compress missing evidence into a
false precision and invite a recommendation interpretation. No weights,
thresholds, rankings, traffic lights, or score engine are authorized.

## Mature design and authoritative-contract review

### References reviewed

- Both project North-Star files, governance files, README, roadmap, scoring
  gates, the four previous post-module North-Star reviews, and Stage 2A–2I.2R
  acceptance history.
- Repository Stage 2G.2 artifact/checksum and clean-clone contracts, Stage 2H
  fixed risk-slot/bounded-search contracts, and Stage 2I fail-closed readiness
  and three-state decision gates.
- Frozen ROIC methodology, dependency graph, concept registry v2, Plan v3,
  Stage 2I.2R outputs, and the previously reviewed CFA, Damodaran, Ministry of
  Finance CAS, issuer, and SSE analytical references recorded there.
- Mature MADR/ADR, OpenLineage-style reference, and JSON-Schema-style
  discriminated-status patterns at the contract-design level.

### Borrowed designs and applicability

- MADR/ADR: explicit decision, alternatives, consequences, reopen/supersession
  conditions. Applicable because non-computability is a durable governance
  decision, not an incidental missing field.
- OpenLineage style: logical input artifact IDs/digests, decision run/CI IDs,
  and output artifact references. Applicable because clean-clone reviewers must
  trace closeout to immutable evidence without the default DB.
- Discriminated status: a versioned `status` vocabulary whose ROIC branch
  forbids a numeric value. Applicable because `null`, zero, unavailable, and
  evidence-limited non-computability must not be conflated.
- Existing repository patterns: computed ledger counts, fixed risk slots,
  source-record backreferences, checksum manifests, and fail-closed gates.

### Not copied

No external ADR, lineage, or schema framework is added as a dependency. No
generic enterprise metadata server, ontology, numeric completion model, or
runtime workflow engine is introduced.

### Repository-specific cuts

- A single `m2_module_status_v1` matrix and one current M2 gap ledger.
- Exact source-record IDs for nine Stage 2F, two Stage 2H, and seven Stage 2I
  gaps; original ledgers remain authoritative history.
- ROIC status is a value-profile evidence contract with no numeric branch.
- Closeout permits only `M3_NORTH_STAR_PREFLIGHT_ALLOWED`; market-mechanism
  implementation remains `not_started`.

## Actual module inventory reviewed

- Data foundation: providers, services, normalized models, quality checks,
  DuckDB/Parquet storage, source registries, Fact identity, Context, PIT,
  reconciliation, version chains, lineage, and reproducibility capsules.
- M2 value foundation: profitability/cash-quality Facts and Metrics, capex/FCF
  proxy, earnings quality, ROE, ROA, and financial-safety methodology/results.
- Realization and valuation: dividend events/metrics, repurchase scan, share
  timeline, PIT valuation observations, history/percentiles, stress scenarios,
  one-page profile, and clean-clone artifact contracts.
- Risk: eight-slot risk-veto methodology, evidence registry/normalization,
  bounded-search register, historical PIT profile, and legacy migration.
- ROIC: frozen methodology, dependency graph, concept registry, readiness,
  Plan v3 acquisition, isolated corrected facts, executed search, PIT/identity
  verification, and fail-closed decision gate.
- Explicitly absent: production ROIC Metric/Result, score engine, market-
  mechanism hypothesis/proxy/control code, Web recommendation/target-price/
  trading features.

## Consequences and next gate

- Milestone wording after all Stage 2J validations and final CI may be:
  `Milestone 2: CONDITIONALLY CLOSED WITH EXPLICIT EVIDENCE GAPS`.
- Trusted existing dimensions remain independently usable; current gaps stay
  visible and score-ineligible.
- The only permitted next-stage state is `M3_NORTH_STAR_PREFLIGHT_ALLOWED`.
  It does not authorize or start M3 implementation.
- A failed artifact, profile, protected-baseline, clean-clone, or final-CI gate
  changes the Stage 2J verdict to blocked/fail; this review alone is not the
  closeout acceptance.
