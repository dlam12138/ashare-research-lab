# M4 real daily source contract design record

Date: 2026-09-14. [Goal](../goals/2026-09-14_m4_real_daily_source_contract_design.md). Executor: DSH for design documents; independent reviewer: Codex.

## Starting evidence

New worktree `D:/量化分析-m4-real-daily-adapter-design` on `codex/m4-real-daily-adapter-design@7888553674d4480f0da59ada67c83be04134f1ad`. This is the design-gate commit on top of `main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`. PR #20 remains open at `d593f40ee6cc17147164c67d31f84ce34da6785a`, 42 successful checks, not merged. Protected M2 HEAD, stash and database hash are recorded in the Goal and were checked before work.

## Work boundary

DSH is to draft only the versioned real source design and acceptance cases, then update this record with its actual read-only source checks and document actions. It must not run tests, fetch data, modify code, commit, push or merge. Codex will independently inspect actual files and run the regression; this initial record contains no future test or acceptance result.

## DSH delivery (actual actions, 2026-09-14)

Files written by DSH (only these two):

- `docs/m4_real_daily_source_contract_design_v1.md` — 184 lines, 18265 bytes.
- `docs/m4_real_daily_source_acceptance_cases_v1.md` — 103 lines, 11137 bytes.

The first DSH invocation inspected the Goal, design gate, current contracts and implementation context, but wrote no deliverable. The second invocation read this Goal, the design gate, this record and `src/ashare_research/mechanism/datasets/synthetic.py` lines 184–303; it also ran read-only greps over `src/ashare_research/mechanism` for public type/version names and `_fail` error codes, and globs over `docs/`, `reports/` and `src/ashare_research/mechanism/` to confirm relative link targets. Only the listed design deliverables and this record were changed by DSH.

Design content delivered: proposed independent real contract (`M4_REAL_SOURCE_BUNDLE_V1` input, `M4_REAL_DATASET_PREPARATION_V1` output, `M4_REAL_SOURCE_REJECTION_V1` rejection, `M4_REAL_DAILY_ROLE_ADAPTER_V1`, `M4_CANONICAL_REAL_SOURCE_DIGEST_V1`), V1 isolation rules, per-field source/calendar/membership/security/timestamp/units/returns/coverage/lineage contract, ordered validation with first-failure and aggregate-quality semantics, a stable error-code list, canonical serialization/digest rules, a manually recomputable three-date example (returns 0.02/0.00/0.01; coverage 5/6 against gate 1/1, boundary check at 5/6), M3 reuse limits, and later bridge blockers. Cases file defines baseline `NORMAL-01` plus normal cases RDC-N01–N04 and negative cases RDC-E01–E28 with input delta, expected output/error code and validation entry for each.

Verification actually performed by DSH: one read-only PowerShell listing of the two files for existence, byte size and line count (`Get-ChildItem` + `Get-Content`). No pytest, no data fetch, no database or provider access, no temp directory, no delegation, no code/test/CI change, no commit, push or merge. `M4_REAL_*` names are proposed only; nothing was implemented or imported. Codex independently corrected design inconsistencies concerning raw-byte reader injection, proposed contract/plan types, source-bound revalidation, PIT evidence basis, quality gating, outcome-byte audit, digest ordering and numeric example; Codex owns the regression, hygiene checks and acceptance verdict.
