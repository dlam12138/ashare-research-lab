# M2 Stage 2K post-closeout scoring North-Star review

Date: `2026-08-04`

Target: PetroChina (`601857.SH`)

Starting commit: `d34f66cf297a0a9cb0513b414624a496edcb4072`

Decision: `M2_SCORING_ADDENDUM_REOPENED`

## Purpose

Stage 2J conditionally closed M2 with explicit evidence gaps and kept scoring
`SCORING_DEFERRED_BY_DESIGN`. This review is a fresh, evidence-led North-Star
comparison of four ways to treat the scoring addendum. It reopens only the
scoring module, preserves Stage 2J as an immutable historical closeout, and
does not reopen ROIC, dividend, risk-evidence, or any other completed M2 module.

## Verified review baseline

- Branch, local HEAD, fetched upstream and direct remote ref all resolve to
  `feat/m2-value-assessment-mvp` at `d34f66cf297a0a9cb0513b414624a496edcb4072`.
- Default `data/research.duckdb` SHA-256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline: 354 Facts / 102 Metric Results / 16 definitions.
- Stage 2J remains a valid historical conditional closeout at
  `1cb5b776a9f36a72167294fba8d83fb46c43f829`; its CI run `30866296153`
  (Ubuntu `91858789432`, Windows `91858789449`) passed.
- The pre-existing open CI evidence head is `d34f66c` (Stage 2J finalization
  commit); the latest remote CI at this head is re-verified in the Stage 2K
  validation section.
- Protected untracked `AGENTS.md`, `agent/goals/`, the existing stash, and the
  pre-existing Stage 2I.2R acceptance wording edit are outside this decision.

## Current module inventory relevant to scoring

- Trusted: profitability/cash-quality, ROE, ROA, financial safety, PIT
  valuation, valuation history/stress scenarios, lineage, Identity, PIT,
  reproducibility.
- Complete with explicit gaps: dividend realization (9 exchange-payload gaps),
  repurchase evidence (bounded no-event scan), risk-veto layer (two
  `missing_evidence` slots), value-realization layer, one-page profile.
- Not computable under strict evidence contract: ROIC (seven exact gaps).
- Scoring: currently `deferred_by_design`.
- Market mechanism: `not_started`; only `M3_NORTH_STAR_PREFLIGHT_ALLOWED`.

## Scoring feasibility before the review

The value profile exposes six current PIT observations (PE, PS, PB, FCF-proxy
yield, announced and paid dividend yield). Four are `computed` on
`2026-07-31`; the two dividend-yield observations are `missing_input` at the
latest trade date with `partial_evidence` at 2025-09-09/09-18. ROIC is not
computable. Dividend and risk evidence retain explicit gaps. Only one issuer
vertical slice exists. Therefore no peer percentile can be computed today and
no overall score exists.

## Options considered

Qualitative labels are deliberately limited to `high`, `medium`, and `low`.
There is no numeric weighting or composite score in this review.

### 1. `START_M3_PREFLIGHT_NOW`

| Question | Assessment |
|---|---|
| Directly completes the value-assessment product promised by the North Star | `low`; it changes the milestone to market-mechanism work and leaves the profile without the scoring addendum the North Star explicitly asks for ("建议拆分为独立评分"). |
| Preserves the separation of good company, good price, good investment | `medium`; it preserves the current separate dimensions but does not build the missing scoring layer. |
| Can every output be traced to Metric/evidence IDs | `n/a` for scoring; no scoring proposal is made. |
| Hides missing ROIC, dividend or risk evidence | `low`; the current profile already exposes them, but deferring scoring again leaves them unpresented as a dimension. |
| Can risk vetoes remain non-compensatory | `medium`; unchanged, but no scoring contract formalizes it. |
| Is one issuer enough for the proposed benchmark mode | `n/a`; the proposal is not about scoring. |
| Would a numeric score create false precision | `n/a`; none is created. |
| Can a shadow prototype test the method without production authorization | `n/a`; not under this option. |
| Should scoring be completed before M3 preflight | `yes`-leaning: the North Star's value-assessment output is the profile; the M2 scoring addendum is the natural next value-assessment step, and M3 preflight is a separate milestone. |

Risks: defers the scoring addendum again, leaves `SCORING_DEFERRED_BY_DESIGN`
unexamined, and starts M3 before the value-assessment product is complete.

### 2. `PERMANENTLY_DEFER_ALL_SCORING`

| Question | Assessment |
|---|---|
| Directly completes the value-assessment product promised by the North Star | `low`; the North Star explicitly recommends independent dimension scores rather than a single total. |
| Preserves the separation of good company, good price, good investment | `medium`; separate dimensions remain, but no scoring contract makes the separation auditable. |
| Can every output be traced to Metric/evidence IDs | `medium`; current descriptive outputs are traceable, but no scoring traceability exists. |
| Hides missing ROIC, dividend or risk evidence | `low`; the profile already exposes them. |
| Can risk vetoes remain non-compensatory | `medium`; unchanged, but never formalized. |
| Is one issuer enough for the proposed benchmark mode | `low`; permanent deferral avoids the question instead of answering it. |
| Would a numeric score create false precision | `low`; no score is created. |
| Can a shadow prototype test the method without production authorization | `low`; the option forbids even a shadow. |
| Should scoring be completed before M3 preflight | `n/a`; the option refuses scoring forever. |

