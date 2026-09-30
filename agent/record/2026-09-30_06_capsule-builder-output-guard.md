# Capsule builder output boundary

Date: 2026-09-30. Module: reproducible value-assessment infrastructure.
Goal: agent/goals/2026-09-30_capsule_builder_output_guard.md.
Source: user requested continuation after PR #37 delivery.
Base: origin/main/live main 74418cc39c89945aa1a45e4627ee3873fced92b8.
Working branch: codex/capsule-builder-output-guard, initially clean.

Verified actual branch/HEAD/worktrees/remotes/stash/database, recent three
records, governance/standing authority and actual PR #37 merge/42 successful
checks. Preserved prior delivery branch and all primary dirty/untracked files.
Read build_test_capsule: output mkdir(exist_ok=True) precedes validate_snapshot.
That can block same-path retry after invalid input and adopt an output directory
created by another caller after the initial exists check.

Plan: parent reproduces both defects in owned synthetic temp paths; DSH makes
bounded ordering/exclusive-mkdir/symlink guard change and tests; parent reviews
diff, runs exact focused suite/lint and old/new valid-manifest parity, checks
protected state, writes acceptance and creates one scoped PR. All hosted checks
and head/base guards mandatory before merge under standing authorization.

DSH receives write authority only for the source function and new test file,
no tests/Git/network/real input/recursion; parent handles exact validation because
of the known DSH temp-directory ACL limitation. Validation/implementation pending.

Decision: validate-before-create and exclusive mkdir close the two initial
boundary defects without adding complex cross-platform directory publication
or dangerous rollback cleanup. Errors later in an owned build may still leave
partial output; not claimed fixed. No data or research method changes.

## Parent baseline reproduction

Ran real committed synthetic fixture in an owned TemporaryDirectory. Missing
input left invalid-parent/capsule behind and blocked corrected same-path retry.
Deterministic Path.mkdir boundary injection created a competing caller directory
with capsule_manifest.json sentinel after the initial exists check. Baseline
adopted that directory and overwrote the caller sentinel. Exit 0:
invalid_input_left_output=true, corrected_retry=blocked, competing_output=adopted,
caller_manifest_preserved=false. Normal cleanup removed only probe-owned files.
Identical command retained for repaired comparison; no real database used.

## Implemented and independently validated

DSH completed one bounded repair and froze: initial exists-or-is_symlink guard,
validate_snapshot before any output mkdir, exclusive mkdir(exist_ok=False),
docstring and new regression module. Parent reviewed actual diff and all new tests.
Worker ran read-only AST/scoped lint/diff checks despite assigning validation to
parent; no pytest/network/Git mutation or out-of-scope edits observed. Parent
acceptance relies on independent results, not worker assertions.

Parent identical reproduction changed to false/success/rejected/true, preserving
caller manifest. Old/new successful manifest dictionaries and bytes equal;
logical digest 8d89d7d4a71f0e5dcaacccabc231e70411822f457c2dda9e03fe846c750f0ed1.
First parity harness failed relative import due unqualified temporary module;
package-qualified harness passed, with no source change.

Goal exact eleven-module pytest: 221 passed, 6 skipped in 49.45s, exit 0.
Four symlink-privilege skips and two absent baostock snapshot skips, explicit.
Full-tree pinned Ruff passed; git diff --check passed. No tests weakened.
Primary exact status/diff/HEAD/stash snapshot equal; protected DB hash unchanged;
live main still 74418cc39c89945aa1a45e4627ee3873fced92b8.
Acceptance: acceptance/2026-09-30_capsule_builder_output_guard.md includes exact
commands, probe evidence, known limits and mandatory hosted delivery gate.
Parent preparing scoped commit/PR; hosted checks and guarded merge still pending.
