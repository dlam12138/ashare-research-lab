# Goal: M4-B hypothesis registry minimum implementation

Date: 2026-09-12. Executor: DeepSeek Harness (`deepseek-flash`). Reviewer: Codex.

## Objective and verified baseline

Implement the frozen, in-memory, metadata-only M4-B Theory / Hypothesis Registry described by
`docs/m4b_hypothesis_registry_design_v1.md`, and prove it against every frozen acceptance family in
`docs/m4b_hypothesis_registry_acceptance_cases_v1.md`. The implementation is synthetic/schema-only:
it must not create a real registry dataset, acquire literature, execute a hypothesis, read market
data, access holdout, or make a research claim.

- Worktree: `D:/量化分析-m4b-registry-implementation`.
- Branch: `codex/m4b-hypothesis-registry-implementation`.
- Base: live `origin/main` at `7fec2c137123150ded1fc2c1144116e19982444c`, the verified merge
  commit for PR #14. The worktree was created directly from that ref.
- PR #14 is merged and its 42 GitHub checks passed. The frozen design and acceptance cases are on
  main; no M4-B source implementation exists at the baseline.
- Normative design blob: `6d9c292001c09a4b1a8e895e54619dc1e8826f3d`; normative acceptance
  cases blob: `4a9b227204fc1c0eabc28e1e8b3d60a53c46f0b2`; protected Stage4P contract
  blob: `dfd41eaafc099e7748499f72de7ddd800bf97f69`.
- Protected original M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

## Allowed scope

Only these paths may be added or changed:

1. `agent/goals/2026-09-12_m4b_hypothesis_registry_implementation.md` (this contract;
   Codex-owned and committed before Harness execution)
2. `src/ashare_research/mechanism/registry/__init__.py`
3. `src/ashare_research/mechanism/registry/records.py`
4. `src/ashare_research/mechanism/registry/states.py`
5. `src/ashare_research/mechanism/registry/snapshot.py`
6. `tests/test_m4b_hypothesis_registry.py`
7. `README.md`, only to expose the implemented metadata-only API and accurately preserve all
   real-data, real-candidate, literature, holdout and execution prohibitions
8. `tests/test_project_entry.py`, only for truthful README/status synchronization without weakening
   any protective assertion
9. `tests/test_m4_stage4p_governance.py`, only for truthful README/status synchronization without
   changing protected aggregate, north-star, preflight or production-surface gates
10. `agent/record/2026-09-12_01_m4b-hypothesis-registry-implementation.md`
11. `acceptance/2026-09-12_m4b_hypothesis_registry_implementation.md`

## Forbidden scope

Do not modify the normative design or acceptance-case documents, `reports/**`, `config/**`,
`data/**`, `events/**`, dependencies, workflows, fixtures, existing M4 implementation modules,
top-level `src/ashare_research/mechanism/*.py`, or tests outside the three listed test files. Do not
create `src/ashare_research/m4`, `knowledge/`, a database schema, persistence layer, CLI, provider,
network or filesystem integration. Do not collect a real candidate, download literature, scan
anomalies, rank or sort by returns, select or auto-promote candidates, run a backtest, compute
statistics, read real market data, access holdout, or represent metadata as evidence. Do not weaken,
delete or skip tests. Preserve other worktrees, the stash, the protected database and ignored
runtime data. Do not delegate. Do not push, open a PR, merge, or begin a later stage.

## Required behavior

1. Implement exactly the four-module subpackage and the 13 public functions frozen in design
   sections 11.1-11.2. Export the frozen public dataclasses/enums/constants/errors needed to use
   those functions, with an explicit `__all__`; do not expose operational verbs or private helpers.
2. Implement the exact 26-key immutable record, nested transition/request structures, closed enums,
   strict V1-V12 validation order, stable error codes and no-coercion behavior. All record/history
   containers are immutable tuples; canonical-dict views are independent pure-JSON copies.
