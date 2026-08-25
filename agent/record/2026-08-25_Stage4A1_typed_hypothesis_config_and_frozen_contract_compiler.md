# M4 Stage 4A.1 Work Record — Typed Hypothesis Config & Frozen Contract Compiler

## Status

`COMPLETED — READY_FOR_M4A1_MERGE_REVIEW`

## Basic information

- Date: 2026-08-25
- Agent: Codex
- Branch: `feat/m4a1-typed-hypothesis-contract`
- Worktree: `D:\量化分析-m4a1`
- Starting commit: `7a6668d8a683d02eabd9a860d19546fd163a20c1`
- Task source: user-supplied M4 Stage 4A.1 implementation contract
- Module: mechanism validation / typed contract infrastructure

## Task contract

### Objective

Build `HypothesisConfig -> strict validation -> FrozenMechanismContract ->
canonical serialization -> deterministic digest` for synthetic configurations
only, without changing M3 research behavior.

### Verified baseline

- `origin/main` equals the mandated canonical SHA
  `7a6668d8a683d02eabd9a860d19546fd163a20c1`.
- Isolated clean worktree created at `D:\量化分析-m4a1`.
- The protected dirty M2 worktree `D:\量化分析` was not modified.
- Existing stash in the protected worktree was not touched.
- North-Star SHA-256 is
  `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- Stage4P architecture is `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`.
- Existing `model_digest.canonical_digest` is the repository’s canonical
  digest helper and will be reused.

### Allowed scope

- Additive typed config and compiler modules under
  `src/ashare_research/mechanism/`.
- Focused synthetic tests, Stage4A.1 governance artifacts, and minimal README
  status wording if required.
- Minimal `mechanism/__init__.py` public API delta only if justified.

### Forbidden scope

- Real data, real symbols, providers, network, outcomes, regressions,
  bootstrap execution, robustness execution, holdout execution, or research
  inference.
- Dataset adapter, analysis plan, executor, CLI execution, M4-B registry,
  literature, anomaly search, portfolio, recommendation, M5, M6.
- New dependency.
- Mutation of pre-existing M3 mechanism code or frozen M3 artifacts.

### Required tests / validation

Focused Stage4A.1 tests; Stage4P and M3 boundary tests; full pytest; Ruff;
compileall; diff check; JSON validation; protected baseline identity checks;
static no-network/no-execution checks; cross-path semantic identity test.

### Acceptance / stop conditions

Acceptance requires strict typed validation, immutable contract values,
canonical semantic identity, deterministic digest, synthetic-only proof, and
unchanged M3 behavior. Stop if main moves unexpectedly, a dependency or M3
rewrite is required, deterministic identity fails, real data is read, or
required CI fails.

### Commit / push

Use a small reviewable commit set, ordinary push of the feature branch only,
and stop at `STOP_FOR_M4A1_MERGE_REVIEW`; do not merge.

## Initial state and inspected governance

- Read `agent/agent.md`, `agent/record/README.md`, `CLAUDE.md`, `README.md`,
  the canonical North-Star, Stage4P architecture/contract/reuse/tradability
  reports, `model_digest.py`, the Stage4P governance test, and recent work
  records.
- Stage4P freezes the architecture as
  `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE` and the first paradigm as
  `daily_conditional_controlled_mechanism_research`.
- Stage4P explicitly says production implementation was not started before
  this task and real execution remains unauthorized.

## Implementation plan

1. Implement small stdlib/PyYAML typed schema and stable validation errors.
2. Implement compiler, immutable frozen representations, canonical JSON, and
   reuse of `model_digest.canonical_digest`.
3. Add focused synthetic tests and governance artifacts.
4. Run local validation and audit protected files/diff/synchronization.
5. Commit, push, and stop for merge review.

## Design decisions recorded before implementation

- Use frozen dataclasses plus enums and tuples; no schema framework is needed
  for this bounded allow-list.
- Treat input mappings as a strict external boundary and expose typed config
  objects separately from compiled contract objects.
- Canonicalize all contract semantics into JSON-compatible immutable/value
  representations; normalize `Decimal(str(value))` to plain decimal strings,
  reject non-finite values, and normalize negative zero to `0`.
- Preserve declared control and robustness order because order is semantic;
  reject duplicates rather than sorting or auto-selecting.
- Reuse `model_digest.canonical_digest` for contract identity rather than
  introducing a second hash algorithm.
- Keep all compiler operations pure and synthetic; no provider/data imports or
  calls are allowed.

## Actual operations

- Verified protected worktree branch, HEAD, remote, stash, and dirty state.
- Fetched `origin --prune` and verified `origin/main` against the mandated
  canonical SHA.
- Created clean worktree and feature branch from `origin/main`.
- Read applicable governance files and Stage4P reports before code changes.

## Data and method boundary

- No data source, provider, external file, network acquisition, real target,
  real outcome, or statistical execution is authorized or used.
- All fixtures and evidence will use synthetic identities only.

## Validation

- `PYTHONPATH=src pytest -q tests/test_m4_stage4a1_typed_contract.py` — PASS,
  50 passed.
- `PYTHONPATH=src pytest -q tests/test_m4_stage4a1_typed_contract.py
  tests/test_m4_stage4p_governance.py` — PASS, 63 passed.
- `PYTHONPATH=src pytest -q tests/test_m4_stage4a1_typed_contract.py
  tests/test_m4_stage4p_governance.py tests/test_m3_stage3a_mechanism_preflight.py`
  — PASS, 73 passed.
- `PYTHONPATH=src python -m pytest -q` — PASS, 2309 passed, 4 skipped, 2
  existing pandas date-format warnings.
- `ruff check .` — PASS.
- `python -m compileall -q src tests` — PASS.
- `git diff --check` — PASS.
- PowerShell JSON parsing of both Stage4A.1 reports — PASS.
- Synthetic proof — PASS: A/B semantic config digest, contract digest,
  canonical dict, serialized bytes, and output SHA were exactly equal; six
  meaningful mutation cases changed the digest.
- Stage4P/M3 protected identity — PASS: all pre-existing M3 mechanism files
  remain byte-identical; only the two approved additive A.1 modules are new.

The first full-suite run found the expected stale file-count assertion in the
M3 preflight boundary. It was corrected additively to allow exactly
`hypothesis_config.py` and `contract_compiler.py`; the rerun passed in full.

## Result

Typed config, strict parser, compiler, immutable frozen contract, canonical
serialization, semantic config digest, contract digest, focused tests, and
synthetic evidence are complete. The implementation is compile-only and
synthetic-only. M4-A dataset/plan/executor and M4-B remain not started.

## Remaining issues

- No implementation blocker remains.
- PR #5 is open and unmerged.
- Merge requires separate final merge review.
- Existing pandas date-format warnings remain unchanged and are outside this stage.

## Final remote evidence

- Feature branch: `feat/m4a1-typed-hypothesis-contract`.
- Implementation candidate HEAD: `3f5ef9891369c686d98ef3bc66f92da3c1fad97a`.
- Origin synchronization: `0 / 0` (`HEAD...origin/feat/m4a1-typed-hypothesis-contract`).
- PR: [#5](https://github.com/dlam12138/ashare-research-lab/pull/5).
- PR state: `OPEN`; merged: `NO`; draft: `NO`.
- PR base: `main`.
- PR head: `feat/m4a1-typed-hypothesis-contract`.
- PR head SHA: `3f5ef9891369c686d98ef3bc66f92da3c1fad97a`.
- Mergeability: `MERGEABLE`; merge state: `CLEAN`.
- Exact-tip CI: `PASS`; required checks: `42 / 42 SUCCESS`.

Candidate-tip workflow runs, all at the implementation candidate HEAD and all
successful:

| Run ID | Workflow | Event | Head SHA | Conclusion |
| --- | --- | --- | --- | --- |
| `32818118234` | M3 Integration Closeout | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818118192` | M3 Stage 3C-A-R2 digest identity | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818118128` | M3 Stage 3C-B pre-execution lock | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818118197` | M3 Stage 3C-C pre-robustness lock | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818118200` | M3 Stage 3D-A frozen OOS contract | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818118136` | M3 Stage 3D-B pre-unseal holdout lock | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818118289` | Stage 2G reproducibility | `push` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144433` | M3 Integration Closeout | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144439` | M3 Stage 3C-A-R2 digest identity | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144425` | M3 Stage 3C-B pre-execution lock | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144492` | M3 Stage 3C-C pre-robustness lock | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144443` | M3 Stage 3D-A frozen OOS contract | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144367` | M3 Stage 3D-B pre-unseal holdout lock | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |
| `32818144495` | Stage 2G reproducibility | `pull_request` | `3f5ef9891369c686d98ef3bc66f92da3c1fad97a` | `success` |

The seven workflow runs above produced the Windows, Ubuntu, and
`identity-compare` jobs; all 42 reported checks were successful. Cross-platform
identity: `PASS`; Windows: `PASS`; Ubuntu: `PASS`; `identity-compare`: `PASS`.
This section records the original candidate-tip evidence; a governance repair
tip will require a new exact-tip CI confirmation after the ordinary push.

## Final file changes

- `src/ashare_research/mechanism/hypothesis_config.py` — added.
- `src/ashare_research/mechanism/contract_compiler.py` — added.
- `tests/test_m4_stage4a1_typed_contract.py` — added.
- `tests/test_m4_stage4p_governance.py` — additive A.1 allowed-file boundary.
- `tests/test_m3_stage3a_mechanism_preflight.py` — additive A.1 allowed-file boundary.
- `reports/m4_stage4a1_typed_config_and_compiler_contract_v1.json` — added.
- `reports/m4_stage4a1_synthetic_compile_identity_v1.json` — added.
- `acceptance/m4_stage4a1_typed_hypothesis_config_and_frozen_contract_compiler.md` — added.
- This Goal and work record — updated.
- No README update was needed; existing M4 preflight wording remains consistent
  with the explicit no-execution boundary.

## Final Git state

- Final branch before push: `feat/m4a1-typed-hypothesis-contract`.
- Last validation commit: `7088ce4`.
- Governance evidence commit: `d0098fe`.
- The final metadata commit contains this record update; its exact HEAD is
  captured in the final handoff after commit.
- Four local commits were ahead of `origin/main` before this metadata update.
- Worktree was clean after `d0098fe` before this metadata update.
- Protected M2 worktree and its stash were not touched.
- Implementation candidate HEAD is `3f5ef9891369c686d98ef3bc66f92da3c1fad97a`.
- Final governance repair is verified against the current branch tip after the
  documentation-only change; the repair tip is reported in the final handoff
  to avoid a self-referential record update.

## Final boundary

- `M4A1_TYPED_HYPOTHESIS_CONFIG = IMPLEMENTED`
- `M4A1_FROZEN_CONTRACT_COMPILER = IMPLEMENTED`
- `M4_DATASET_ADAPTER = NOT_STARTED`
- `M4_ANALYSIS_PLAN = NOT_STARTED`
- `M4_EXECUTOR = NOT_STARTED`
- `M4B = NOT_STARTED`
- `REAL_DATA_READ = NO`
- `REAL_OUTCOME_READ = NO`
- `NETWORK_ACQUISITION = NO`
- `REAL_HYPOTHESIS_EXECUTION = NO`
- `REAL_ANOMALY_RESEARCH = NOT_AUTHORIZED`
- `ALPHA / PORTFOLIO = NOT_AUTHORIZED`
- `final stop = STOP_FOR_M4A1_FINAL_MERGE_REVIEW`
