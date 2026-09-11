# Acceptance: M4 dataset adapter design

Verdict: PASS (design delivery only).

## Scope and baseline
User approved PR #9 squash merge and next dataset adapter design. This delivery is
design only; it contains no adapter or executor implementation.
Goal: [contract](../agent/goals/2026-09-07_m4_dataset_adapter_design.md).
Record: [work log](../agent/record/2026-09-07_02_m4-dataset-adapter-design.md).
Normative design: [specification](../docs/m4_dataset_adapter_design_v1.md).
Future acceptance: [synthetic scenarios](../docs/m4_dataset_adapter_acceptance_cases_v1.md).

- Approved PR head: 13a441ffc0deedc6cc49001d3009e8aaa5442628, 42 successful checks.
- Squash/base: origin/main bab24f981fef9336b84280544ce709702b9df116.
- `git diff --exit-code 13a441ffc0deedc6cc49001d3009e8aaa5442628 origin/main`:
  exit 0 immediately after merge; identical tree.
- Design branch: codex/m4-dataset-adapter-design in D:/量化分析-m4-adapter-design.
- Only five new Markdown documents: this acceptance, linked Goal, work log, specification
  and scenario matrix. All pre-existing tracked files are byte-identical to base.

## Reviewed decisions
1. Retain original frozen contract alongside plan; exact recompile comparison prevents
   losing outcome horizon/identity semantics or accepting a merely rehashed plan.
2. Explicit synthetic date domain and calendar/membership evidence fix the denominator
   independently of observed rows. Missing days never silently disappear.
3. Every role binds semantics, source identity and availability. Hashes prove synthetic
   consistency only; real provenance and timing validation require separate design.
4. Separate structural errors from retained quality gaps; require complete valid rows,
   exact coverage arithmetic and no execution authorization even for ready datasets.
5. Keep immutable canonical output and original M3 contracts/modules unchanged.

The matrix covers positive behavior, quality boundaries, forgery, holdout rejection,
unsupported semantics, deterministic identity and no-IO behavior. It records expected
future results explicitly; no adapter tests or dataset digest are claimed to exist.

## Actual validation
From the design worktree:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
git diff --check
git diff --cached --check
```
Focused tests: 132 passed in 0.82s, including frozen North-Star/M1/M2/M3 protection
checks. Interpreter module-path check confirmed this worktree's source was imported,
not the other worktree's editable installation. No dependency install was needed.
No local full-suite rerun: only additive Markdown is changed.

- Inline Python document audit: 5 UTF-8 files, 7 valid local links, balanced code fences,
  policy names matched to A.1 source; exact arithmetic confirms 2/3 passes 0.66 but fails
  0.67. Passed. The scenario matrix remains a specification, not an implemented test.
- `git diff --check` and `git diff --cached --check`: exit 0.
- `git diff bab24f981fef9336b84280544ce709702b9df116 --exit-code -- src tests reports README.md pyproject.toml .github`:
  exit 0. Staged name-status contains exactly five additions.
- Main commit bab24f9: seven successful workflows, **21/21 successful checks**,
  inspected using `gh run list --branch main --commit bab24f981fef9336b84280544ce709702b9df116 --json databaseId,status,conclusion,workflowName`
  and the GitHub commit check-runs API.
- [Main full-suite and identity workflow](https://github.com/dlam12138/ashare-research-lab/actions/runs/34134084010):
  Linux **2487 passed, 3 skipped, 3 warnings** (152.48s); Windows **2487 passed,
  3 skipped, 2 warnings** (394.58s). Cross-platform identity comparison passed.
  Counts come from this run's actual logs, not the previous PR acceptance counts.

## Protected state and stop
Original M2 HEAD remains 3679b1bac7a1634c6452784a4d8f6d139966f222 with its existing
acceptance edit and untracked files. Stash remains cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
Original DB SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Existing branches/worktrees and ignored data preserved. No source, tests, reports,
North-Star, workflow, dependency, README or protected hash baseline changed.

New design is local-only; no feature push, PR creation or merge of this design is
authorized by this task. PR #10 was not merged. Stop before adapter implementation,
executor, provider binding, real data or research execution. The existing README's
PR-relative wording remains inherited from #9; its post-merge wording is not changed
in this additive design task. Current exact capability is documented here.

## Delivery identity
One local commit contains these five documents; use this file's containing commit
or `git rev-parse codex/m4-dataset-adapter-design` for its exact SHA, also reported in
the final response. No self-referential commit hash is inserted into its own content.
origin/main and live remote main equal bab24f9. Pre-existing local main remains
9e016e772156fe689cbf77ed1febd772833c830e intentionally. The new design branch is one
local commit ahead of its main baseline and has no remote feature branch.
No unresolved design blocker; real provenance, multi-horizon inputs and the executor
are explicit future scopes. Proceeding to implementation requires separate authorization.
