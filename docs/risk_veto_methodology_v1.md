# Stage 2H Risk-Veto Evidence Methodology v1

Status: frozen before the PetroChina formal run on 2026-08-02.  This is an
evidence gate, not a risk score and not an investment recommendation.

## Scope and status vocabulary

The vertical slice evaluates PetroChina (`601857.SH`) over FY2021-FY2025,
using only information available at each source's `available_at`.  The output
statuses are deliberately finite:

- `observed`
- `not_observed_within_bounded_evidence`
- `not_evaluated`
- `missing_evidence`

`missing_evidence` never becomes a negative conclusion.  Every observation and
event has `score_eligible: false`.  A key audit matter is not a modified audit
opinion; ordinary accounting-policy or common-control recasts are not error
risk; ordinary related-party transactions are not abuse; a financing proposal
or authorization is not realized dilution; and routine inquiries are not major
discipline.

## Frozen risk IDs and trigger rules

| Risk ID | Trigger |
|---|---|
| `modified_audit_opinion` | Qualified, adverse, or disclaimer opinion; an unmodified opinion with KAMs does not trigger. |
| `going_concern_material_uncertainty` | Explicit material uncertainty related to going concern. |
| `formal_regulatory_investigation_or_major_discipline` | Formal investigation or major discipline only. |
| `material_error_restatement` | Restatement classified as `prior_period_error_or_misstatement`. |
| `controlling_shareholder_pledge_risk` | Direct controller pledge ratio ≥20%, or pledged total shares ≥10%; project thresholds, not legal thresholds. |
| `material_related_party_transaction_risk` | Non-market terms, approval/cap breach, or material non-operating financing. |
| `controlling_shareholder_fund_occupation_or_related_guarantee` | Official fund-occupation or illegal related guarantee finding. |
| `repeated_equity_financing_or_material_dilution` | Completed financing with realized positive share-count dilution. |

Restatement classifications are: `prior_period_error_or_misstatement`,
`accounting_policy_or_standard_change`, `common_control_combination`,
`presentation_or_reclassification`, `other_explained_recast`, and
`unresolved`.  Only the first is eligible for the error trigger.

## Evidence and PIT contracts

`risk_evidence_record_v1`, `risk_event_record_v1`, and
`risk_veto_observation_v1` are deterministic JSON contracts.  Evidence stores
the true source type, exact HTTPS URL, announcement ID, URL locator hash,
content SHA-256, byte size, page count, announcement date, retrieval time,
PIT `available_at`, page/section locator, extraction method, warnings, and a
relative content-addressed cache object key.  The URL hash is only a locator;
it never substitutes for the content hash.

Each risk also has a `bounded_search_register_v1` with systems, date range,
terms, identifiers, query time, result/retrieval counts, rejected candidates
and reasons, anti-bot/network gaps, and a completeness basis.  Network
acquisition is bounded and explicit; the formal runner is offline and uses the
Stage 2G.2 path-independent resolver and artifact verifier.

## Reference review and repository-specific cuts

| Reference reviewed | Borrowed design | Why applicable | Not copied / repository-specific cut |
|---|---|---|---|
| [CSRC annual-report content rule](https://www.csrc.gov.cn/csrc/c101954/c7547588/content.shtml) and [information-disclosure rule](https://www.csrc.gov.cn/csrc/c106256/c1653948/content.shtml) | Official annual-report scope and disclosure evidence | Establishes the issuer's required annual-report evidence surface | This project records bounded retrieval and does not infer absence from an unavailable regulator search. |
| [SSE Listing Rules](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/mainipo/c/c_20260424_10816589.shtml), [related-transaction guideline](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/mainipo/c/c_20250516_10779128.shtml), and [disciplinary standards](https://www.sse.com.cn/lawandrules/sselawsrules2025/disciplinary/c/c_20250516_10782991.shtml) | Related-party, fund-occupation, pledge and discipline concepts | Gives official boundaries for event extraction and classification | Project trigger thresholds are conservative evidence-gate rules, not legal conclusions; routine inquiries remain separate from major discipline. |
| [CSAS 1502](https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/201612/W020161229380915195622.pdf), [CSAS 1504](https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/201612/W020161229380915020654.pdf), and [CSAS 1324](https://m.mof.gov.cn/zcfb/201612/W020161229380915405158.pdf) | Separate opinion, KAM and going-concern sections | Prevents KAMs or going-concern disclosures from being mislabeled as modified opinions | The runner accepts only structured classifications; it does not parse or score narrative materiality. |
| [OpenBB standardization](https://docs.openbb.co/odp/python/developer/standardization) | Provider/standard-field separation and explicit typed schemas | Supports source-specific extraction followed by deterministic normalization | No provider model or external data platform is introduced. |
| [OpenLineage object model](https://openlineage.io/docs/1.30.0/spec/object-model) and [dataset facets](https://openlineage.io/docs/spec/facets/dataset-facets/) | Run/job/dataset-style lineage and input/output separation | Maps naturally to source evidence, event inputs, run outputs and artifact manifests | Existing Stage 2G.2 artifact contracts are reused; no parallel lineage service is built. |
| [Arelle Users Manual](https://www.arelle.org/arelle/wp-content/uploads/2011/12/OpenfilingArelleUsersManual.pdf) | Fact/context/unit-style extraction discipline | Useful precedent for separating a reported fact from its reporting context | No XBRL parser is added to this risk slice; PDF locators and hashes remain the source boundary. |

## Formal run boundary

The official annual reports are stored as a committed evidence ledger with
external hash-addressed cache objects, but the PDFs are not redistributed by
the repository.  `acquisition-preflight` requires an explicit cache root;
`run-offline-formal` reads only committed ledgers and optional hash-verified
cache records.  Each run emits source evidence, events, bounded searches,
observations, a summary, `artifact_manifest.json`, `checksums.sha256`, and a
reproducibility report.  No default DuckDB mutation or report publication
occurs without an explicit publish flag.
