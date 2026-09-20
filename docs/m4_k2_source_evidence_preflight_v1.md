# M4 K2 real-source evidence preflight v1

Date: 2026-09-20. Decision: **FAIL_CLOSED / NO K2 IMPLEMENTATION CANDIDATE**. This repository-only review used no provider, network, database contents, real observations or holdout. It does not select or verify any source.

Task contract: [K2 evidence preflight Goal](../agent/goals/2026-09-20_m4_k2_source_evidence_preflight.md). Required evidence comes from the accepted [real-source design](m4_real_daily_source_contract_design_v1.md), its [acceptance cases](m4_real_daily_source_acceptance_cases_v1.md), and the bounded [K1 acceptance](../acceptance/2026-09-14_m4_real_source_offline_kernel.md).

## Evidence disposition

| Required class | Disposition | Tracked candidates and reusable principles | Missing proof / reason not nominated |
| --- | --- | --- | --- |
| `TARGET_OUTCOME` and `FACTOR` source, version and raw bytes | `INSUFFICIENT_EVIDENCE` | [M3 timing contract](../reports/m3_stage3b_return_and_timing_contract_v1.json) and [source registry](../reports/m3_stage3b_source_registry_v1.json) document a case-specific target series; [Stage 3B-R4 registry](../reports/m3_stage3br4_source_registry_v1.json) records bounded acquisition principles. | The M3 raw data is not committed; its SHA cannot be recomputed from tracked bytes. No M4 `FACTOR` provider exists. Revision/vintage selection, normalization-versus-raw proof and portable raw retention are absent. M3 case constants cannot be promoted into generic M4 proof. |
| Exchange calendar, suspension and half-day evidence | `INSUFFICIENT_EVIDENCE` | [M3 source registry](../reports/m3_stage3b_source_registry_v1.json) names `query_trade_dates`; valuation calendar registries such as [v1](../config/pit_valuation_market_calendar_registry_v1.json) demonstrate content-addressed calendar principles. | The valuation calendars are symbol-scoped and derived from target price rows, which the design forbids as the expected-date authority. No tracked authoritative raw exchange calendar, calendar version, holiday SHA, suspension table or half-day table closes the design contract. |
| Security identity and per-date membership | `INSUFFICIENT_EVIDENCE` | [Identity recovery contract](../reports/m3_stage3dbr2_security_identity_recovery_contract_v1.json) demonstrates security-level fail-closed identity; [primary proxy contract](../reports/m3_stage3br1_primary_proxy_contract_v2.json) supplies t−1 and target-exclusion principles. | The identity repair is case/provider-specific and its holdout was consumed. Current-master metadata is not per-date membership. No tracked source proves historical membership plus per-date `available_at`; K1 explicitly leaves membership unverified. |
| `published_at`, `available_at` and PIT timing | `INSUFFICIENT_EVIDENCE` | [M3 timing contract](../reports/m3_stage3b_return_and_timing_contract_v1.json) separates observation, publication, availability and ingestion concepts; K1 enforces their structural order on invented fixtures. | No tracked real role source supplies citation-grade `published_at` or `available_at`. K1's calendar is caller-frozen and unverified. Structural semantics are reusable; real timestamp evidence is not present. |
| Return, unit and adjustment semantics | `INSUFFICIENT_EVIDENCE` | The M3 timing contract freezes case-specific adjusted/unadjusted return distinctions; [bounded reuse map](../reports/m4_stage4a2_m3_bounded_reuse_map_v1.json) identifies principles requiring generalization. | No tracked M4 contract freezes role-specific horizon, predecessor anchor, unit, currency, adjustment policy/version or transform identity for a real study. Real execution remains unauthorized in the [generic-engine contract](../reports/m4_stage4p_m4a_generic_engine_contract_v1.json). |
| Bounded transport proof | `INSUFFICIENT_EVIDENCE` | [Stage 3B-R4 registry](../reports/m3_stage3br4_source_registry_v1.json) and [oil transport contract](../reports/m3_stage3br4_oil_transport_contract_v3.json) show server-bounded requests, raw date scans and holdout rejection. | The proof is case-scoped and depends on external caches. K2 requires explicit `requested_window_only`, response min/max, a proof digest and retained raw bytes whose SHA can be recomputed. |
| License and redistribution | `INSUFFICIENT_EVIDENCE` — **binding blocker** | The [Stage 2G reproducibility contract](stage2g_reproducibility_contract.md) and its [clean-clone acceptance](../acceptance/m2_stage2g2_clean_clone_reproducibility_and_evidence_contract.md) state only the principle that restricted market snapshots remain external. | No tracked provider terms or named license artifact exists; `license_id` is only a proposed field. The acceptance cases explicitly leave license terms, rate limits and redistribution uncovered. A provider cannot be nominated without this disposition. |

## Decision

No tracked combination closes all mandatory classes. M3 artifacts contain useful validation patterns, but they are case-scoped, depend on external raw caches, or include already-consumed holdout evidence. K1 proves only in-memory validation behavior. None may be represented as a verified, selected or execution-safe K2 source.

K2 implementation, provider access, data acquisition, real-source validation, holdout and hypothesis execution remain **BLOCKED**.

## Smallest next task

The next separately authorized stage may be only a **provider-evidence acquisition design v1**. It must freeze, without fetching data:

1. a bounded candidate-provider set per role and evidence class;
2. durable raw-byte retention/serving with recomputable SHA and revision/vintage rules;
3. citation-grade publication/availability requirements;
4. authoritative exchange calendar, suspension and half-day registration;
5. security identity plus per-date membership and `available_at` evidence;
6. explicit bounded-transport proof fields; and
7. a named license/redistribution artifact and fail-closed disposition per provider.

Acquisition and implementation require later, separate authorization.
