# M4 synthetic demonstration CLI acceptance

Local verdict: PASS. Hosted publication/check/merge gate pending at this commit;
final handoff must independently report actual head, checks and merge identity.
This usability task grants no next research stage or real-data authorization.

Goal: agent/goals/2026-10-01_m4_synthetic_demo_cli.md.
Verified base origin/main and live remote main:
c1b68a4772f420ad9392e7d33de25be6fa71220a.
Branch codex/m4-synthetic-demo-cli, clean owned worktree before task.
Earlier email evidence branches retained without changing their commits.

## Six-file scope and behavior

- src/ashare_research/synthetic_demo.py: fixed invented 24-row/four-role example,
  public request/digest construction, existing pipeline and authoritative validator.
- tests/test_m4_synthetic_demo_cli.py: 18 final cases; no historical test edits.
- README.md: direct text/JSON usage and scope.
- Goal, agent/record/2026-10-01_04_m4-synthetic-demo-cli.md and this acceptance.

Command exposes only help and --json. Default text identifies invented input,
24 complete rows/96 observations, stages and digest, verbatim interpretation
boundary. JSON equals serialize_pipeline_result bytes, no custom schema.
All result construction/validation/serialization precedes output. Known
ValueError validation failures exit 1 with sanitized code and no stdout;
usage errors exit 2 before any computation; no abbreviated options.
No provider/file/database/environment/market/holdout inputs or access by module;
bootstrap disabled, empty robustness registry, absent registry metadata binding.
No duplicate statistical computation or imports from tests/private upstream APIs.

## Exact independent parent validation

PowerShell in D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest -q tests/test_m4_synthetic_demo_cli.py tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_project_entry.py
python -m pytest -q tests/test_m4_synthetic_demo_cli.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/synthetic_demo.py tests/test_m4_synthetic_demo_cli.py
python -m ashare_research.synthetic_demo
python -m ashare_research.synthetic_demo --json
git diff --check
git diff --cached --check
```

Initial focused regression: 67 passed in 72.40s, no skips.
After parent serialization/parser fixes: 18 final demo cases passed in 26.05s.
Original pipeline/entry sources unchanged; their prior 53 passing cases remain
valid. No unrelated repeat full local suite; hosted full suite mandatory.
Pinned Ruff: All checks passed, exit 0. Text/JSON CLI exit 0, stderr empty.
Unstaged whitespace passed; staged gate and complete scoped diff reviewed before
commit. JSON command was also captured by a parent subprocess (check=True) and
its metadata/hash inspected without retaining values.

Acceptance evidence:
- completed stages CONTRACT, PLAN, SYNTHETIC_INPUT, DATASET, MATRIX, EXECUTION;
- 24 complete rows and 96 role observations;
- execution_authorized=false, real_data_used=false, holdout_accessed=false;
- provenance_class=SYNTHETIC_TEST_ONLY, dataset_mode=SYNTHETIC;
- canonical bytes 43141, SHA256
  bfa3d6b22eeb0b97851f9ed34e2286a86c24bf25f032176f7c4393d9de03b9ff;
- pipeline digest
  269d823e6847542f5d60fdbd69a971fd2089b10a8cdca7b23d68ffee736d2f81.

Tests exercise genuine processes, another cwd, exact canonical envelope/digest,
authoritative revalidation, synthetic/holdout/bootstrap/registry boundaries,
AST public API/no IO surface, runtime blocked filesystem/env/network probes,
unsupported arguments/help/parser short circuit and sanitized pipeline plus
serialization failures. Standard pytest tmp_path, no permissions bypass.

## Independent review, deviations and protection

Parent inspected actual files, public API use, summary/serialization behavior,
new tests and narrow README. Serialized bytes are unchanged by final parent fix.
DSH exited 0 but violated parent-only tests instruction by manually running
embedded test scripts and simulating assertions despite not invoking pytest.
Parent records this deviation and independently runs actual pytest; worker's
claim is not acceptance. No fallback worker, custom temp-root, ACL workaround,
historic test weakening, external acquisition or database mutation occurred.

Actual primary exact status/binary diff/HEAD/stash snapshot unchanged:
HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
Protected research.duckdb SHA256:
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
SHA256 map of all tracked mechanism sources, M4 frozen docs/evidence/tests
unchanged. Git scoped diff additionally confirms no protected path edits.
Other user worktrees/local main 966206f06262e43f40c1c7aadbfb8596839eac91
preserved. No protected input/credential/database contents read; only DB hash.

Remaining limitations: demonstration fixed invented calendar/data, disabled
bootstrap, no research conclusion. Cross-process bytes validated locally;
cross-platform hosted regressions required before acceptance of delivery.
Historical Brent PIT/license gaps and independent K2 gates remain unresolved.

## Delivery gate

Parent may push only this scoped branch and open PR. Before merge independently
verify 42 successful required checks, expected head/base, clean mergeability,
actual diff/protection/Goal compliance. Standing scoped merge authorization
applies after PASS; no direct-main push, force push or next research stage.
Final handoff includes head/merge and local/origin/remote synchronization evidence.
