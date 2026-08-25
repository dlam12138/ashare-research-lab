# M4 Stage 4P — North-Star v2 Adoption & Generic Research Architecture Preflight

## Status

`COMPLETED — READY_FOR_NORTH_STAR_V2_MERGE_REVIEW`

## Objective

Adopt the user-supplied North-Star v2 as the single canonical North-Star document and freeze the smallest safe M4-A Generic Mechanism Research Engine and M4-B Theory / Hypothesis Registry boundaries. This is governance and architecture preflight only; it does not implement M4 or execute new research.

## Verified baseline

- Base branch: `main` via `origin/main`
- Base commit: `a72b923256a483f2a8d5faefe657ae844dbace19`
- Starting isolated branch: `feat/m4-generic-research-preflight`
- Starting worktree: `D:\量化分析-m4-preflight`
- Existing protected dirty worktree: `D:\量化分析` (not used for checkout/reset/clean/stash-pop)
- North-Star v1 SHA-256: `ad297e609b49bc6f76421ae6b50d213a003f6cec11c964d7da27f20127bd570f`
- North-Star v2 source SHA-256: `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`
- North-Star v2 source: user-provided file `D:\量化分析\A股个股研究与市场机制验证平台-项目北极星-v2.md`, copied byte-for-byte into this isolated worktree. The requested external directory `D:\量化分析-inputs` was absent and is recorded as a deviation.
- M3 production mechanism package, `reports/m3_*`, and `acceptance/m3_*` were inspected from the base and are protected from mutation.

## Allowed scope

- Canonical North-Star v1 → exact user-supplied v2 adoption after audit.
- Minimal README M4 roadmap synchronization.
- Machine-readable Stage4P audit, M3 reuse inventory, M4-A/M4-B contract proposals, architecture decision, future tradability boundary, frozen baseline identity record.
- Governance Goal, acceptance, work record, and focused governance tests.
- Documentation-only commit and test-only commit; CI/PR preparation without merge.

## Forbidden scope

- New real market outcome reads or real research-data acquisition.
- New hypothesis execution, regression, bootstrap, anomaly scan, momentum/value/PEAD A-share return testing, alpha strategy, trading-cost backtest, portfolio optimization, minute-level work, Web UI, or production M4 code.
- Changes to M2/M3 research results, M3 frozen artifacts, M3 production mechanism code, databases, or runtime data.
- Literature full-text acquisition or a real hypothesis registry dataset.

## Required behavior

1. The canonical North-Star is exactly the user v2 input and there is no second canonical v2 copy.
2. The v1 → v2 audit is machine-readable and records preserved boundaries, new governance, scope-conflict checks, and milestone changes.
3. README retains M2/M3 conditional-closeout and M3 disposition evidence and says M4 is preflight-only, implementation not started, and not authorized for execution.
4. M3 reuse inventory classifies the actual mechanism components and keeps PetroChina-specific behavior outside generic core.
5. M4-A is limited to a frozen hypothesis config → validated contract → deterministic plan → bounded execution → reproducible artifacts → evidence disposition flow, with config separate from the frozen research contract and fail-closed gates.
6. M4-B stores provenance and candidate metadata only, with an explicit state machine separating literature from A-share evidence.
7. At most three candidate classes are named for representation testing; no real outcomes, parameters, or effectiveness claims are produced.
8. Economic significance and tradability remain a future, separately authorized boundary.

## Required tests and validation

- Focused Stage4P governance tests and North-Star consistency tests.
- M3 boundary/protected artifact tests.
- Full `pytest`.
- `ruff check .`.
- `python -m compileall src tests`.
- `git diff --check`.
- JSON parse/schema-shape validation for all new reports.
- Exact-byte frozen M3 identity comparison.

## Acceptance criteria

- `acceptance/m4_stage4p_north_star_v2_adoption_and_architecture_preflight.md` is satisfied.
- Required Stage4P reports exist and validate.
- North-Star v2 adoption and v1 → v2 audit pass.
- README is synchronized without changing M1–M3 evidence.
- M3 mechanism package and frozen M3 artifacts have zero diff from baseline.
- No real outcome/data acquisition or production M4 implementation occurred.
- Branch is committed and pushed; CI/PR evidence is recorded if the available GitHub workflow permits it.
- Final decision is `M4_STAGE4P_NORTH_STAR_V2_ADOPTION_PASS` only if all checks pass, followed by `STOP_FOR_NORTH_STAR_V2_FINAL_MERGE_REVIEW`.

## Stop conditions

- `M4_STAGE4P_MAIN_MOVED` for an unknown functional/research change on `origin/main`.
- `M4_STAGE4P_NORTH_STAR_V2_INPUT_MISSING` if the only user-provided v2 source cannot be verified.
- `M4_STAGE4P_NORTH_STAR_SCOPE_CONFLICT` if v2 authorizes forbidden trading/research automation.
- `M4_STAGE4P_RESEARCH_CODE_MUTATION` if protected M3 code or artifacts change.
- Any new real outcome/data acquisition or production M4 implementation.
- Any failed frozen identity, governance, or required validation gate.

## Commit/push requirements

- Target branch: `feat/m4-generic-research-preflight`.
- Preferred commits:
  1. `docs: adopt North-Star v2 for generic research`
  2. `test: lock M4 preflight governance boundaries`
- Push the feature branch only; never push directly to `main`, force-push, or merge.
- Create a PR targeting `main` only when credentials/tooling are available; do not merge it.

## Completion

- Stage4P governance preflight is complete and all required acceptance gates passed.
- North-Star v2 SHA-256 remains `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- Architecture remains `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`.
- M4-A and M4-B preflights are complete; production implementation and real research execution remain not started and not authorized.
- Final disposition is `M4_STAGE4P_NORTH_STAR_V2_ADOPTION_PASS`.
- `STOP_FOR_NORTH_STAR_V2_FINAL_MERGE_REVIEW`.
