# Acceptance: M4-A.2I analysis plan compiler

Status: LOCAL_PASS — final remote CI and delivery HEAD are recorded in the implementation PR.
Goal: [contract](../agent/goals/2026-09-07_m4a2i_analysis_plan_compiler.md).
Record: [operations](../agent/record/2026-09-07_01_m4a2i-analysis-plan-compiler.md).
Verified main merges: #8 69657ac14a94d7ec98021e1af0fbc14f00e834b4;
#7 / implementation base 349101a1bae61dc4a11991e2420d21eedb69ff87.
Branch: `codex/m4a2i-analysis-plan-compiler`, isolated `D:/量化分析-m4a2i`.
Implementation/test commit: `745fffe28494e41e169c95a004241160ee47730a`.
The delivery HEAD is the commit containing this packet plus README/status assertions;
its exact SHA is recorded in the PR body after push to avoid a self-referential commit hash.

## Implemented behavior
Five public functions in `ashare_research.mechanism.planning` compile, validate, digest,
copy and serialize immutable `DeterministicAnalysisPlan` objects. The source contract is
validated by A.1 and a strict structural/semantic recheck; noncanonical input is rejected.
Dataset roles, control order, condition, development/quality boundaries, bootstrap policy,
robustness order and evidence rules mechanically follow the frozen design. Bootstrap
contains no sample-derived block length. Holdout always has execution_authorized=false.
No adapter, provider, regression, statistical execution, dependency or CLI was added.

## Exact validation and results
Commands executed from the isolated worktree with Python 3.13.9 and `pip install -e '.[dev]'`:

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | 132 passed in 2.29s |
| `.venv/Scripts/python.exe -m pytest -q` | 2486 passed, 4 skipped, 2 existing pandas date-parse warnings in 479.70s |
| `.venv/Scripts/python.exe -m ruff check src/ tests/` | All checks passed |
| `.venv/Scripts/python.exe -m compileall -q src tests` | Exit 0 |
| `git diff --check` and `git diff --cached --check` | Exit 0 |

Full suite ran once after implementation stabilized. New suite adds 67 tests covering
complete design mapping, A/B and cwd/key-order invariance, immutable nested structures,
defensive copies, digest tampering, rehashed invalid semantics, ordered control/registry
identity, all condition operators, empty controls/registry, disabled bootstrap, optional
holdout, and compilation without file/network/statistical calls. Initial new-test run had
one unfilled golden-placeholder failure; no product assertion was weakened to pass.

## Fixed synthetic identities
Fixture: `_document()` from existing A.1 tests, without holdout.

- Source contract: `ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457`.
- Plan digest: `45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981`.
- Serialized bytes SHA256: `c2c2ea0bd541fb2640f47d5286af0a9121acbb77861ac1b363480a10773a9182`.

The existing Windows/Linux full-test matrix checks these fixed identities without a new workflow.

## Protected evidence
- Existing Stage4P aggregate gates pass unchanged: 194 M1/M2/M3 artifacts,
  aggregate `7a147f62224732a31b35a545c5286c235e1702aff63d9baddcf17dcdd7b4e46a`;
  85 M3 artifacts, `c4c9d52fc14a2dcb53efc7f59bc01824dbaf58c5ce3891ed5abe5f0c0768eb48`;
  21 protected M3 modules, `733f14bf7b060b6e1b1131f1219708b1ca7d6a0e46764fe9b763b6fb651dd625`.
- North-Star SHA256 remains `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- A.1 source/schema, reports, old acceptance, pyproject and workflows have no diff from base.
  Merged design files have no diff from approved #7 HEAD. No protection hashes changed.
- Original M2 HEAD remains `3679b1bac7a1634c6452784a4d8f6d139966f222`; original modified
  acceptance and all untracked files remain. Seven original worktrees and branches retained.
- Stash remains `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` (one entry).
- Original DB SHA256 remains `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
  This implementation tree has no default research.duckdb. Ignored venv/test output retained.

## Main and remote verification
Both prior PRs were squash merged with exact approved HEAD guards, no branch deletion.
After #8 its tree equaled the approved head; #7 then introduced exactly its six files.
Final origin/main and GitHub main equal `349101a1bae61dc4a11991e2420d21eedb69ff87`;
all seven main workflows succeeded, **21/21 checks**.
The pre-existing local `main` ref remains `9e016e772156fe689cbf77ed1febd772833c830e`,
intentionally retained; implementation uses fetched origin/main. Only the new feature
branch is pushed. Final feature local/origin/remote equality and CI are audited in PR body.

## Changed files and stop
- `src/ashare_research/mechanism/planning/__init__.py`
- `src/ashare_research/mechanism/planning/compiler.py`
- `tests/test_m4_stage4a2i_analysis_plan.py`
- `README.md`
- `tests/test_project_entry.py`
- `tests/test_m4_stage4p_governance.py` (current README status only)
- This acceptance file, its linked Goal and work record.

No scope deviations or unresolved local failures. Digest validation is content identity,
not cryptographic authorization; dispatch plans do not prove executor availability.
Stop: new implementation PR review, before merge. Dataset adapter, executor, M4-B and
real hypothesis execution remain unauthorized. Final verdict requires final PR CI success.
