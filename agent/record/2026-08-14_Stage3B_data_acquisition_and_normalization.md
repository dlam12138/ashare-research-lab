# Work Record: M3 Stage 3B — Data Acquisition and Normalization

Status: CLOSED — fail-closed data-gap acceptance

## Basic information

- Date: 2026-08-14
- Agent: Codex
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting commit: `ae2225f45c984f90b00ca28b3c35b421fe030359`
- Source: user-authorized M3 Stage 3B execution instruction
- Module: mechanism validation / data foundation
- Goal contract: `agent/goals/2026-08-14_m3_stage3b_data_acquisition_and_normalization.md`

## Objective

Acquire and normalize Tier-1 development inputs, construct the PIT-safe
`SH_MARKET_EX_601857` primary proxy if strict inputs are available, and produce deterministic
offline acceptance without reading the sealed holdout or executing mechanism statistics.

## Scope

Stage 3B semantic addenda, source registry, capability-specific acquisition/normalization,
market-proxy construction, immutable external raw manifest, development coverage metadata,
focused tests, README status correction, acceptance evidence, commits, push, and CI closeout.

## Non-goals

Stage 3C; real mechanism inference; holdout access; regression/statistical results; Tier 2/3
acquisition; default DB writes; large raw-data commits; M1/M2 refactors; PR or merge.

## Starting state

- The user-facing workspace was actually on protected dirty M2 branch
  `feat/m2-value-assessment-mvp` at `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`.
- A separate worktree `D:\量化分析-m3-stage3b` was created for the existing M3 branch.
- M3 local and origin both resolve to Stage 3A final commit `ae2225f45...`; isolated worktree clean.
- One pre-existing stash is present and protected.
- The isolated worktree has no `data/research.duckdb`.
- Stage 3A three-contract SHA-256 values were recorded in the Goal contract.
- README has two stale statements saying M3 has not started.
- Existing `BaseProvider` covers stock basics, trade calendars, stock daily, and index daily;
  it does not provide historical PIT universe/share, oil, or industry capabilities.

## Files read before implementation

- `AGENTS.md`, `CLAUDE.md`, `agent/agent.md`, `agent/record/README.md`
- Three recent work records, including the Stage 3A record
- Both project North-Star documents
- Stage 3A acceptance and all three frozen core contracts
- Existing provider base interface and relevant README status lines

## Risks identified

- Strict historical Shanghai eligibility/share inputs may not be freely obtainable; the required
  response is fail-closed evidence, not a convenient substitute.
- The SSE Composite methodology changed on 2020-07-22; current rules cannot be backfilled.
- Overseas daily closes are not observable by the same A-share close and require explicit lagging.
- Editable-install path leakage previously affected full-suite tests; validation will bind
  `PYTHONPATH` to this isolated worktree.
- The current calendar date is inside the sealed holdout; all acquisition bounds require explicit
  validation before any network request.

## Implementation plan

1. Establish Goal contract and this work record.
2. Research official methodology regimes and freeze semantic/source contracts.
3. Implement scoped acquisition, validation, normalization, proxy, and manifest capabilities.
4. Acquire only warm-up/development inputs into external storage and run offline A/B normalization.
5. Add focused tests and acceptance evidence; update README factually.
6. Run all local gates, commit/push, wait for remote CI, and independently review final evidence.

## Decision log

- Use an isolated M3 worktree to preserve the original dirty M2 checkout exactly.
- Treat absence of strict historical PIT inputs as an allowed fail-closed Stage 3B outcome, never
  authorization to degrade the primary proxy.
- Treat data-quality/coverage metadata as permitted and all return relationship or conditional
  statistics as prohibited.

## Actual operations

1. Read the attached execution instruction.
2. Verified real branch, HEAD, remotes, stash, worktrees, and relevant files.
3. Verified M3 local/origin identity and created the isolated M3 worktree.
4. Read governance, recent records, North Stars, Stage 3A acceptance/contracts, provider interface,
   and README status drift.
5. Recorded frozen Stage 3A hashes and confirmed the default DB is absent in this worktree.
6. Created the Goal contract and this work record before implementation changes.
7. Reviewed official SSE methodology evidence. The applicable regimes are the pre-2020-07-22
   rule (new listings enter on the eleventh trading day; price times issued shares; divisor
   maintenance; risk-warning shares were not excluded) and the rule effective 2020-07-22
   (risk-warning exclusion, one-year/three-month new-listing delay, STAR/CDR eligibility).
8. Inspected installed Akshare 1.18.79 and Baostock 00.9.30 capabilities. Baostock exposes dated
   all-stock snapshots but no issued-share history. Akshare exposes CNINFO company share-change
   and Eastmoney share-structure histories; both require full coverage and share-class audits.
9. Reviewed official EIA/FRED Brent metadata and candidate Shenwan industry-index regimes.
10. Added the three Stage 3B semantic/source contracts and corrected only the stale README status.
11. Implemented capability-specific provider protocols plus contract, normalization, oil-alignment,
    primary-proxy, immutable-manifest, coverage, and canonical-digest primitives.
12. Added a one-shot acquisition/offline-audit tool with a hard 2022-12-31 upper bound, immutable
    raw paths, raw SHA verification, and refusal to rerun into an existing capsule.
