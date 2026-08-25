# M4 Stage 4P Acceptance — North-Star v2 Adoption & Generic Research Architecture Preflight

## Decision

`M4_STAGE4P_NORTH_STAR_V2_ADOPTION_PASS` is attainable only when every gate below is true. This document records preflight acceptance criteria; it does not authorize M4 implementation or real research execution.

## Gates

- [x] North-Star v2 was adopted byte-for-byte from the verified user input; the canonical file has SHA-256 `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- [x] The v1 → v2 machine-readable audit is `PASS`; preserved M1–M3 governance boundaries and new v2 governance are recorded.
- [x] There is one canonical North-Star path; the temporary copied `-v2.md` source was removed from the isolated worktree after adoption.
- [x] README says M4 is `PREFLIGHT ONLY; IMPLEMENTATION NOT STARTED` and does not change M2/M3 evidence or dispositions.
- [x] M1–M3 protected report/acceptance aggregate and M3 mechanism-package aggregate remain byte-identical to the base manifest.
- [x] M4-A contract is frozen at the daily conditional/controlled mechanism slice and keeps config separate from the frozen research contract.
- [x] M4-B contract is frozen as provenance/candidate metadata and state governance only; literature is not local A-share evidence.
- [x] Reuse inventory covers the actual mechanism package, M3 tools, and M3 tests; PetroChina-specific logic is kept outside generic core.
- [x] Future tradability/economic-significance boundary is frozen as separately authorized and currently not allowed.
- [x] No new real outcome, real research-data acquisition, hypothesis execution, anomaly scan, regression/bootstrap, or production M4 code occurred.

## Required evidence

- `reports/m4_stage4p_north_star_v2_adoption_audit_v1.json`
- `reports/m4_stage4p_m3_component_reuse_inventory_v1.json`
- `reports/m4_stage4p_m4a_generic_engine_contract_v1.json`
- `reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json`
- `reports/m4_stage4p_future_tradability_boundary_v1.json`
- `reports/m4_stage4p_architecture_decision_v1.json`
- `reports/m4_stage4p_frozen_m1_m3_identity_v1.json`
- `agent/goals/2026-08-24_m4_stage4p_north_star_v2_adoption_and_architecture_preflight.md`
- `agent/record/2026-08-24_Stage4P_north_star_v2_adoption_and_architecture_preflight.md`

## Explicit non-acceptance

Acceptance does not authorize `M4-A` implementation, `M4-B` schema implementation, real candidate collection, paper download, A-share momentum/value/PEAD testing, anomaly research, economic-significance research, portfolio alpha research, M5, M6, merge, or deployment.

## Stop

`STOP_FOR_NORTH_STAR_V2_MERGE_REVIEW`
