# M4 Stage 4A.1R Work Record — Post-Merge README Status Canonicalization

## Status

`COMPLETED — READY_FOR_M4A1R_MERGE_REVIEW`

## Baseline and scope

- Base: `dc0af0955eed7c53fb07a74e4dec6bbb32d486f7`.
- Branch: `docs/m4a1r-readme-status-canonicalization`.
- Worktree: isolated `D:\量化分析-m4a1r`.
- Scope: README current-status canonicalization only, plus one scoped
  regression test and the matching governance artifacts.
- No M4-A.2, M4-B, implementation, North-Star, M3, M2, workflow, data, or
  research changes were authorized or made.

## Stale wording and repair

Before:

- M3 closeout paragraph said `M4 are not authorized` without a historical
  time qualifier.
- Milestone 4 roadmap said `PREFLIGHT ONLY; IMPLEMENTATION NOT STARTED`.

After:

- The M3 statement is explicitly marked `At M3 closeout`, and its historical
  stop remains `STOP_FOR_NORTH_STAR_REVIEW`.
- A current-status clarification records Stage4P complete, M4 in progress,
  and M4-A.1 canonicalized on main.
- The roadmap records M4-A.2 and M4-B not started and real hypothesis
  execution not authorized.

## Protected identity

- North-Star v2 SHA before/after:
  `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- `hypothesis_config.py`, `contract_compiler.py`, both Stage4A1 reports, and
  the Stage4P architecture report are byte-identical before/after.
- M3 protected files, reports, acceptance, and Stage4P contracts are
  unchanged.
- No real data, provider, network, or research execution was used.

## Validation

- README regression is covered by the existing Stage4P governance test.
- Focused README/A.1/Stage4P/M3/M2 governance suite: `86 passed`.
- Full pytest: `2309 passed, 4 skipped, 2 existing pandas date-format warnings`.
- `ruff check .`: PASS.
- `python -m compileall -q src tests`: PASS.
- `git diff --check`: PASS.
- Stage4A1 JSON validation, North-Star SHA validation, implementation identity,
  and protected identity checks: PASS.
- Feature CI and PR evidence will be reported in the final handoff after the
  ordinary push; no merge is authorized in this stage.

## Final stop

`STOP_FOR_M4A1R_MERGE_REVIEW`
