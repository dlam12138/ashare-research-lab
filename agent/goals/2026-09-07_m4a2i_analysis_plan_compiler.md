# Goal: M4-A.2I analysis plan compiler

## Objective and verified baseline
User authorized squash merge #8 then #7 and compile-only implementation followed by a PR.
Verified remote main a0a7c13ee47057abf5e40a96a616baf78451774e and exact approved PR
heads 997a769fd645102b05043926098ff4f24d7b77b6 / 36f3466e0e960d1761e57c4ab6b0e59f9dfd6888;
each had 42 passing checks. Squash commits: #8 69657ac14a94d7ec98021e1af0fbc14f00e834b4,
#7 349101a1bae61dc4a11991e2420d21eedb69ff87. Second merge adds only six frozen design files.
Implementation base is origin/main 349101a1bae61dc4a11991e2420d21eedb69ff87,
branch codex/m4a2i-analysis-plan-compiler, isolated D:/量化分析-m4a2i.

## Scope and required behavior
Add mechanism/planning with immutable DeterministicAnalysisPlan, build_analysis_plan,
plan_to_canonical_dict, serialize_analysis_plan, compute_plan_digest, validate_analysis_plan.
Follow reports/m4_stage4a2_deterministic_analysis_plan_design_v1.json mechanically.
Strict A.1 contract validation; deterministic semantic roles, ordered controls, canonical
identity and defensive conversion; holdout execution_authorized is always false.
Add synthetic boundary/identity tests, README current capability/API changes and only
related existing documentation assertions. One Goal, work record and acceptance file.

## Forbidden scope and protection
No A.1/schema/M3-source/North-Star/frozen-research/design changes, new dependencies,
workflow, CLI, data adapter, provider, fitting, bootstrap execution, executor or real research.
No hash-baseline changes. Preserve all existing branches/worktrees/stash/runtime/DB.
Original dirty M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222 stays untouched;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f;
DB SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Tests and exact commands
Test complete design mapping; A/B, key and cwd invariance; fixed synthetic identity;
sensitivity to ordered controls/condition/window/quality/bootstrap/robustness/holdout;
deep immutability; defensive copies; malformed and forged contracts/plans; absent optional
sections; no file/data/network/statistical calls during compilation.
In this worktree's isolated environment:
```text
python -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
python -m pytest -q
python -m ruff check src/ tests/
python -m compileall -q src tests
git diff --check
```
Run full suite once stable; rerun relevant checks only for later changes/failures.

## Acceptance and stop
Both prior PRs merged and final main CI green; deterministic compile-only implementation
passes local validation and new PR CI. Independently inspect final diff, HEAD, untracked
files, protected bytes/DB/stash and remote synchronization. Few scoped commits, ordinary
feature push, one PR to main. Put final CI in PR body, no evidence-only CI commit loop.
Final verdict PASS / CHANGES_REQUIRED / BLOCKED. Stop BEFORE new PR merge;
dataset adapter, executor and real hypothesis execution remain unauthorized.