3. Reuse only `ashare_research.mechanism.model_digest.canonical_digest` for the two record digests
   and registry digest. Implement exact UTF-8/LF canonical serialization and fail-closed parsing,
   including non-canonical byte rejection and key/CWD/process stability.
4. Implement all 12 frozen states and 20 legal edges, their exact reason compatibility and
   prerequisites, optimistic `from_state` matching, immutable transitions, terminal-state behavior,
   `DEFERRED` recovery, authorization-reference gates and the complete `ESTABLISHED` evidence gate.
5. Implement immutable snapshots, deterministic identity-key ordering, duplicate versus provenance-
   rewrite distinction, `MAX_REAL_DEMO_CANDIDATES=3`, `MAX_RECORDS_PER_SNAPSHOT=3`, and no partial
   snapshot on failure.
6. Mechanically reject forbidden source identities, outcome/statistical keys, environment/selection
   keys, absolute paths, credential-like values and unsupported public operations as frozen by the
   design. Registry code must remain IO-free and import only the section 11.3 whitelist.
7. Translate AC-01 through AC-22 into focused executable tests, including subprocess/CWD byte
   reproducibility, nested mutation resistance, exact first-error precedence, idempotence, import
   boundary/static public-surface checks and explicit proof that no real candidate or execution path
   was introduced.
8. Update README only after implementation passes, stating that the minimum registry API is
   implemented for synthetic/schema validation while real registry data, literature acquisition,
   real hypothesis execution, real data and holdout remain not authorized.

## Required tests and exact validation commands

Run from this worktree and record every command and exit code independently. Use the shared verified
interpreter, set `PYTHONPATH` to this worktree's `src`, and disable pytest cache creation.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4b_hypothesis_registry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/mechanism/registry tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py
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
git diff --name-only origin/main...HEAD
git diff --name-only origin/main -- reports config data events docs
git hash-object docs/m4b_hypothesis_registry_design_v1.md docs/m4b_hypothesis_registry_acceptance_cases_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
Test-Path src/ashare_research/m4
Test-Path knowledge
```

Also verify changed Markdown as UTF-8 with a final newline, no trailing whitespace or conflict
markers, and resolve every repository-relative Markdown link. Host Codex must rerun tests because
DSH's sandbox is known to deny some pytest temporary-directory fixtures; any such Harness error is
recorded verbatim and is not called a pass.

## Acceptance criteria

- Changed paths are exactly within the whitelist. Frozen design, acceptance cases, Stage4P report,
  existing M4 modules and protected artifacts remain byte-identical.
- The implementation conforms to every normative constant, type, field, transition, validation
  stage, error, serialization/digest and import/public-surface rule; no implementation-critical
  design choice is silently changed.
- AC-01 through AC-22 have executable coverage. New tests, project/governance tests, bounded
  execution and the upstream M4 regression group pass; ruff and diff hygiene pass.
- No real candidate, real registry dataset, literature content, provider/database access, market
  input, holdout access, statistical outcome, research conclusion or generalized executor exists.
- Worktrees, stash, database hash, original M2 HEAD and remote main are unchanged; branch commits
  contain only the Goal and a scoped implementation delivery.
- Codex independently inspects branch/HEAD, commits/diff, changed/untracked files, test evidence,
  protected baselines, remote synchronization and Goal compliance. Verdict is exactly `PASS`,
  `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop and report if any normative document or allowed path changes concurrently; conformity would
require changing a frozen report/design, an existing implementation module, dependency, workflow,
fixture or protected artifact; an acceptance case cannot be implemented without a design decision;
any real candidate/data/literature/provider/holdout/statistical execution is required; a protective
assertion would need weakening; or a non-whitelisted diff appears. Do not widen scope to continue.

## Commit and push requirements

Codex commits this Goal before Harness execution. Harness may create one scoped local implementation
delivery commit containing only paths 2-11 after validation; if its sandbox cannot update the shared
Git metadata, it must leave the reviewed changes uncommitted and record that limitation for Codex.
Do not push, open a PR, merge, or start a later stage. After local delivery, wait for Codex's
independent verdict.
