# M4 portable plan ZIP delivery and direct verification

Objective: user explicitly continued; root alone, no DSH/agents. Deliver existing
compile-only M4 plans as one deterministic ZIP and verify directly without
extraction. research plan --hypothesis JSON --archive NEW_ZIP [--json];
research plan --verify-archive ZIP [--json]. Existing directory modes preserved.

Verified baseline: dependency PR68 OPEN/MERGEABLE/CLEAN,42SUCCESS checks, head
codex/m4-plan-package@f9479c1d16d7257c3bf1cf4a1aa2960a0001a508. origin/live main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b. Fresh isolated codex/m4-plan-archive
from dependency head, not main. Before implementation snapshot
tmp/m4-plan-archive-baseline.json: original primary/status/diff/HEAD/local-main/
stash/database,408protected path hashes, foreign registrations/dependency status.

Allowed nine files: this Goal; acceptance/2026-10-07_m4_plan_archive.md;
agent/record/2026-10-07_03-m4-plan-archive.md; README.md;
src/ashare_research/tools/{research_plan,research_plan_package,research_plan_archive,research_entry}.py;
tests/test_research_plan_archive.py. Ignored evidence/runtime caches allowed.
Forbidden: existing test changes; mechanism/compiler/schema/config/registry/
adapters/executor/reports/events/evidence/fixtures/CI/M2 archive changes; sources,
network/providers/DB/statistical execution/outcomes/holdout; user dirt/stash/DB/
foreign worktree mutation; main/force push/merge/destructive cleanup.

Required: reuse original once-read bounded strict JSON and canonical plan-package
byte generation and verification; source and artifact identities/false boundaries
unchanged. ZIP exactly four flat regular members; fixed timestamps/order/metadata,
ZIP_STORED, no host paths/timestamps. Compile/encode/verify entirely in memory
before exclusively creating output, parent must exist; no intermediate directory
or extraction. Existing destinations/linked or reparse root/ancestors rejected.
Archive source is one bounded regular-file read. Reject missing/extra/duplicate/
traversal/absolute/backslash/NUL/directory/symlink/special members, compression/
encryption unsupported, member/total/archive bounds, bad CRC/truncated layouts.
Recompile stored hypothesis and compare all four bytes including manifest; forged
inventory hashes cannot conceal changes. Input bytes loaded once despite source
mutation after read. Errors sanitized/empty stdout. Write failure retains partial
output for inspection, never overwrite/delete or claim success. No atomic
publication or hostile concurrent filesystem sandbox promise. Invalid flags fail
closed. ZIP/hash/recompilation prove consistency only, not independent sealing,
authorship/historical-source validation/real research readiness or execution.

Exact validation, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan.py tests/test_research_plan_package.py tests/test_research_plan_archive.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_entry.py tests/test_research_plan_archive.py
git diff --check
Meaningful public cases: directory/ZIP byte identity, deterministic bytes after
relocation, original digests/boundaries/offline guards, actual single-read mutation
handoff; adversarial layout/CRC/forged inventories/bounds/flags and destination
preservation/write-failure/races/reparse paths. Actual relocated CLI ZIP demo,
independent committed diff/Goal/scope/tests/refs/protection review required.
Targeted tests once, affected failure/change reruns only, no full local suite.

Acceptance: local commands/demo pass, exact nine-file diff from verified dependency
head, original snapshots protected and task clean/synced; normal commit/push and
stacked PR targeting codex/m4-plan-package, explicitly depends on PR68. Verify
all required exact-head hosted checks and base/mergeability before final PASS.
Stop failed checks/conflicts/base or dependency drift/scope expansion; no bypass.
No automatic merging of either PR, no subsequent stage without explicit request.
Final PASS/CHANGES_REQUIRED/BLOCKED evidence packet includes exact commits/tests,
files, sync/protections, limitations and dependency/next-stage authorization.
