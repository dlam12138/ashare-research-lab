# M4 real daily source contract design record

Date: 2026-09-14. [Goal](../goals/2026-09-14_m4_real_daily_source_contract_design.md). Executor: DSH for design documents; independent reviewer: Codex.

## Starting evidence

New worktree `D:/量化分析-m4-real-daily-adapter-design` on `codex/m4-real-daily-adapter-design@7888553674d4480f0da59ada67c83be04134f1ad`. This is the design-gate commit on top of `main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`. PR #20 remains open at `d593f40ee6cc17147164c67d31f84ce34da6785a`, 42 successful checks, not merged. Protected M2 HEAD, stash and database hash are recorded in the Goal and were checked before work.

## Work boundary

DSH is to draft only the versioned real source design and acceptance cases, then update this record with its actual read-only source checks and document actions. It must not run tests, fetch data, modify code, commit, push or merge. Codex will independently inspect actual files and run the regression; this initial record contains no future test or acceptance result.
