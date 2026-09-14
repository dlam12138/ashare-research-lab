# M4 real daily source contract design — independent acceptance

Date: 2026-09-14. Verdict: **PASS** for the bounded design-only Goal; no real adapter, real data acquisition, outcome study, execution, PR or merge is authorized. [Goal](../agent/goals/2026-09-14_m4_real_daily_source_contract_design.md), [record](../agent/record/2026-09-14_01_m4-real-daily-source-contract-design.md), [design](../docs/m4_real_daily_source_contract_design_v1.md), [cases](../docs/m4_real_daily_source_acceptance_cases_v1.md).

## Independently reviewed delivery

- DSH produced the two design documents and updated the record. Its first invocation did not write files; its second did. Codex independently reviewed and corrected API and validation ambiguities in the allowed documents. DSH did not run pytest or commit.
- The design proposes separate `M4_REAL_SOURCE_BUNDLE_V1`, `M4_REAL_DATASET_PREPARATION_V1` and rejection schemas, independent real contract/plan and an external frozen lock. The proposed validator requires actual offline raw bytes and deterministic normalization before trusting SHA or normalized observations. It separates raw acquisition identity, semantic dataset identity and complete preparation identity.
- Source/contract/holdout checks precede target-byte examination; missing PIT evidence fails closed, while late availability enters the predeclared coverage gate as `PIT_UNPROVEN`. The validator records whether target bytes were examined and never grants execution or exposes a matrix/statistic. Existing synthetic V1 interfaces stay untouched.
- Cases RDC-N01–N04 and RDC-E01–E28, with RDC-E17B and RDC-E21B, map input deltas to proposed validation stages and failure outcomes. The distinct missing-source/missing-observation and coverage/joint-date cases now agree with the design. Synthetic-entry isolation asserts rejection by existing frozen behavior without inventing a new existing error code.
- Manual Decimal recomputation: `102/100-1=0.02`, `102/102-1=0`, `103.02/102-1=0.01`; expected cells `3 × 2=6`, PIT-qualified cells `5`, complete dates `2`; `5/6 < 1/1`, equality at `5/6`, and `4/6=2/3` with two complete dates at the boundary. Two missing factor dates leave one complete date and fail `min_joint_dates=2`.

## Validation and protected state

From `D:/量化分析-m4-real-daily-adapter-design`:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4_synthetic_pipeline_orchestrator.py
```

Result: **294 passed in 220.53s**. No new implementation or tests were written; these are existing offline regressions, not proof that a real adapter exists. `git diff --check` and `git diff --cached --check` passed. A strict UTF-8/LF/trailing-space/conflict-marker/relative-link audit passed for the Goal, record, design and cases; rerun including this acceptance file before final commit. Exact arithmetic was independently recomputed with `Decimal`.

At review, local `main`, `origin/main` and live remote main were `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`; this task's base was design-gate `7888553674d4480f0da59ada67c83be04134f1ad`. PR #20 remained OPEN at `d593f40ee6cc17147164c67d31f84ce34da6785a`, base main `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`, with 42/42 successful checks. Protected M2 HEAD remained `3679b1bac7a1634c6452784a4d8f6d139966f222`, stash SHA `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, default database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`, and North-Star v2 SHA256 `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`. The M2 worktree's pre-existing modified/untracked files were preserved. The full worktree list and stash were inspected; no other worktree was changed by this task.

## Limits and next gate

This is an implementable *proposed* validation design, not a provider-ready or research-ready adapter. Real calendar/member/revision/PIT evidence, source licenses, target horizon, transformation/adjustment choices, signal cutoff, coverage defaults and a real execution bridge remain unresolved. A subsequent implementation requires a separate Goal and explicit authorization under the design gate; this PASS does not start it. Local commit and post-commit Git evidence are recorded in the final delivery report.
