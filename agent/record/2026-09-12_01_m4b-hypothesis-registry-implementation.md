# M4-B hypothesis registry implementation record

Date: 2026-09-12. Executor: DSH-assisted implementation. Reviewer: Codex.

## Contract and baseline

- Goal: `agent/goals/2026-09-12_m4b_hypothesis_registry_implementation.md`.
- Worktree/branch: `D:/量化分析-m4b-registry-implementation` /
  `codex/m4b-hypothesis-registry-implementation`.
- Verified base: `origin/main@7fec2c137123150ded1fc2c1144116e19982444c`.
- Goal commit: `d4229f5b90a992b0f67f74a4ad567cf4ce224bd6`.
- Frozen design, acceptance and Stage4P blobs remained
  `6d9c292001c09a4b1a8e895e54619dc1e8826f3d`,
  `4a9b227204fc1c0eabc28e1e8b3d60a53c46f0b2`, and
  `dfd41eaafc099e7748499f72de7ddd800bf97f69`.

## Delivery

Implemented the four-module `ashare_research.mechanism.registry` subpackage: immutable 26-key
records, canonical bytes and double digests, strict fail-closed validation, the closed 12-state /
20-edge transition machine, immutable bounded snapshots and registry digests. The public surface
contains the 13 frozen functions plus the frozen supporting types/constants/error.

The implementation is in-memory and metadata-only. It contains no persistence, provider, network,
filesystem, real candidate, literature acquisition, real market data, holdout, backtest, ranking,
promotion or statistical execution path. README states those boundaries explicitly.

## DSH usage and review findings

DSH independently read and verified the Goal, baseline and both normative documents. Two headless
implementation attempts exhausted their useful work in detailed design reasoning without safely
writing files, so Codex stopped them and implemented from their field/state/error analysis. A later
DSH diff review identified concrete gaps: missing `MODEL`/`AI`/`MEMORY` forbidden-source markers,
an incomplete frozen outcome-key superset, and the illegal-edge versus authorization first-error
case. Codex corrected all three before final validation. DSH did not create a commit.

## Validation evidence

Commands were executed independently with `PYTHONPATH=<worktree>/src`, the shared interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`, and `-p no:cacheprovider` for pytest.

| Command group | Result |
| --- | --- |
| `pytest ... tests/test_m4b_hypothesis_registry.py` | PASS, 24 passed |
| `pytest ... tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | PASS, 15 passed after the required evidence link was created |
| `pytest ... tests/test_m4_bounded_execution.py` | PASS, 49 passed |
| five-file upstream M4 regression group from the Goal | PASS, 255 passed |
| `ruff check` on the frozen changed source/test scope | PASS |
| `git diff --check` and Markdown/link hygiene | PASS |

The first governance run had one expected evidence-order failure because README already linked the
still-to-be-created acceptance file. After this file and the acceptance file were created, the same
command passed without changing or weakening any protective gate.

## Deviations and residual boundaries

- DSH did not produce the delivery commit; Codex owns final review and the local delivery commit.
- The frozen V2 exact-key rule necessarily reports `UNKNOWN_RECORD_FIELD` before the V8 category
  for any extra top-level/nested key. The implementation preserves that explicitly frozen
  V1–V12 order while retaining the complete V8 forbidden-key sets and scans.
- No real M4-B candidate or execution is authorized. Push, PR, merge and the next stage are outside
  this Goal and remain stopped pending the independent verdict and user authorization.
