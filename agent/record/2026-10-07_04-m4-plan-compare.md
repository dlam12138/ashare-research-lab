# M4 compile-only plan comparison record

User continuation executed by root alone; no DSH or delegated agents.
Goal: agent/goals/2026-10-07_m4_plan_compare.md.
Fresh branch codex/m4-plan-compare from verified archive branch commit
1640ee54aec0fc20f283734a226a2eda86917862. Before implementation independently
checked actual Git/worktrees/remotes/stash/protected hashes and both dependency
PRs, including archive final gate and retained actual full-suite summaries.
Original primary tree, stash, databases and unrelated worktrees preserved.

Added research plan-compare, using existing complete verifiers without edits,
to compare canonical config/contract/plan JSON. Source SHA and compiled identities
are reported separately; deterministic RFC6901 diff distinguishes missing/null
and scalar types, lists use original indexes. JSON and escaped Markdown remain
compile-only and read-only. README explains invocation and limits. No unrelated
modules, existing tests, CI definitions or protected baselines changed.

Final local validation: three targeted tests passed in1.22s, Ruff passed, diff
check passed. First targeted run found renderer iteration order mismatch after
JSON key sorting; fixed the source and reran the affected tests. Real subprocess
demo produced10differences, unchanged input hashes, and fail-closed rejection of
an actual Windows junction. Exact commands/results in acceptance/2026-10-07_m4_plan_compare.md.

Only seven contract-authorized tracked files. Normal commit/push and stacked PR
base codex/m4-plan-archive, depends69 then68. Exact final head, actual hosted test
summaries, all-check gate, committed independent review and protection/sync evidence
go in ignored tmp/m4-plan-compare-final-review.md. Pending hosted results are not
represented as successful. No automatic merge or next stage.
Independent committed review found Markdown emphasis/link syntax needed escaping;
fixed renderer, extended the new test, reran affected checks and made a normal
follow-up commit. Final hosted gates apply to this corrected head.
