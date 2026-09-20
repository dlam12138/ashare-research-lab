# M4 real-source offline kernel K1 — independent acceptance

Date: 2026-09-14. Verdict: **PASS** for the bounded K1 Goal only. [Goal](../agent/goals/2026-09-14_m4_real_source_offline_kernel.md), [record](../agent/record/2026-09-14_02_m4-real-source-offline-kernel.md), [kernel](../src/ashare_research/mechanism/datasets/real_daily_kernel.py), [tests](../tests/test_m4_real_daily_kernel.py).

## Reviewed behavior and scope

- The entry is `verify_real_daily_source_proof_k1`, with `M4_REAL_SOURCE_OFFLINE_BUNDLE_K1` and offline proof/rejection schemas. It is not the proposed full real daily adapter, creates no matrix/statistics and never authorizes execution. Its proof always declares `calendar_evidence_verified=false` and `real_source_validated=false`.
- An independently supplied trusted lock digest binds the contract, frozen date domain, code identity and source provider/endpoint/revision/vintage/raw SHA/normalization rule before the injected byte mapping is touched. A reader-callback mutation test confirms validation uses an input snapshot. Unsafe locators, missing roles, changed source version or holdout rows fail closed before raw access.
- K1 accepts only invented, canonical in-memory JSON fixture bytes. It verifies byte length and SHA, rejects duplicate JSON keys/records and forged normalized observations, then checks explicit time offsets, publication/availability/ingestion order and `SOURCE_PUBLICATION_VERIFIED` basis. A late observation becomes a `PIT_UNPROVEN` gap; missing PIT fields fail structurally.
- Exact coverage uses frozen role×date denominator, integer cross multiplication and a separate complete-date minimum. Quality rejection retains gap reasons and has `matrix=None`, empty accepted roles and false execution/statistical flags. Source-bound proof validation and the frozen synthetic serializer/pipeline reject forged or incompatible proof objects.
- No existing source/test/CI/README file changed. K1 has no provider, filesystem, database, network or execution imports. Calendar and membership provenance remains unverified, so this PASS is not a real-source validation or research-readiness decision.

## Actual execution and validation

DSH was invoked twice but produced analysis only; Codex stopped it and authored the implementation/tests. DSH did not run tests or commit. The first existing regression run failed one AC-21 directory-stability assertion because Codex concurrently started Ruff and Ruff created `.ruff_cache`. There was no K1 assertion failure; 293 other tests passed. The ignored cache was preserved. Non-concurrent repeats passed **294/294 in 222.74s** and **294/294 in 177.48s**; after the final input-snapshot change, the exact regression passed **294/294 in 256.64s**. Focused K1 tests passed **15/15 in 0.13s**; `ruff format` and `ruff check` on both new Python paths passed.

Exact commands from `D:/量化分析-m4-real-source-kernel`:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_real_daily_kernel.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4_synthetic_pipeline_orchestrator.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/mechanism/datasets/real_daily_kernel.py tests/test_m4_real_daily_kernel.py
git diff --check
git diff --cached --check
```

The final-code regression includes the defensive input snapshot. The five changed paths are exactly those whitelisted in the Goal. A final strict Markdown audit, commit diff/status and protected-state review follow before delivery.

## Baselines and next gate

Task base `e4fbde5da61875f4ce410f28192a42f8b9d8507b`; local `main`, `origin/main` and remote main matched `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`. PR #20 remained OPEN at `d593f40ee6cc17147164c67d31f84ce34da6785a` with 42/42 successful checks. Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`, 16 pre-existing status lines, stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, default DB SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`, North-Star v2 SHA256 `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307` were unchanged at review.

K2 requires a separate Goal and explicit authorization to select and verify real calendar/member sources, provider formats, timing evidence, licenses and a versioned real study bridge. This acceptance does not start K2, fetch real data, push, open a PR or merge PR #20.
