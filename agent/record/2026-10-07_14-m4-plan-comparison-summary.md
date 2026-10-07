# Plan comparison section summary

User continues bounded engineering and explicitly requests root alone, no DSH.
Verified primary3679b1b/main8d0fb4d/basee427e5a, PR80 OPEN/MERGEABLE with
29SUCCESS/9pending at initial query. Fresh clean isolated
codex/m4-plan-comparison-summary. Read agent agreement/record guidance/latest
records, the verified plan comparison module, plan/package/archive verifiers,
diagnostic and comparison summary conventions, public help/README and relevant
tests. Goal: agent/goals/2026-10-07_m4_plan_comparison_summary.md.
Before implementation captured47worktrees/46foreign states/27dirty hashes/
427protected hashes and checked database/stash/localmain against the previous
stage baseline; evidence at tmp/plan-comparison-summary/baseline.json.

Pre-code baseline PASS. Added --summary/--section to plan-compare. The summary
is a pure projection of the captured fully verified comparison; each side is
still reproduced once through the unchanged directory/ZIP verifier. Sections
validate before IO; unknown sections reject INVALID_SECTION and a bare
--section rejects INVALID_ARGUMENTS. Per-section counts and totals must
reconcile with the captured globals or fail closed with
COMPARISON_SUMMARY_MISMATCH; without --summary legacy JSON/Markdown stay equal
to base.

Actual targeted21passed48.37s; Ruff and git diff --check PASS; no failed test,
existing test edit or full local-suite claim. Six new cases cover exact
projection, legacy equality, all transports, repeated/reordered sections,
NO_MATCHING_CHANGES, count/identity/boundary preservation, once-per-side
verification with mutation-after-read handoff, invalid options before IO,
doctored-report guards and offline/no-write/junction limits. AST review: every
pre-existing function/class except cli main is unchanged; only the projection
additions and cli main changed
(tmp/plan-comparison-summary/calculation-review.json).

Actual demo:10changes (config2/contract2/plan6); identical summary across four
transports; config+plan filter shows8rows with global counts intact; format-only
pair is canonically equal with NO_MATCHING_CHANGES; invalid section and bare
--section reject; real junction and forged plan.json with rewritten manifest
fail closed;11source hashes unchanged and no files created. Evidence in
tmp/plan-comparison-summary/demo/.

Protection review PASS:46foreign registrations/HEAD/branches/statuses,27dirty
hashes,427protected hashes and database/stash/localmain unchanged; compilers,
plan/preparation verifiers and both preparation comparison modules byte-equal
to base. Exact commands/cases/limits:
acceptance/2026-10-07_m4_plan_comparison_summary.md.

Seven-file scoped normal feature commit/push and PR stacked on80. Final actual
head/scope/clean tree/refs/protections and hosted state retained in
tmp/plan-comparison-summary/final-evidence.json.
No main/force push, automatic merge or following stage.
