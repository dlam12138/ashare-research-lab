# M4 compile-only plan ZIP delivery

Objective: deterministic ZIP delivery and direct offline reproduction of an
existing user plan package. Work directly, no DSH or delegation.

Verified baseline: origin/codex/m4-user-plan-package and live remote
83b2c99159ce1d1497e0f52f6701a1a06f3d268e (open PR89 dependency).
Clean isolated codex/m4-user-plan-archive at that commit.
Origin/live main: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222; existing 21
status lines preserved. Stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
Database SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Fresh ignored tmp/archive-baseline.json records 1355 protected file hashes and
56 foreign worktree branches, HEADs and statuses.

Allowed eight files: this Goal,
agent/record/2026-10-08_04-m4-user-plan-archive.md,
acceptance/2026-10-08_m4_user_plan_archive.md, README.md,
src/ashare_research/tools/{research_plan_package,research_plan_archive,research_entry}.py,
tests/test_research_plan_archive.py. Ignored local validation artifacts allowed.
Forbidden: existing tests, research_plan/compiler/mechanism code, fixtures,
reports, config, events, CI, governance/routing changes, data acquisition,
research execution, real backtests/holdout, databases, foreign trees/user changes,
stash changes, extraction/restoration, destructive cleanup.

Required behavior: research plan-archive --package DIR --output NEW_ZIP [--json]
or --verify ZIP [--json]. Capture each package member once and reproduce using
the original compiler before export. Add shared bounded capture verification
helpers without changing existing directory package receipts/behavior.
Exactly four ASCII members, stored without compression, fixed metadata/order,
no clocks/host paths. Bound archive before parsing, bound EOCD member count and
central directory before ZipFile construction, reject unexpected names/order,
duplicates, traversal, links, encrypted/compressed members, excess size and
noncanonical metadata/prefixes/trailers. Verify captured members through original
compilation and compare regenerated whole ZIP bytes. Never extract.
Existing output preserved; exclusive new file, no parent creation, managed path
and Windows junction guards, recheck before write, readback before success.
Retain owned partial output on late failure. Stable sanitized errors without
partial stdout. Hash consistency is not provenance, signature, evidence or
execution authorization. All original execution boundaries remain false.

Required tests: public CLI, determinism/relocation, original identity/boundaries,
single source/package/archive capture, source mutation, forged rehashed reports,
ZIP structural/member/metadata corruption and bounds, output collisions/races/
partial writes, junction/ancestor guards, no network/database/executor access,
unchanged legacy package verification.
Exact validation with PYTHONPATH=src and D:/量化分析/.venv/Scripts/python.exe:

    python -m pytest -q tests/test_research_plan_archive.py tests/test_research_plan_package.py tests/test_research_plan.py tests/test_research_entry.py
    python -m ruff check src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_archive.py
    git diff --check

Public subprocess export/verify demonstration under ignored tmp/ with receipts.
Independently inspect actual diff/commit, scope and acceptance; compare protected
hashes, primary/foreign state and stash; verify local/origin/live synchronization.
Acceptance: all local gates pass, only eight allowed files changed, unchanged
protected state and original directory behavior, reproduction rejects corruption.
Hosted CI reported separately with pending checks explicit.
Stop conditions: unexpected changes, baseline drift, protected mismatch,
conflicts, scope expansion, unresolved failures. Fix scoped defects, no gate bypass.
Commit/push: scoped normal commit and non-force branch push; stacked PR with base
codex/m4-user-plan-package, explicitly dependent on PR89. Never push main.
No automatic merge or next stage under current user governance.
