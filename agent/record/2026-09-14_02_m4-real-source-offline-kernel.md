# M4 real-source offline kernel K1 record

Date: 2026-09-14. [Goal](../goals/2026-09-14_m4_real_source_offline_kernel.md). Executor: DSH for bounded code/tests. Independent reviewer and Git operator: Codex.

Starting worktree `D:/量化分析-m4-real-source-kernel` on `codex/m4-real-source-kernel@e4fbde5da61875f4ce410f28192a42f8b9d8507b`, clean, based on the accepted design. Main/PR/M2/stash/database/North-Star identities and status were verified before implementation and are recorded in the Goal. No implementation, test or acceptance result is claimed yet.

## Execution record

Two `dsh --profile headless` invocations inspected the Goal, accepted design, cases and synthetic code but remained in analysis without writing a file. Codex interrupted both runs and independently wrote `src/ashare_research/mechanism/datasets/real_daily_kernel.py` and `tests/test_m4_real_daily_kernel.py`. DSH did not implement, test, commit or push. This record does not attribute Codex code to DSH.

The kernel uses only invented canonical JSON bytes supplied through an injected mapping. It checks the external trusted lock digest before any raw access, binds contract/domain/code/provider/endpoint/revision/vintage/raw hash/normalization rule, validates safe relative locators and actual byte hashes, reparses rows and compares claimed observations, checks explicit timestamps and exact coverage plus joint-date gates. A passing K1 proof explicitly says `calendar_evidence_verified=false` and `real_source_validated=false`; no provider parser, verified real calendar/member source, matrix or execution path exists.

Focused validation: `PYTHONPATH=src` with the shared interpreter, `pytest -q -p no:cacheprovider tests/test_m4_real_daily_kernel.py` → **14 passed in 0.11s** (latest run). `ruff format` and `ruff check` on the two new Python files → **all checks passed**.

The first existing six-file M4 regression ran while Codex concurrently started Ruff. Ruff created the ignored `.ruff_cache` directory during the AC-21 ambient-directory snapshot, so that regression reported **293 passed, 1 failed**; the failure was a directory-name change, not an assertion about K1 logic. The full existing regression was then rerun with no concurrent repository writes and reported **294 passed in 222.74s**. The ignored cache was preserved. A final validation after review is still required before acceptance and commit.

Final-code validation: after adding defensive input snapshotting and its behavior test, focused K1 pytest reported **15 passed in 0.13s**, Ruff check passed, and the exact six-file M4 regression ran without concurrent writes and reported **294 passed in 256.64s**. No source/test changes followed this run.
