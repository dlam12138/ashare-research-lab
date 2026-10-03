# Direct delivered ZIP verification — acceptance checkpoint

Goal agent/goals/2026-10-03_m2_archive_verification.md; record
agent/record/2026-10-03_03-m2-archive-verification.md. Base origin/live main
f291ea6ed06770d8b778d3734a569775a60aaeae; branch codex/m2-archive-verification.
Own execution, no DSH/subagents. This checkpoint precedes commit and hosted gates;
final actual CI/merge/protection evidence is retained in ignored tmp review packet.

Implemented research archive --verify ZIP [--json] and public verify_archive.
Shared one bounded source snapshot / safe temporary decoder / full canonical
package verifier with restore. Original export/restore guards, receipt schema,
errors, deterministic ZIP bytes and limits preserved. Verification uses owned
temporary decoding, never a caller destination; reports status verified and
existing SHA/count/manifest/complete verifier metadata and limits. --output is
forbidden in verify mode and remains required in export/restore. Invalid argument
combinations rejected before source reading with sanitized error2/no stdout.
CLI remains offline, no legacy config/log/default-database initialization.

Exact local commands with PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe in the owned worktree:
```powershell
python -m pytest -q tests/test_archive_verification.py tests/test_package_archive.py::test_unsafe_members_limits_malformed_and_crc_fail_before_destination
python -m pytest -q tests/test_archive_verification.py::test_six_real_kinds_receipt_compatibility_no_destination_and_process_cli
python -m ruff check src/ashare_research/tools/package_archive.py src/ashare_research/tools/research_entry.py tests/test_archive_verification.py
python -m ashare_research.cli research archive --verify tmp/m2-offline-workflow.zip --json
git diff --check
git diff --exit-code f291ea6ed06770d8b778d3734a569775a60aaeae -- reports config events evidence src/ashare_research/mechanism tests/fixtures
```
Initial targeted run:1 failed,2 passed in60.29s. New test incorrectly counted
all nested canonical-rebuild TemporaryDirectory calls as ZIP decoder roots.
Corrected exact assertion to six m2-package-archive roots while retaining the
requirement that every observed temporary root is removed. No product change,
guard relaxation, existing test modification or skipped test. Only affected
six-kind/real-process acceptance rerun:1 passed in81.30s (0:01:21).
Scoped Ruff and diff/protected tracked checks passed.

Two new acceptance cases cover six real package kinds with exact old receipt
compatibility; every byte verifier flags; no source mutation, destination or
absolute path leak; all owned temporary roots cleaned; readable CLI with forbidden
legacy services and actual workflow subprocess JSON. Failure case covers seven
invalid argument combinations before any source open, missing/directory/link and
unreadable sources, malformed ZIP, CRC corruption, traversal and rehashed financial
claim with valid ZIP CRC rejected by canonical reconstruction, no foreign changes,
single bounded source read and post-read mutation not affecting receipt. Existing
unsafe archive acceptance passed on the shared load/decoder. No local full suite.

Actual retained workflow ZIP verification exited0:131files,6,210,409ZIPbytes;
ZIP SHA2564cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561;
manifest SHA2567889bea763c849fcf194dd95c87b32802fe53b4e381af616e15398e15212d973.
Original ZIP hash unchanged. Receipt tmp/m2-archive-verification-result.json.
Primary dirty/untracked snapshot, HEAD3679b1b, localmain966206f, stashcb568efd,
database hash and427protected paths/hashes unchanged; physical snapshots saved.

Installed compatible pinned baseline still required. This proves reproducibility,
not authenticity, historical availability or research/production qualification.
Known33facts/66missingparents and provider historical evidence gaps unchanged.
No scope expansion; commit/push scoped branch, all42hosted gates and independent
exact base/head/merge/protection review required before standing-authorized merge.
Engineering continuation allowed only with stage authorization; no automatic next
stage, new data acquisition, real research/backtests/holdout or production admission.
