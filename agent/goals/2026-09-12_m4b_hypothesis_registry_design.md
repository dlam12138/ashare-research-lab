# Goal: M4-B hypothesis registry design

Date: 2026-09-12. Executor: DeepSeek Harness (`deepseek-flash`). Reviewer: Codex.

## Objective and verified baseline

Freeze an implementable design and acceptance cases for the minimum M4-B Theory / Hypothesis
Registry slice: provenance-aware candidate metadata, canonical identity, strict validation, and a
fail-closed state machine. This is design and documentation only. It does not implement a registry,
create a real candidate dataset, acquire literature, or authorize real hypothesis execution.

- Worktree: `D:/量化分析-m4b-registry-design`.
- Branch: `codex/m4b-hypothesis-registry-design`.
- Base: live `origin/main` at `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd`, the verified
  merge commit for PR #13. The worktree was created directly from that ref.
- PR #13 is merged. Its 40 GitHub checks passed, and the synthetic-only bounded execution is on
  main. M4-B remains `NOT_STARTED`; real-data execution and real hypothesis execution remain
  unauthorized.
- The frozen Stage4P M4-B preflight contract is
  `reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json`, with
  `status=FROZEN_PREFLIGHT_ONLY`, `implementation_status=NOT_STARTED`,
  `real_registry_dataset_authorized=false`, and `not_implementation=true`.
