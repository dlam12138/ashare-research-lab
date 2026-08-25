# M4 Stage 4A.1R Goal — Post-Merge README Status Canonicalization

## Status

`COMPLETED — READY_FOR_M4A1R_MERGE_REVIEW`

## Objective

Repair only README current-status wording after M4 Stage 4A.1 was
canonicalized on main. Preserve M3 closeout statements as historical facts and
make the current M4 roadmap accurately state that M4 is in progress, M4-A.1 is
canonical on main, and M4-A.2/M4-B remain not started.

## Verified baseline

- Base: `dc0af0955eed7c53fb07a74e4dec6bbb32d486f7`.
- Worktree: isolated clean `D:\量化分析-m4a1r`.
- North-Star v2 SHA-256:
  `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- M4-A.1 implementation, reports, M3 protected scope, and Stage4P artifacts
  were inspected before changes.

## Allowed and forbidden scope

Allowed: `README.md`, this Goal, the matching Acceptance and Work Record, and
one narrowly scoped README status regression test.

Forbidden: implementation, reports, North-Star revision, M4-A.2, M4-B, M3 or
M2 changes, workflow changes, dependencies, and real research execution.

## Required current facts

- M1 completed; M2 conditionally closed; M3 conditionally closed.
- Stage4P complete; North-Star v2 canonical.
- M4 in progress; architecture remains
  `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`.
- M4-A.1 canonical on main; M4-A.2, M4-A dataset adapter, M4-A analysis plan,
  M4-A executor, and M4-B not started.
- Real hypothesis execution, anomaly research, economic-significance research,
  portfolio/alpha research, M5, and M6 remain unauthorized.

## Acceptance and stop

The README historical M3 wording, current M4 roadmap, and next-review boundary
must be explicit without changing frozen technical artifacts. Stop at
`STOP_FOR_M4A1R_MERGE_REVIEW`; do not start M4-A.2.
