# M4 native plan ZIP acceptance evidence

Goal agent/goals/2026-10-07_m4_plan_archive.md. User continuation, root alone,
no DSH/agents. Verified dependency codex/m4-plan-package@f9479c1d16d7257c3bf1cf4a1aa2960a0001a508,
PR68OPEN/MERGEABLE/CLEAN/42SUCCESS independently rechecked before implementation;
origin/live main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged. Owned branch
codex/m4-plan-archive freshly created from dependency, not main. Nine scoped files.

Added research plan --hypothesis JSON --archive NEW_ZIP [--json] and
--verify-archive ZIP [--json]. Reuses original strict bounded JSON, once-read bytes,
existing canonical four-file generation and shared recompilation verification.
Original directory/stdout behavior and existing tests preserved. No intermediate
directory/extraction/network/database/execution. ZIP_STORED with fixed names,
order/timestamps/Unix regular-file metadata, no host paths/timestamps in receipts.
All original digests/boundaries retained; no independent-seal/research-ready/
execution or historical-source validation claim. Verification receipt reports
actual loaded archive byte SHA256/size and original verified compiled envelope.

Compact native ZIP preflight checks EOCD before ZipFile allocates member objects:
exact four-member count/fixed central-directory size, single disk, no prefix/
trailing data/ZIP64/comment. Member rules reject extras/comments, invalid names,
missing/extra/duplicate/traversal/absolute/backslash/NUL/directory/link/special
entries, unsupported compression/encryption, oversized/inconsistent member sizes,
total/archive bounds and bad CRC/layouts. No compression-bomb decompression occurs.
Stored hypothesis is recompiled and all four artifacts compared byte-for-byte;
forged inventory hashes cannot conceal edited plans. Not a general-purpose ZIP
verifier; only the documented native compact uncompressed format is supported.

Existing/new destinations created exclusively only after compilation/encoding/
full in-memory verification; parent must exist. Regular bounded archive input
loaded once; link/reparse paths and ancestors rejected even with relative paths.
Concurrent creation race preserves new user content through xb. I/O failure
reports sanitized failure/empty stdout, retains partial file, never deletes or
overwrites. No atomic publication or hostile concurrent filesystem guarantee.

Exact local commands, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_research_plan.py tests/test_research_plan_package.py tests/test_research_plan_archive.py
# 8 passed in1.57s; no existing tests changed/failed/full suite repeated.
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_entry.py tests/test_research_plan_archive.py
# All checks passed. Two test style findings corrected before test execution.
git diff --check
# PASS.
```
Independent code review added first-member offset validation to reject unmanaged
prefix data even when it starts with ZIP magic and has a valid EOCD. Added a
real prefixed ZIP case. Affected-only rerun:
python -m pytest -q tests/test_research_plan_archive.py,3passed; Ruff/diff rechecked.

Three new public cases cover ZIP/directory exact bytes, direct original compilation
identities, deterministic exports/relocation, false boundaries, service/network/DB/
executor/extraction guards, mutation after original source and archive reads;
adversarial names/layout/modes/compression/encryption/CRC/truncation/forged metadata
and resource limits; invalid flags/malformed sources, existing-file preservation,
missing parents/sources, reparse ancestors, exclusive-create races and partial
write failures without success/overwrite/deletion. Original5tests still pass.

Actual CLI subprocess demo, exit0/no stderr:
```powershell
python -m ashare_research.cli research plan --hypothesis docs/examples/m4_hypothesis.json --archive tmp/plan-archive-demo.zip --json
# Renamed to tmp/plan-archive-relocated.zip.
python -m ashare_research.cli research plan --verify-archive tmp/plan-archive-relocated.zip --json
```
Archive19267bytes; SHA2568102f4e360228dbe3990d12918c806eb65230f33c5dd110386698d2a627e96a3;
contract56e914cf9afef8af935c2553e242dc2c0c888d537c5494dabb05eb094a1c4610;
plan c73268f7b63a24f300aec8e5fd3f20adbe3fc1031b85acebe3835148964c3267.
Source immutable and false boundaries; export/verify receipts retained in
tmp/plan-archive-{export,verification}-receipt.json. Actual Windows junction under
owned ignored tmp: relative verify and export-through-ancestor rejected exit2/
LINKED_PACKAGE_PATH/empty stdout, target unchanged/new.zip not created; retained.

Pre-implementation tmp/m4-plan-archive-baseline.json stores original primary
dirty/untracked/diff/refs/main/stash/database/foreign worktrees/dependency status
and408protected path hashes. Independent committed scope/Goal/diff/tests/protection/
PR refs/sync/hosted checks recorded in tmp/m4-plan-archive-final-review.md. Local
evidence PASS; final acceptance requires that exact-head hosted review. Normal
push and stacked PR targeting codex/m4-plan-package; depends on OPEN PR68.
No automatic merge of either PR or following stage under supplied user governance.
