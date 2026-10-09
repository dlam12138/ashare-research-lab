# Plan review summary

User continues bounded engineering and explicitly requests root alone, no DSH.
Verified primary3679b1b/main8d0fb4d/base0b9c358, PR81 OPEN/MERGEABLE with
36SUCCESS/4pending at initial query. Fresh clean isolated
codex/m4-plan-review-summary. Read the latest records, the compile-only plan
module and plan package/archive verifiers, diagnostic and comparison summary
conventions, public help/README and relevant tests. Goal:
agent/goals/2026-10-07_m4_plan_review_summary.md. Before implementation
captured48worktrees/47foreign states/27dirty hashes/427protected hashes and
checked database/stash/localmain against the previous stage baseline; evidence
at tmp/plan-review-summary/baseline.json.

Pre-code baseline PASS. Added --summary/--section to plan. The summary is a
pure projection of the captured compile or verify report; the compile mode
compiles once and each verify transport fully reproduces the delivered
package/archive once through the unchanged verifier. Selectors validate before
IO: export modes with any selector and a bare --section reject
INVALID_ARGUMENTS; unknown or malformed sections reject INVALID_SECTION.
Repeated sections dedupe in the fixed canonical order; omitted sections show
all nine. Identity, shape counts, boundary and notes survive filtering
unchanged, and the projection fails closed with PLAN_SUMMARY_MISMATCH on
schema/status, boundary, hypothesis/digest/state or role/term/summary
inconsistencies. Without --summary legacy JSON and default Markdown stay
byte-equal to base.

Actual targeted24passed36.17s; Ruff and git diff --check PASS; no failed test,
existing test edit or full local-suite claim. Nine new cases cover exact
projection across compile/directory/ZIP transports, legacy JSON/Markdown
byte-equality, repeated/reordered sections, payload mapping,
identity/shape/boundary preservation, once-read snapshot handoff for compile
and both verify transports, invalid selectors and export-mode rejection before
IO, doctored-report invariant guards with sanitized CLI failure, sanitized
verifier failures and offline/no-write guards with a monkeypatched reparse
path. AST review: every pre-existing function/class except cli main is
unchanged; only the five projection additions and cli main changed
(tmp/plan-review-summary/calculation-review.json).

Actual demo: five legacy invocations byte-equal to the base worktree; the
summary is identical across compile/directory/ZIP modes except the source
legend; filtering to method+holdout keeps identity/shape/boundary/notes;
repeated sections dedupe; invalid section and bare --section reject before IO;
a real Windows junction and a forged manifest-consistent plan.json fail
closed; six source hashes unchanged and summary runs created no files.
Evidence in tmp/plan-review-summary/demo/.

Protection review PASS:47foreign registrations/HEAD/branches/statuses,27dirty
hashes,427protected hashes and database/stash/localmain unchanged; the
preparation tools, plan comparison and plan package/archive verifiers are
byte-equal to base. Exact commands/cases/limits:
acceptance/2026-10-07_m4_plan_review_summary.md.

Seven-file scoped normal feature commit/push and PR stacked on81. Final actual
head/scope/clean tree/refs/protections and hosted state retained in
tmp/plan-review-summary/final-evidence.json.
No main/force push, automatic merge or following stage.
