# M4 offline progress check

Date: 2026-09-30. Module: mechanism research engineering.
Goal: agent/goals/2026-09-30_m4_offline_progress_check.md.
Base f78aeb20349ff80e537b987abf15c4381ba5f360; branch
codex/m4-offline-progress-check initially clean.
User requested continued advancement and better pace.

Verified actual primary/working branch, HEAD, remote/main, stash/worktrees/DB;
read governance, agent agreement, record README and last three task records;
PR #38 is actually MERGED with 42 successful checks. Primary dirty files preserved.
Read current README, K1 integration, K2 preflight, EIA PIT assessment and Table11
record. Transport succeeded but missing historical publication/availability/version
evidence remains; monthly CSV does not supply the five daily observations.
Existing README lacks later offline real-format K1/PIT diagnostic entry guidance.

Decision: stop incremental low-priority capsule hardening and consolidate existing
metadata diagnostics into one usable offline entry. Small six-file engineering
change; reuse frozen assessment rather than new source selection or real execution.
No provider download, real values, credentials or DB access. Narrow scope prevents
a partial EIA diagnostic from claiming complete K2 or project readiness.
One bounded DSH worker edits new tool/test and concise README; parent reviews and
runs focused meaningful checks once, relying on unchanged product and hosted full
regression. Implementation and validation pending.

## Implementation and parent acceptance

DSH delivered fixed-path metadata tool, 23 new tests and concise README usage,
then froze. Parent inspected actual files, with no prior evidence/assessor/product
changes. Tool recomputes the frozen assessment after strict JSON, allowlisted
linked digests and frozen-identity checks, compares retained bytes, outputs text
or JSON, and separates diagnostic success from research readiness/authorization.

DSH instruction deviation: ran tests despite explicit parent-only validation;
known sandbox temporary-directory permission error led it to add a custom UUID
default-permission scratch fixture. Parent restored standard pytest tmp_path and
removed the custom cleanup workaround, keeping all failure assertions. Worker
claimed no deviations, but this record preserves the actual deviation. No fallback.

Parent exact Goal commands: focused pytest 25 passed in 1.95s, no skips; original
assessor unittest 7 passed in 0.004s; text and JSON CLI exit 0 with PIT missing and
research_ready/execution_authorized false; assessor --check and artifact validator
PASS; pinned Ruff PASS; git diff --check PASS. Staged gate required before commit.
No duplicate full product suite locally; mandatory hosted full regression follows.

Acceptance includes exact commands, negative cases, metadata-only limits and
deviation: acceptance/2026-09-30_m4_offline_progress_check.md.
Primary exact snapshot and stash match; protected database hash unchanged; live
main remains f78aeb20349ff80e537b987abf15c4381ba5f360. Six allowed files only.
Local gate PASS. Scoped PR delivery and all hosted checks pending; exact final
Git/PR/merge/synchronization evidence supplied in final handoff. No new research.
