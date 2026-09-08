# Work record: M4 synthetic dataset adapter

Date 2026-09-08. Module: mechanism validation. Parent: Codex.
Goal: [contract](../goals/2026-09-08_m4_synthetic_dataset_adapter.md).

## Baseline and plan
Verified actual original M2 dirty status/HEAD, all worktrees, remote, stash, DB hash
and clean design HEAD 40d10b4. Live main is bab24f9. Read design, prior Goal, routing
protocol and agent agreement. Created isolated implementation branch from design.
Establish Goal, delegate source/tests to one Luna worker; parent reviews design edges,
protected scope and independently accepts actual implementation. No push or merge.

## Actual validation and delivery
Spawned one worker /root/luna_dataset_worker explicitly as gpt-5.6-luna, medium,
fork_turns=none. Worker owns only the new datasets package and its test file; parent
owns governance/evidence and full acceptance. No recursive delegation permitted.

Parent inspected actual planning validator and existing protection tests. Clarified
serializer versus four-argument validator responsibility in the Goal; the output has
no predicate threshold, so full recomputation must use the original plan. Sent worker
review notes about shared-series identity and exact coverage without Decimal rounding.

Baseline focused command from Goal: 132 passed in 2.64s. Module-path check confirms
this worktree's src is used. Existing tracked files remain unchanged.

Parent inspected the first in-progress source draft and sent concrete review findings:
mutable nested evidence, direct-construction validation, RETAIN_IN_DENOMINATOR status,
serializer semantic consistency, plan-role observation ordering, shared-series source
consistency, and an undefined local in dict conversion. These are draft findings, not
accepted behavior. Worker is completing implementation and targeted regression tests.

First worker final report omitted the assigned test file and could not run focused
pytest. Parent rejected this completion as CHANGES_REQUIRED and returned it to the
same Luna worker; no model fallback. Parent's isolated inline synthetic reproduction
confirmed invalid direct Observation construction and rehashed serializer inputs with
unknown status, missing complete rows and altered complete values were accepted.
Sent exact failures back for tests and repair. No full suite run on this failing draft.

Second worker delivery reported six passing tests; parent read them and found missing
matrix coverage plus callable-only assertions unrelated to claimed no-IO behavior.
Independent runtime repro still accepted partial complete rows, coverage_gate='2',
false quality rejection and a list-backed output, and mutated nested evidence through
dict.__setitem__. Escalated after two inadequate deliveries as required. Parent split
remaining work into bounded input and output/test steps and assigned the input step
to the same Luna worker; no silent expensive-model implementation fallback.

The narrowed input delivery had 16 passing tests but still lacked strict nested shape
validation and complete evidence handling. Parent explicitly announced and recorded
source ownership escalation; Luna retained only the test-file assignment. Parent
implemented recursive exact runtime types, immutable typed evidence, exact evidence
field parsing, deterministic source-ID conflict validation, context-independent decimal
string validation, and full audit/quality/complete-row checks in serialization.
Source Ruff passes. Independent repro after repair rejected all five prior invalid
cases and accepted valid four-argument recomputation. Luna is extending the test matrix.
An in-progress test run had 25 passed/2 failed: GT/GTE expected values incorrectly
treated factor 0 as not greater than -0.01. Asked worker to correct the mathematical
oracle; no product predicate was changed to match the incorrect test.

Luna supplied 34 meaningful focused cases including fixed input/output/serialized-byte
identities after further review removed callable-only testing and required actual
rehashing. Parent added 24 independent review regressions in a separate file covering
shared-series valid reuse/conflicts, zero controls, stale/extra domain evidence,
rehashed outputs, immutable copies, future PIT with weak flags, zero-gate empty sample,
missing binding/domain and statistical/data-engine call guards. Combined: 58 passed
in 2.29s; Ruff src/tests passes. Full suite started once after source/test stabilization.

After user continued the task, the previous execution session was unavailable (unknown
process ID), and no final exit/output could be recovered. Last observed progress was
67% with no failures. This is NOT evidence of a completed pass. Repeated full validation
because its result remained unresolved, now saving stdout/stderr, JUnit XML and exit
code under ignored tmp/adapter-validation. No tests or product code changed for rerun.

Persisted full suite completed: 2544 passed, 4 skipped, 2 warnings in 400.28s, exit 0;
JUnit/log/exit marker retained under tmp/adapter-validation. New suites contain 58
passing cases; all existing frozen protection tests pass. Final compileall and staged/
unstaged diff checks pass. Three evidence documents and their local links validated.
Original DB/stash were rechecked unchanged. Final live-main lookup failed twice due to
the configured 127.0.0.1 proxy being unavailable. Last successful remote lookup and
local origin/main were bab24f9; final live synchronization is unverified. No proxy
settings or remote resources were changed. No source/design/test baseline
modified, no push or merge. Committing exactly seven task additions locally; final
commit SHA is reported outside its own content. Verdict PASS; stop before next stage.