- Protected original M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`;
  stash: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

## Allowed scope

Only these paths may be added or changed:

1. `agent/goals/2026-09-12_m4b_hypothesis_registry_design.md` (this contract;
   Codex-owned and committed before Harness execution)
2. `docs/m4b_hypothesis_registry_design_v1.md`
3. `docs/m4b_hypothesis_registry_acceptance_cases_v1.md`
4. `agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md`
5. `acceptance/2026-09-12_m4b_hypothesis_registry_design.md`
6. `README.md`, limited to current-capability and roadmap statements made stale by this design
   freeze while preserving the semantics `M4-B NOT STARTED` and
   `real hypothesis execution NOT AUTHORIZED`
7. `tests/test_project_entry.py`, only if required to synchronize hard-coded README status text,
   without weakening any protective assertion
8. `tests/test_m4_stage4p_governance.py`, only if required to synchronize canonical README status;
   do not alter protected aggregate, north-star, preflight, or production-surface gates

The design and acceptance-cases documents are normative. Every interface is proposed and must not
be described as implemented.

## Forbidden scope

Do not modify `src/**`, `reports/**`, `config/**`, `data/**`, `events/**`, dependencies, workflows,
north-star documents, existing M4 design/acceptance documents, fixtures, or any test outside the
two conditional status-sync files above. Do not add `knowledge/` or `src/ashare_research/m4`, and do
not add a top-level `src/ashare_research/mechanism/*.py` file. Do not implement M4-B, collect a real
candidate, download paper or textbook content, build a real registry dataset, scan anomalies, rank
backtests, auto-promote candidates, call providers, read database contents or real market data,
access holdout, or run statistical execution. Do not weaken or delete tests. Preserve other
worktrees, stash entries, ignored runtime data, and protected artifacts. Do not delegate. Do not
push, open a PR, merge, or start implementation.

## Required design behavior

The design must freeze, without leaving implementation-critical choices open:

1. The record schema: types, required/optional status, nullability and enums for every frozen
   minimum field; record schema version; identity-bearing versus mutable fields; unknown-key policy.
2. Canonical serialization and digest identity: UTF-8 without BOM, LF, deterministic key ordering,
   exact numeric representation, digest algorithm and binding scope, and exclusion of hostname,
   absolute path, wall-clock time, database contents, or other environment-specific inputs.
3. Provenance rules for all six frozen source types, citation/source identity, version and notes;
   literature is a hypothesis source and never local A-share evidence. Forbidden canonical sources
   must be mechanically rejected with stable error codes.
4. The twelve frozen states and an explicit legal-transition matrix, transition prerequisites,
   non-skippable boundaries, no unsupported regression or promotion, and the rule that
   `ESTABLISHED` is unreachable without applicable frozen development, registered robustness and
   independent OOS evidence.
5. Validation order and stable error codes; fail-closed and type-strict behavior; no coercion,
   partial writes or ambiguous duplicate IDs; idempotent re-validation.
6. Mechanical separation between registry metadata and research outcome artifacts. Coefficients,
   intervals, p-values, dispositions and other outcome/statistical fields must be forbidden.
7. Exact scale semantics for `MAX_REAL_DEMO_CANDIDATES=3`, plus enforced prohibitions on automated
   anomaly scanning, backtest ranking, return-based sorting, and candidate auto-promotion.
8. A proposed implementation placement in `src/ashare_research/mechanism/registry/`, matching the
   existing subpackage pattern and preserving the frozen top-level `mechanism/*` aggregate and the
   absence of `src/ashare_research/m4` and `knowledge/`. Freeze proposed module layout, public
   signatures and import boundary without writing code.
9. Synthetic/schematic examples only. No real candidate, downloaded full text, real citation
   acquisition, real A-share outcome, provider or registry dataset may be introduced.
10. Traceability and authorization semantics: source/version/theory remain traceable; a record may
    remain `NOT_TESTED` indefinitely; design completion is not implementation, execution, evidence,
    real-data, holdout, push, PR or merge authorization.

The acceptance cases must specify the input change, expected output or stable error code,
validation stage and authorization interpretation for at least: valid synthetic record; unknown
source type; missing provenance; forbidden citation source; unknown/extra key; strict bool/int and
numeric handling; illegal transition; `ESTABLISHED` without complete evidence; outcome/statistic
key rejection; scale violation; duplicate hypothesis ID; canonical serialization and digest
stability under key order and CWD changes; byte reproducibility; nested mutation; registry/outcome
separation; and fail-closed read paths.

## Required tests and exact validation commands

Run from this worktree and record each command and exit code independently. Use the shared verified
interpreter and disable pytest cache creation.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'
gh pr list --state open --json number,title,headRefOid,baseRefName,url
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
git diff --name-only HEAD -- src reports config data events
Test-Path src/ashare_research/m4
Test-Path knowledge
```

Also verify all changed Markdown as UTF-8 with a final newline, no trailing whitespace or conflict
markers, and resolve every repository-relative Markdown link. Review the actual current interfaces
and frozen contracts directly; do not infer them from earlier summaries.

## Acceptance criteria

- Changed paths are exactly within the whitelist. `src/**`, frozen reports and all protected
  artifacts have no diff; the Stage4P M4-B preflight report remains byte-identical.
- All ten required behavior areas are frozen without an implementation-critical ambiguity; every
  acceptance case includes input, expected result/error, validation stage and authorization meaning.
- The design explains why direct implementation is not yet permitted and marks all proposed APIs as
  proposed. `M4-B NOT STARTED` and real-execution-not-authorized semantics remain explicit.
- Existing project-entry, governance, bounded-execution and upstream M4 regression suites plus ruff
  pass. Any genuine environmental failure is recorded verbatim and independently attributed; it is
  never hidden or worked around by weakening a test.
- Worktrees, stash, database hash, north-star and frozen M1-M3 evidence remain unchanged; live
  `origin/main` is independently verified.
- Codex independently reviews branch/HEAD, commits and diff, changed/untracked files, test evidence,
  worktrees/stash, protected baselines, remote state and Goal compliance. Final verdict is exactly
  `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop and report if the baseline or an allowed path changes concurrently; the design requires a
source implementation, frozen report, dependency, workflow or protected-artifact change; a real
candidate, literature acquisition, provider, database content, real market input, holdout or
statistical outcome is required; a protective assertion would need weakening; a frozen-contract
conflict cannot be resolved in the new design; or any `src/**` diff appears. Do not widen scope or
weaken a gate to continue.

## Commit and push requirements

Codex commits this Goal contract before Harness execution. DeepSeek Harness creates one scoped local
design-delivery commit containing only paths 2-8 after validation. Do not push, open a PR, merge, or
start implementation. After delivery, wait for Codex's independent verdict.
