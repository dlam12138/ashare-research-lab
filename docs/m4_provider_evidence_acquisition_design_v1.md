# M4 provider-evidence acquisition design v1

Date: 2026-09-20. Status: **DESIGN_ONLY / NO PROVIDER SELECTED / NO ACQUISITION AUTHORIZED**.

This design implements the next-task boundary from the accepted [K2 source-evidence preflight](m4_k2_source_evidence_preflight_v1.md). It defines how evidence would be evaluated in a later stage; it does not verify current provider facts, contact a provider, acquire bytes, open a database, inspect outcomes or authorize K2 implementation.

## 1. Dossier identity and schema

Schema: `M4_PROVIDER_EVIDENCE_DOSSIER_V1`. One dossier represents one provider/publisher + endpoint/method + dataset + evidence-role combination. Canonical JSON uses UTF-8, sorted keys, compact separators, LF, explicit-offset timestamps and no floats.

Mandatory top-level fields:

| Group | Required fields |
| --- | --- |
| Identity | `schema_version`, `dossier_id`, `state`, `role`, `provider_id`, `publisher`, `endpoint_id`, `method`, `dataset_id`, `security_scope`, `exchange_scope` |
| Retrieval | `requested_start`, `requested_end`, normalized `request_params`, `retrieved_at`, `credential_class`, `transport_proof` |
| Raw evidence | `raw_locator`, `raw_sha256`, `raw_bytes_length`, `media_type`, `retention_class`, `revision_id`, `vintage_id`, `supersedes_raw_sha256` |
| PIT | `source_published_at`, `source_available_at`, `availability_basis`, `timezone`, `timestamp_evidence_sha256` |
| Semantics | `value_semantics`, `unit`, `currency`, `adjustment_policy`, `return_kind`, `return_horizon`, `normalization_rule_id`, `normalization_rule_version` |
| Calendar/membership | `calendar_evidence_id`, `suspension_evidence_id`, `half_day_evidence_id`, `identity_evidence_id`, `membership_evidence_id`, `membership_as_of_rule` |
| Rights | `license_artifact_id`, `license_sha256`, `license_effective_date`, `permitted_use`, `redistribution_scope`, `retention_constraints`, `display_constraints` |
| Review | `evidence_checks`, `rejection_code`, `reviewer_id`, `reviewed_at`, `source_tree_digest`, `dossier_digest` |

`dossier_digest = sha256(canonical_bytes(dossier without dossier_digest, reviewer notes and transient diagnostics))`. Host absolute paths, credentials, secrets and local clock defaults are forbidden digest inputs. Any changed evidence, revision, licence version or review result creates a new dossier identity.

## 2. State machine

| From | To | Gate |
| --- | --- | --- |
| creation | `UNVERIFIED_CANDIDATE` | Tracked candidate name only; never selectable or executable. |
| `UNVERIFIED_CANDIDATE` | `EVIDENCE_COMPLETE` | Every mandatory field validates; original bytes are retained and rehashed; rights, PIT, calendar/membership, semantics and transport gates all pass. |
| `UNVERIFIED_CANDIDATE` | `REJECTED` | Any mandatory evidence is absent, contradictory, expired, unretainable or out of scope. Stable rejection code required. |
| `EVIDENCE_COMPLETE` | `REJECTED` | Later tamper, expiry, revocation or contradiction is proven. |

`REJECTED` is terminal. No transition reverses in place. Reconsideration requires a new dossier digest. `EVIDENCE_COMPLETE` means dossier evidence is complete; it does not select a provider or authorize acquisition, adapter code, real validation or execution.

## 3. Evidence gates

### Raw bytes, transport and revisions

Original response bytes must be retained immutably at a registered relative locator and independently rehashed. Transport proof contains `requested_window_only`, request/response min/max dates, raw date-scan result, out-of-window count, response headers digest and `proof_digest`. Credential values are never retained; only `credential_class` and a redacted request-shape digest are allowed.

Every revision/vintage is a new source identity. Selection rules must be frozen before acquisition; a later revision may not silently overwrite earlier bytes. The bounded transport principles in the tracked [Stage 3B-R4 registry](../reports/m3_stage3br4_source_registry_v1.json) and [oil transport contract](../reports/m3_stage3br4_oil_transport_contract_v3.json) are reusable, while their case sources and external caches are not generic proof.

### PIT, calendar and membership

