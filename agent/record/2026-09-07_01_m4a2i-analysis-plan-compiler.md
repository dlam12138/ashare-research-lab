# Work record: M4-A.2I analysis plan compiler

Date: 2026-09-07. Agent: Codex. Module: mechanism validation / engineering governance.
Goal: [task contract](../goals/2026-09-07_m4a2i_analysis_plan_compiler.md).
Base: 349101a1bae61dc4a11991e2420d21eedb69ff87; branch codex/m4a2i-analysis-plan-compiler.

## Scope and start
Read agreement, record index and latest three records, frozen A.2 design, A.1 compiler,
config and digest helper. Checked original worktree, remote, stash, DB and PR checks.
A transient ls-remote connection reset succeeded on retry. Merged #8 and #7 using
squash and exact --match-head-commit; no branches deleted. Verified #8 tree identical
to approved head and #7 only adds original six files. Created independent worktree.
Main CI running. Installing declared dependencies in a new local venv.

## Decisions and plan
Use a frozen envelope and existing immutable JSON objects for nested declarative sections.
Recheck direct contract construction structurally, then reuse A.1 semantic parser/compiler
without changing A.1. Preserve control and registry ordering. Compile no data or statistics.
Implement and test mappings, update current README assertions, run focused/full checks,
inspect protections, commit and push scoped files, create PR and await CI. No next stage.
Only synthetic contracts are used; no research data, outcomes or thresholds are selected.

## Implementation and verification
- Added the planning subpackage only; existing A.1 and M3 modules remain unchanged.
  Contract runtime type checks reject mutable containers and bool/int substitution.
  An A.1 semantic round-trip must equal the original envelope, including source identity;
  it is validation, not a replacement or repair of input. The plan validator reuses A.1
  field semantics with internal placeholders for fields not projected into the plan.
  Those placeholders are never output or bound as the original source contract.
- Control role instances CONTROL_0001... expand in contract order, with corresponding
  beta_control_0001... terms. Sections use frozen dataclasses/tuples/JSON objects.
  Only canonical_digest is reused from the M3 digest module; no execution API is called.
- README now distinguishes merged A.2 design, this PR's compile-only implementation,
  and unimplemented data/execution adapters. Only current-status doc assertions changed;
  historical M3 stop, A.1 status and all artifact hash checks were retained.
- Initial new-test run: 58 passed, one failure at the intentionally unfilled golden
  identity placeholder. Full mapping against frozen design passed. Recorded the reviewed
  synthetic contract/plan/serialized-byte identities, then the focused suite passed 124.
- Final boundary review added all four condition operators, rehashed source-identity
  rejection and bool/int plan-field checks: focused suite **132 passed in 2.29s**.
  New A.2I suite contributes 67 tests. Ruff and compileall pass; diff check passes.
- Main 349101a CI: all seven workflows completed successfully, **21/21 checks**.
- Compared protected source/report/workflow/dependency paths with implementation base:
  no changes. The six merged design files match approved PR #7 bytes. Original M2 status,
  stash and DB hash still equal the Goal baseline. All existing worktrees retained.
- Full offline suite: **2486 passed, 4 skipped, 2 existing pandas date-parse warnings**,
  479.70s. One full run after stable implementation, no research/protection failures.
- Code and all synthetic tests committed as 745fffe28494e41e169c95a004241160ee47730a.
  README/current-status assertions and this task's Goal/record/acceptance form the
  second scoped commit. Full commands, identity values and changed paths are recorded
  in [acceptance](../../acceptance/2026-09-07_m4a2i_analysis_plan_compiler.md).
- Final local main ref 9e016e7 was intentionally retained; fetched origin/main and
  actual GitHub main both equal implementation base 349101a. No default DB exists in
  this isolated tree. Generated ignored environment/test output is retained.

## Delivery
Local acceptance complete. Ordinary feature push and one PR to main follow this evidence
commit; exact final HEAD, remote equality and final CI outcomes will be recorded in the
PR body, without repeated evidence commits. No new PR merge or next-stage work is authorized.