Risks: a permanent deferral is not an evidence-based conclusion; it would leave
the project unable to answer "is this a good company at a good price with a
realization path and bounded risk" in the structured form the North Star
requests, and it offers no path to resolve the the one-issuer and missing-
evidence concerns that motivate it.

### 3. `BUILD_EXPLAINABLE_INDEPENDENT_DIMENSION_SCORING`

| Question | Assessment |
|---|---|
| Directly completes the value-assessment product promised by the North Star | `high`; the North Star asks for independent dimension scores (企业质量、估值吸引力、价值兑现能力、风险水平) shown separately. |
| Preserves the separation of good company, good price, good investment | `high`; four independent dimensions with no overall score preserve the distinction. |
| Can every output be traced to Metric/evidence IDs | `high`; an explicit component registry binds each component to stable Metric Result / evidence IDs. |
| Hides missing ROIC, dividend or risk evidence | `low`; the missingness/coverage/confidence contract makes ROIC absence a coverage gap and dividend/risk gaps explicit, never zero. |
| Can risk vetoes remain non-compensatory | `high`; risk vetoes are separate flags that no other dimension score can average away. |
| Is one issuer enough for the proposed benchmark mode | `partial`; absolute-contract and categorical-evidence modes work with one issuer, self-history percentile works with the existing 3y/5y/expanding distributions, but peer-percentile cannot. This is disclosed and bounded, not hidden. |
| Would a numeric score create false precision | `low` only if the contract keeps score, coverage, and confidence separate and marks non-production outputs. A shadow prototype is the controlled way to test this. |
| Can a shadow prototype test the method without production authorization | `high`; a non-production shadow is precisely the way to validate the method before any production score. |
| Should scoring be completed before M3 preflight | `yes`; the scoring addendum is value-assessment work, and M3 preflight is a separate milestone. |

Risks: the method must be frozen before viewing the PetroChina result, coverage
gates must prevent false precision, and peer-percentile must remain a bounded
future enhancement. All are addressed by the Stage 2K contract.

### 4. `BUILD_ONE_COMPOSITE_STOCK_SCORE`

| Question | Assessment |
|---|---|
| Directly completes the value-assessment product promised by the North Star | `low`; the North Star explicitly forbids a black-box "综合得分超过80就买入" and recommends separate dimension scores. |
| Preserves the separation of good company, good price, good investment | `low`; a composite necessarily collapses them and can mask a strong quality score beside a poor price and a risk veto. |
| Can every output be traced to Metric/evidence IDs | `medium`; mechanically possible, but a composite invites a recommendation interpretation. |
| Hides missing ROIC, dividend or risk evidence | `high`; a composite silently reweights missing dimensions away and can hide a missing ROIC or dividend gap. |
| Can risk vetoes remain non-compensatory | `low`; a composite is the opposite of a non-compensatory veto. |
| Is one issuer enough for the proposed benchmark mode | `low`; a single composite with one issuer and no peer basis is largely arbitrary. |
| Would a numeric score create false precision | `high`; exactly the risk the North Star warns about. |
| Can a shadow prototype test the method without production authorization | `low`; even a shadow composite would normalize the wrong output shape. |
| Should scoring be completed before M3 preflight | `no`; a composite is not the scoring the North Star wants. |

Risks: this is the forbidden "黑箱式综合得分" path. It is rejected outright.

## Decision

`M2_SCORING_ADDENDUM_REOPENED`.

Only the scoring module is reopened, through a versioned addendum. Stage 2J
remains an immutable historical conditional closeout. The four independent
dimensions are:

- `enterprise_quality`
- `valuation_attractiveness`
- `value_realization_capacity`
- `risk_and_evidence_integrity`

No fifth overall/composite score is allowed. No ranking, recommendation,
target price, upside probability, or portfolio weight is produced. Scoring is
prototyped only as a non-production shadow in this stage.

## Governance wording update

After this review, the scoring module's status is updated from
`SCORING_DEFERRED_BY_DESIGN` to a reopened-addendum state. Milestone 2 is
described as `CONDITIONALLY CLOSED; SCORING ADDENDUM REOPENED`. Only the
scoring module is in progress; all other M2 evidence gaps retain their current
status. Stage 2J history is preserved as an immutable closeout and this addendum
supersedes only the scoring status.

## Boundary

This review alone does not create a scoring result. The scoring contract,
benchmark audit, missingness/coverage/confidence policy, sensitivity, and the
non-production shadow are delivered in the subsequent Stage 2K phases and are
validated before any decision.