`published_at` and `available_at` require source-side evidence and explicit timezone; `ingested_at` never substitutes for either. The four-time ordering follows the accepted [real-source design](m4_real_daily_source_contract_design_v1.md) and [M3 timing principles](../reports/m3_stage3b_return_and_timing_contract_v1.json).

Calendar evidence must identify an authoritative publisher/version and retain raw holiday/session bytes plus trading-date, suspension and half-day digests. Quote rows cannot define the calendar. Identity evidence is security-level; per-date membership must carry t−1/as-of rules, source availability and target exclusion. The [identity recovery](../reports/m3_stage3dbr2_security_identity_recovery_contract_v1.json) and [primary proxy](../reports/m3_stage3br1_primary_proxy_contract_v2.json) contracts contribute principles only, not reusable real-study data.

### Semantics and rights

Role-specific unit, currency, adjustment, horizon, predecessor anchor and transform version must be explicit. Mixing adjusted and unadjusted series is rejected.

The named license artifact is mandatory: provider/publisher, artifact identifier, version/effective date, exact content SHA256, permitted-use and redistribution scope, retention/display constraints, credential constraints, and reviewer/date. Absence, expiry or incompatible scope rejects the dossier even when data quality passes. This closes the binding gap recorded by the [K2 preflight](m4_k2_source_evidence_preflight_v1.md) and the tracked [Stage 2G redistribution boundary](stage2g_reproducibility_contract.md).

Original acquired bytes are immutable. Redaction never replaces the bytes whose source SHA is verified. A redacted derivative has its own locator/SHA, a field-level redaction manifest and back-reference. If original retention is forbidden, the dossier is rejected rather than treating the derivative as source evidence.

## 4. Fail-closed cases

Applicable `REAL_*` codes and `RDC-E01`–`RDC-E28` from the [accepted cases](m4_real_daily_source_acceptance_cases_v1.md) are adopted without renaming. Evidence-only additions are frozen below; later changes require a versioned amendment.

| Case | Expected result |
| --- | --- |
| Missing/expired licence artifact or content SHA | `REAL_LICENSE_EVIDENCE_MISSING`, `REJECTED` |
| Licence forbids required retention/use/redistribution | `REAL_LICENSE_SCOPE_FORBIDDEN`, `REJECTED` |
| Only redacted bytes retained or manifest/back-reference missing | `REAL_REDACTION_UNPROVEN`, `REJECTED` |
| Calendar lacks authoritative version/raw evidence | `REAL_CALENDAR_VERSION_MISSING`, `REJECTED` |
| Raw bytes missing/hash mismatch/locator unsafe | Adopt `REAL_RAW_HASH_MISMATCH`, `REAL_SOURCE_ROLE_MISSING`, or `REAL_SOURCE_IDENTITY_MISMATCH`, `REJECTED` |
| Revision/vintage missing or silent overwrite | Adopt `REAL_SOURCE_VERSION_MISSING`, `REJECTED` |
| `published_at`/`available_at` missing or ingestion substituted | Adopt `REAL_PUBLISHED_AT_MISSING`, `REAL_AVAILABLE_AT_MISSING`, or `REAL_INGESTED_AT_AS_PIT`, `REJECTED` |
| Response contains dates outside request/development bounds | Adopt `REAL_ENDPOINT_UNBOUNDED` or `REAL_HOLDOUT_INJECTION`, `REJECTED` |
| Per-date membership/identity evidence incomplete | Adopt `REAL_MEMBERSHIP_INCOMPLETE` or `REAL_SECURITY_IDENTITY_CONFLICT`, `REJECTED` |
| Unit, currency, adjustment or horizon mismatch | Adopt the corresponding RDC semantic rejection; no coercion or fallback |

## 5. Candidate inventory and phase boundary

Names already present in tracked evidence—including `baostock.query_trade_dates`, `baostock.query_history_k_data_plus`, CNINFO access mediated by akshare, and EIA-related endpoints—may appear only as `UNVERIFIED_CANDIDATE`. Their current availability, terms, methods, completeness and suitability are unknown in this design.

Later phases remain separate and require explicit Goals:

1. provider-evidence acquisition (evidence only);
2. provider adapter implementation;
3. real-data validation;
4. study binding and real execution.

No phase may infer authorization from the previous one. Provider selection, credentials, acquisition, K2 code, real observations, holdout, statistics and execution remain unauthorized.
