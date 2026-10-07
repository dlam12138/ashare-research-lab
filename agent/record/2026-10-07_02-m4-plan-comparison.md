# Compile-only plan comparison

User requested continued work by root agent without DSH. Verified live/main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b and protected primary state before work.
Goal: agent/goals/2026-10-07_m4_plan_comparison.md.
Added optional --compare-with to existing plan command, reusing its original
compiler entry once per distinct path. Full original before/after reports,
source SHA256 and compiler digests preserved; sorted canonical changes retain
ordered lists, explicit presence and exact JSON types. Existing single mode
unchanged. No execution/network/database access or method/policy changes.

Seven scoped files. Targeted existing/new/entry tests: 8 passed in 38.48s.
Review then improved JSON type discrimination and escaped pointer sorting;
affected comparison tests: 2 passed in 0.78s. Ruff and diff checks pass.
Public CLI smoke retained at tmp/plan-comparison/smoke.json. No failed/full
local suite or existing test edits. Independent actual diff/Goal/evidence and
protected primary HEAD/status/stash, 21 primary hashes and 427 frozen hashes
checked; foreign HEAD/branch identities unchanged. Foreign routing edits
untouched; foreign file hashes and one quoted primary non-ASCII untracked
path not captured, no claim of comprehensive ignored-runtime protection.

Acceptance: acceptance/2026-10-07_m4_plan_comparison.md.
Normal scoped commit/push/PR; no automatic merge under current user governance.
No next stage or real research authorized by this engineering comparison.
