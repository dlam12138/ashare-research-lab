# M4 verified compile-only plan comparison

Objective: user continuation, root alone, no DSH/agents. Add research plan-compare
(--left DIR | --left-archive ZIP) (--right DIR | --right-archive ZIP) [--json],
showing pre-execution canonical config/contract/plan differences from two fully
verified existing plan packages, including mixed directory/native ZIP inputs.

Verified base codex/m4-plan-archive@1640ee54aec0fc20f283734a226a2eda86917862;
PR69 OPEN/MERGEABLE/CLEAN/42SUCCESS and actual test logs rechecked independently.
PR68 headf9479c1/base-main8d0fb4d remains OPEN/CLEAN. origin/live main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b. Fresh codex/m4-plan-compare from1640ee5.
Pre-implementation snapshot tmp/m4-plan-compare-baseline.json records original
primary/status/diff/refs/stash/database,408protected files, foreign worktrees and
both dependency-tree status snapshots.

Allowed seven files: this Goal; acceptance/2026-10-07_m4_plan_compare.md;
agent/record/2026-10-07_04-m4-plan-compare.md; README.md;
src/ashare_research/tools/research_entry.py;
src/ashare_research/tools/research_plan_compare.py;
tests/test_research_plan_compare.py. Ignored evidence/runtime caches allowed.
Forbidden: existing test/module/verifier/schema/compiler/method/registry/adapter/
executor/fixtures/config/reports/events/evidence/CI changes; new source acquisition,
network/providers/database/statistics/outcome/holdout/real research; user changes,
stash/databases/foreign-tree mutation; main/force push/merge/destructive cleanup.

Required: use unchanged directory/native ZIP public verifiers for complete
recompilation/integrity checking before emitting any output. No unverified report
read or source reread. Retain original hypothesis/source/config/contract/plan
digest identities separately; source-file SHA256 equality independent of canonical
semantic equality. Compare canonical config/contract/plan objects faithfully,
with only known top-level digest fields omitted from difference rows (identities
reported separately). Deterministic ordered JSON Pointer changes; recursive dict
and positional list diff, present/value wrappers distinguish missing from null,
additions/removals and string/bool/int values without coercion. No alignment by
invented semantic keys. Show complete before/after values; no truncation/host paths/
timestamps. JSON and escaped readable Markdown; identity summary and counts.
Source formatting-only edits report changed source hash but zero semantic rows
and equal compiled identities. No winner, improvement, effect size/statistics or
new policy vocabulary. All execution/readiness/source-evidence flags false;
consistency comparison is not independent sealing, authorship, real-source
validation or execution authorization. Input paths read only. Invalid flags or
corrupt/missing/linked/unsupported inputs fail closed with sanitized errors and
empty stdout; existing help/commands/global-option rejection preserved.

Exact validation, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan_compare.py
python -m ruff check src/ashare_research/tools/research_plan_compare.py src/ashare_research/tools/research_entry.py tests/test_research_plan_compare.py
git diff --check
Meaningful cases: public mixed directory/ZIP verification, exact original
identities/semantic deltas/format-only input/reversal, immutable inputs/relocation/
offline guards; added/removed list/dict values and RFC6901 escaping/type distinctions;
forged corrupt packages/native archives, missing/link input and invalid flags fail
before output. No existing tests rewritten/full local suite; affected repeats only.
Actual CLI demo and independent committed diff/Goal/scope/tests/protection review.

Acceptance: commands/demo pass, exact seven-file diff from dependency1640ee5,
original snapshots intact, owned clean/synced; normal commit/push and stacked PR
targeting codex/m4-plan-archive, explicitly depends on69 then68. All required
exact-head hosted checks/base/mergeability independently checked before PASS.
Stop failed checks/conflicts/base/dependency drift/scope expansion, no bypass.
No automatic merge or following stage. Final PASS/CHANGES_REQUIRED/BLOCKED packet
includes exact commits/files/commands/results/protections/sync and dependency limits.
