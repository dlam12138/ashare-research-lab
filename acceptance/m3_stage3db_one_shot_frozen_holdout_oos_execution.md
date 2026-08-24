# M3 Stage 3D-B — Holdout OOS Execution Acceptance

## Verdict

M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP

The frozen primary was not executed. No regression, bootstrap, gamma, or A/B
execution result exists because the authorized market input capsule did not meet
the frozen all-eligible-universe and 0.99 coverage gate.

## Boundary evidence

- Pre-unseal exact-head CI passed at `73630f6660528a0fbcc8868869a2e0eb955af6a4`.
- Immutable marker: `D:/m3_stage3db_holdout/holdout_unseal_event.json`.
- The first Baostock compact-date transport attempt returned an empty calendar
  response and no target rows; it was preserved and not overwritten.
- A runtime-only ISO-date transport retry obtained 897 target qfq rows in the
  separate capsule `D:/m3_stage3db_holdout_retry`.
- AKShare market acquisition obtained 2,310 daily files for a 2,458-code
  master-plus-delist eligible union. 148 codes repeatedly returned empty/non-JSON
  responses (`JSONDecodeError: No value to decode`).
- The 0.99 coverage gate therefore failed closed. No subset proxy was normalized.
- FRED and CNI were not requested after the market coverage failure.

## Governance boundary

Stage 3C-B and Stage 3C-C conclusions remain unchanged. The development primary
remains not established, registered robustness remains completed without stable
positive support, and no evidence level is assigned. No alternative proxy,
threshold, robustness search, minute-level escalation, causal interpretation, or
new development research is authorized.

See `reports/m3_stage3db_oos_analysis_input_manifest_v1.json` for source hashes,
row counts, raw capsule digest, and the exact technical gap.
