# M4-B registry snapshot membership check

User continues bounded engineering and explicitly requests root alone, no
DSH. Verified primary3679b1b/main8d0fb4d/base fbe3898, PR86 OPEN/MERGEABLE
with hosted 36SUCCESS/4pending at the prior publication review. Fresh clean
isolated codex/m4-registry-membership. Read the previous stage records, the
frozen registry package, the frozen view/compare modules and the
comparison-summary precedent. Goal:
agent/goals/2026-10-07_m4_registry_membership.md. Before implementation
captured 53worktrees/52foreign states/28dirty hashes/427protected hashes
against the previous tmp/registry-compare-summary baseline and checked
database/stash/localmain against it; evidence at
tmp/registry-membership/baseline.json.

Pre-code baseline PASS. Added research registry-membership --record
RECORD.json --snapshot SNAPSHOT.json [--json] as a read-only mechanical
membership check between one explicit canonical record and one explicit
canonical snapshot: both files are read once each (max 1MiB) and validated
through the frozen build_record_view/build_snapshot_view entries, so every
single-side failure keeps the previous stable codes; the check then answers
whether the record's (hypothesis_id, hypothesis_version) is registered and
whether the embedded entry has identical canonical record bytes.
registered_identical reports all-true equality; registered_different reports
the sorted changed-field rows and the six-key equality map; not_registered
reports the sorted same-id versions with an all-false equality map and no
changed fields. Captured-view invariant violations fail closed as
REGISTRY_MEMBERSHIP_MISMATCH, re-verified in main before any output, and the
embedded entries are re-parsed/re-serialized through the frozen entries with
record count, real demo count and registry digest recomputed through the
frozen builder and count_real_demo_candidates. The module's public callable
surface stays exactly build_membership/main/render_markdown; every new
helper is underscore-private with no **kwargs and no forbidden name
fragment.

Actual targeted66passed49.07s (eight new cases plus the unchanged comparison
summary, compare, preflight, view, registry and entry suites); Ruff and
git diff --check PASS; no failed test, existing test edit or full local-suite
claim. The new cases cover the exact identical report bytes with delegated
entry/CLI/module outputs and the unchanged frozen 13-entry registry surface,
the registered_different sorted list/equality with Markdown rows, absent
keys with and without same-id versions, delegated frozen failure codes from
both sides including pinned NON_CANONICAL_SERIALIZATION and
REGISTRY_VIEW_MISMATCH, doctored-report guards with sanitized CLI failure,
argument shapes rejected before IO and single-read/offline/no-write/
determinism guards. AST review
(tmp/registry-membership/calculation-review.json): research_entry.py keeps
every declaration and every pre-existing COMMANDS entry unchanged and only
inserts one registry-membership entry immediately after registry; the new
membership module has exactly the declared public/private surface and no
sqlite3/duckdb/requests/urllib/subprocess/socket reference;
research_registry.py, research_registry_compare.py, the registry package and
the previous view/preflight/compare/summary tests are byte-equal to base.

Actual demo: six previous view/preflight/compare/summary invocations
byte-equal to the previous worktree; identical/different/absent-same-id/
absent-other-id checks and the Markdown projection report exact mechanical
membership; seven fail-closed fixtures return exactly the documented
sanitized codes with empty stdout; membership runs created no files,
465 source files and 11 case files stayed unchanged and replay is
byte-equal. Evidence in tmp/registry-membership/demo/.

Protection review PASS:52foreign registrations/HEAD/branches/statuses,
28dirty hashes,427protected hashes and database/stash/localmain unchanged;
the untouched tools, research_registry.py, research_registry_compare.py, the
registry package and the previous tests are byte-equal to base. Exact
commands/cases/limits: acceptance/2026-10-07_m4_registry_membership.md.

Seven-file scoped normal feature commit/push and PR stacked on86. Final
actual head/scope/clean tree/refs/protections and hosted state retained in
tmp/registry-membership/final-evidence.json.
No main/force push, automatic merge or following stage. No record
production, transition application, promotion, default or real candidate
dataset loading, real research/statistics/holdout or literature acquisition.
