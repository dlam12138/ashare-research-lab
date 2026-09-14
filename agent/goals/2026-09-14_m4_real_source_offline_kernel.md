# Goal: M4 real-source offline verification kernel, phase K1

Date: 2026-09-14. Executor: DSH (`dsh --profile headless`) for bounded implementation and tests. Independent reviewer, acceptance and Git operator: Codex. This is a new implementation task authorized by the user's subsequent “继续推进”; it does not inherit the previous design-only Goal's file scope.

## Objective and verified baseline

Implement a pure, offline, fail-closed **source-proof kernel** for proposed M4 real daily inputs. It checks externally locked contract identity, registered raw bytes, deterministic normalization, observation timestamps and exact coverage arithmetic using invented fixtures. It emits only an audit proof or structured rejection and cannot build a matrix or authorize research. This is phase K1, not the complete `M4_REAL_SOURCE_BUNDLE_V1` adapter or a real provider integration.

- New clean worktree `D:/量化分析-m4-real-source-kernel`, branch `codex/m4-real-source-kernel`, base `e4fbde5da61875f4ce410f28192a42f8b9d8507b` (accepted design delivery), based on design-gate `7888553674d4480f0da59ada67c83be04134f1ad` and `main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`.
- Local `main`, `origin/main` and live remote main match `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`. PR #20 is OPEN at `d593f40ee6cc17147164c67d31f84ce34da6785a` with 42/42 successful checks; not merged. This task branch is not based on PR #20.
- Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`; 16 pre-existing status lines; stash SHA `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`; North-Star v2 SHA256 `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`.
- Governing design: [source contract](../../docs/m4_real_daily_source_contract_design_v1.md), [design cases](../../docs/m4_real_daily_source_acceptance_cases_v1.md), [prior acceptance](../../acceptance/2026-09-14_m4_real_daily_source_contract_design.md). Existing synthetic V1 public API, compiler, matrix, executor and pipeline are frozen.

## Allowed and forbidden scope

Only these paths may change:

1. this Goal (Codex owned);
2. `agent/record/2026-09-14_02_m4-real-source-offline-kernel.md` (Codex initial, DSH may append actual actions);
3. `src/ashare_research/mechanism/datasets/real_daily_kernel.py` (DSH implementation);
4. `tests/test_m4_real_daily_kernel.py` (DSH focused tests);
5. `acceptance/2026-09-14_m4_real_source_offline_kernel.md` (Codex independent acceptance).

DSH may read tracked files and write only paths 2–4. No recursive delegation, temp directories, provider/network requests, real data, filesystem discovery, database access, outcome research, statistics, holdout unsealing, synthetic V1 edits, `__init__.py` export changes, dependencies, CI, README, existing test changes, commit, push or PR. Codex may correct only the five allowed paths. Preserve unrelated worktrees, stash and ignored artifacts. No direct main push, force push, PR merge or automatic next stage.

## Required behavior and acceptance

- Public phase-K1 API must be explicitly named/versioned as an **offline proof kernel**, not the full `prepare_real_daily_dataset` promised by the design. Inputs must be immutable/typed or strictly shape-checked. It takes an independently supplied frozen lock, a bound contract/domain, declared source artifacts/observations, and a caller-injected mapping or reader of raw bytes. No direct provider, filesystem or database reads. Every relative locator must be safe and registered; no absolute or parent-traversal path, no unregistered bytes.
- Verify lock/contract/role/window/gate/code/source-version identity **before** examining target source bytes. The lock must not be trusted merely because the bundle self-reports its digest. A missing/mismatched lock or holdout date fails closed. Do not touch the injected reader on these early failures; test this order.
- Verify all registered raw byte lengths and SHA256 values, including calendar/membership artifacts if K1 accepts them; reparse a single narrowly specified canonical JSON fixture format deterministically with duplicate-key, float/NaN, duplicate-record and undeclared-field rejection. Compare normalized rows to declared rows so an honest raw hash cannot mask forged observations. The format is an internal test format only, not a claimed real provider parser. Reject missing bytes/unsupported formats rather than trusting caller rows.
- Check event/published/available/ingested times with explicit timezone offsets and `SOURCE_PUBLICATION_VERIFIED` basis. Missing publication or availability and ingestion-as-PIT fail structurally; availability after cutoff is an audited `PIT_UNPROVEN` gap. Keep outcome byte examination audit honest. No implicit timezone, date inference from existing rows, fill-zero, row filtering or source substitution.
- Domain dates and roles must be independently bound to a declared calendar/contract (K1 may use caller-supplied frozen calendar dates only if it clearly labels them **unverified calendar evidence** and never calls the result real-source validated). Exact cell coverage is `present/(dates×roles)`, with integer cross multiplication and a separate `min_joint_dates`. Reject below-gate/too-few-joint-date results while retaining gap reasons, with `matrix=None`, `execution_authorized=false`, `statistics_computed=false`, `research_outcome_consumed=false`.
- Canonical input/proof digest and serialization must be deterministic across input order and host directory, but detect changed bytes, values, lock or policy. No current-time defaults or host absolute paths. A pure verifier may return an audit proof only; no matrix rows, research statistics or real-adapter readiness.
- Focused tests must use invented in-memory bytes and cover good path, lock/read order, raw hash/byte substitution, normalized-row forgery, unsafe locator, duplicate JSON key/row, missing source/observation, missing published/available, ingestion-as-PIT, late PIT gap, non-trading/holdout date, exact 5/6 and 4/6 boundaries plus joint dates, digest tampering, reorder/cross-directory invariance and synthetic-entry isolation where callable. Tests should be meaningful behavioral checks, not implementation mirrors.
- If any required K1 behavior cannot be implemented without real-source choices or frozen V1 changes, stop and report the precise blocker. Do not weaken the Goal to manufacture a PASS.

## Exact validation commands

From this worktree with shared interpreter:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_real_daily_kernel.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4_synthetic_pipeline_orchestrator.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD main origin/main refs/stash
git worktree list --porcelain
git stash list
git ls-remote origin refs/heads/main refs/heads/codex/m4-multi-hypothesis-acceptance
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
Get-FileHash -Algorithm SHA256 'D:/量化分析/A股个股研究与市场机制验证平台-项目北极星-v2.md'
git -C 'D:/量化分析' rev-parse HEAD
```

Codex independently reviews actual staged code/test diff, error ordering, trust boundaries, serializations, numeric arithmetic, all changed/untracked files, protected hashes, PR #20 and local/remote synchronization. Strict UTF-8/LF/link audit applies to new Markdown. DSH test claims are not sufficient without Codex rerun.

## Stop, commit and final verdict

Accept only a bounded, honest K1 kernel with focused tests and existing regression passing, exactly whitelisted files, clean local delivery commit and independent acceptance evidence. Verdict exactly `PASS`, `CHANGES_REQUIRED` or `BLOCKED`. Stop for main/PR/protected drift, needed out-of-scope V1 edit, real outcome/data access or unresolved source choice. Commit locally after review; do not push, open PR, merge PR #20 or start K2 automatically. K2 provider-specific normalization and verified calendar/membership evidence require another Goal and explicit authorization.
