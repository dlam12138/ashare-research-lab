# Goal: M4 real daily source contract and adapter design

Date: 2026-09-14. Executor: DSH (`dsh --profile headless`) for bounded document design. Independent reviewer and Git operator: Codex.

## Objective and verified baseline

Freeze an implementable, **design-only** contract for validating real daily source evidence before any research execution. Specify a distinct versioned input/preparation envelope and fail-closed validation, without interpreting synthetic V1 evidence as real provenance. Produce a numeric/date example and acceptance cases that a future implementation can test. This stage does not authorize acquiring data, implementing the adapter, reading outcomes or running a hypothesis.

- Worktree `D:/量化分析-m4-real-daily-adapter-design`, branch `codex/m4-real-daily-adapter-design`, clean base `7888553674d4480f0da59ada67c83be04134f1ad` (the approved design-gate commit), itself based on `main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`.
- `main`, `origin/main` and live remote main matched at `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`. PR #20 is OPEN at `d593f40ee6cc17147164c67d31f84ce34da6785a`, with 42 successful checks, and is not merged. Its synthetic acceptance is external evidence; this branch is not based on its head.
- Protected M2 worktree HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`; North-Star v2 SHA256 `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- Inputs: [design-gate decision](../../docs/m4_real_daily_adapter_design_gate_v1.md), North-Star M4 §§17–18, Stage4P contracts, M3 source/timing/membership/PIT contracts, current typed config/compiler, synthetic adapter, matrix/executor/pipeline public APIs and tests.

## Allowed and forbidden scope

Only these five Markdown paths may be added or changed:

1. this Codex-owned Goal;
2. `agent/record/2026-09-14_01_m4-real-daily-source-contract-design.md` (Codex initial record, DSH may update evidence);
3. `docs/m4_real_daily_source_contract_design_v1.md` (DSH design);
4. `docs/m4_real_daily_source_acceptance_cases_v1.md` (DSH cases);
5. `acceptance/2026-09-14_m4_real_daily_source_contract_design.md` (Codex independent acceptance).

DSH may read tracked sources and write only paths 2–4. It must not delegate recursively, create temp directories, run pytest, commit, push or open a PR. Codex may correct only these five files after review. No source/test/CI/README/dependency/frozen-contract changes; no provider requests, database connection, real raw data, literature, outcome read, candidate selection, holdout, statistical execution, other-worktree edits, stash change, ignored-artifact cleanup, push, PR or merge.

## Required design behavior

- Decide and label a **proposed API** for an independent, versioned real source contract, input bundle, preparation and validator. Existing V1 `HypothesisConfig`, `BoundDatasetInputsV1`, `DatasetPreparationV1`, `run_synthetic_pipeline` and synthetic executor stay untouched and synthetic-only. A new real preparation must have `execution_authorized=false`, no accepted matrix/statistic and no capability to reach the synthetic pipeline. State what a later study-contract revision or bridge would require, without implementing it or silently extending closed enums.
- Specify required fields/types and validation order for provider/endpoint/version/vintage/raw SHA, calendar/exchange/timezone/session, security-level identity and t−1 membership, observation/published/available/ingested timestamps, units/adjustments/returns, roles, expected-date denominator, missingness/coverage and immutable source/code identities. Distinguish event time, publication time, first availability and ingestion; ingestion alone is not PIT proof. Separate raw artifact identity from semantic identity and define canonical serialization/digests without host paths or current-time defaults.
- Define first-failure and aggregate-quality behavior. Structural/identity/PIT failures must fail closed; no source replacement, row filtering, fill-zero, backfilled current membership, implicit calendar, post-outcome contract mutation or holdout access. A rejected preparation cannot expose a partial execution-ready matrix. List M3 semantics that can be reused and case-specific constants/data that cannot.
- Give a tiny manually recomputable date/return example, including an unavailable observation and the resulting exact coverage numerator/denominator. Cases must include normal input plus missing published/available timestamp, revision substitution, non-trading date, suspension/identity ambiguity, company-vs-security ID, t−1 membership drift, adjustment mix, missing role, duplicate row, below-gate coverage, forged digest, input reorder invariance, cross-directory identity, post-outcome mutation and holdout injection. Each case needs input delta, expected output/error and validation entry.
- Explicitly mark unresolved decisions if the current frozen interfaces cannot support them. Do not call this real research readiness, implementation readiness, or execution authorization.

## Required tests and exact validation commands

Codex runs the existing offline regression from this worktree with the shared interpreter, after DSH delivery:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4_synthetic_pipeline_orchestrator.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD main origin/main refs/stash
git worktree list --porcelain
git stash list
git ls-remote origin refs/heads/main refs/heads/codex/m4-multi-hypothesis-acceptance
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
```

Independently check all new Markdown for strict UTF-8, LF final newline, trailing whitespace, conflict markers, valid relative links, numeric example arithmetic and case-to-error consistency. Refresh PR #20 head/checks via GitHub. Do not invent real-adapter tests or claim DSH ran pytest.

## Acceptance, stop and delivery

Codex accepts only a complete, internally consistent design and cases with no critical API/failure ambiguities, exactly five whitelisted Markdown files, passing regression/hygiene, protected baselines unchanged and a clean local delivery commit. Final verdict exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

Stop and report if main/PR/protected identities drift, any necessary design decision requires real outcome/data access, frozen V1 mutation, out-of-scope code or test changes, or DSH cannot deliver reviewable docs. Codex commits locally after independent review. Do not push, open PR, merge PR #20 or start implementation. A future implementation requires separate user authorization and Goal.