13. Acquired the bounded external capsule once: calendar, target qfq/unadjusted, four dated universe
    snapshots, and three CNINFO share-history samples covering A, A/H, and B semantics.
14. Ran offline normalization A and B. The audit plus calendar and both target outputs are exact-byte
    identical between runs.
15. Applied the primary fail-closed gate. The acquired sources do not establish complete daily
    official eligibility, every eligible security's applicable issued shares, and full corporate-
    action/divisor continuity. No primary proxy was constructed.
16. Stopped the ordered network acquisition before oil and industry, recorded both as not acquired,
    and generated development manifest, coverage, and acceptance artifacts without research results.

## Data and methodology notes

One bounded network acquisition was performed into an external root. Requests ended no later than
2022-12-31. No holdout market outcome was acquired or read. No statistic or mechanism result was
computed.

The primary proxy contract explicitly retains the historical SSE methodology break. Oil is frozen
to EIA Europe Brent Spot Price FOB but fails closed unless historical release/vintage timing proves
the observation was visible before the A-share close. The industry control explicitly records the
SW 2014 `801016` to SW 2021 `801960` taxonomy transition instead of silently changing proxies.

## Validation

- Stage 3B JSON parse: PASS for all three semantic/source contracts.
- Frozen Stage 3A SHA-256 recheck: PASS, all three hashes unchanged.
- `git diff --check`: PASS after semantic-contract changes.
- Focused Stage 3B tests after implementation: 22 passed.
- Focused Ruff and compileall: PASS after correcting one UP038 lint finding and one line-length
  finding.
- External raw manifest verification: PASS for all 10 files.
- Offline A/B: audit, calendar, qfq target, and unadjusted target exact-byte identical.
- Stage 3B report JSON parse and restricted-output-key gate: PASS.
- The literal `python -m pytest -q tests/test_m3_stage3b_*.py` command did not expand its glob in
  PowerShell and exited 4 with no tests collected. The PowerShell-resolved file-list equivalent then
  passed all 22 focused tests.
- First full-suite run: 1963 passed, 3 skipped, 2 failed. Both failures were stale living-status
  assertions: README still expected preflight-only wording, and Stage 3A still required no mechanism
  package. They were updated to assert current Stage 3B status and the exact allowed data-only module
  set while continuing to prohibit Stage 3C modules. Targeted rerun: 45 passed.
- Final full suite: 1965 passed, 3 skipped, 2 pre-existing pandas warnings.
- Full `ruff check src/ tests/`, compileall, and `git diff --check`: PASS.
- Frozen Stage 3A hashes unchanged and default DB absent after all validation.
- Required pytest/compileall created ignored `__pycache__` directories. Two cleanup attempts were
  rejected by the execution safety policy even after paths were inspected; no bypass was attempted.
  No cache is tracked or included in commits.

## Result

The authorized fail-closed path is implemented, locally validated, pushed, and remotely validated.
Available target/calendar inputs are normalized and reproducible. Required primary-proxy gaps
remain, so Tier-1 is not trusted and Stage 3C is prohibited.

## Outstanding issues

- Complete daily official eligibility, full-market issued shares, and corporate-action/divisor
  inputs were not obtained.
- Oil and industry were intentionally not acquired after the ordered primary-proxy hard stop.
- No implementation defect remains; the unresolved items are upstream data gaps that deliberately
  keep the primary proxy untrusted and Stage 3C prohibited.

## Remote CI closeout

- Normal push advanced origin from `ae2225f` to `f6d1552` with the three planned logical commits.
- GitHub Actions run `31765256230` at `f6d1552` passed Windows and Ubuntu clean-clone jobs,
  including static, contract, capsule, full-suite, and identity-envelope gates.
- The provenance-gated cross-platform identity comparison passed.
- Only upstream GitHub Actions Node.js 20 deprecation annotations remain.
- Documentation commit `df62420` passed final-tip GitHub Actions run `31765642952` on Windows,
  Ubuntu, and the provenance-gated cross-platform identity comparison.
- Closure is conditional on the required GitHub checks attached to this governance-closeout commit
  reaching PASS. Its CI run identifier is external evidence and is not required to be embedded in
  the same commit; no follow-up CI-evidence-only commit is required.

## Final file changes

- Added Stage 3B Goal, work record, acceptance, three semantic/source contracts, development
  manifest, coverage report, five mechanism data modules, capability protocols, one-shot
  acquisition/offline-audit tool, and 22 focused tests.
- Updated only README's stale M3 status and two living-status regression assertions.
- Did not modify the frozen Stage 3A JSON contracts or any M2 artifact/database.

## Final Git state

- Branch: `feat/m3-mechanism-validation-mvp`.
- Starting commit: `ae2225f45c984f90b00ca28b3c35b421fe030359`.
- Semantic commit: `2ea1538`.
- Data implementation commit: `ffd4440`.
- Acceptance commit `f6d1552` pushed and CI PASS (`31765256230`).
- CI-evidence-only documentation commit `df62420` pushed and final-tip CI PASS
  (`31765642952`).
- Governance closeout: this document's containing commit; closed automatically when its attached
  required GitHub checks reach PASS.
