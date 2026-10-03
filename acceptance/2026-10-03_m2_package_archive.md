# Verified portable ZIP package acceptance checkpoint

Goal agent/goals/2026-10-03_m2_package_archive.md; record
agent/record/2026-10-03_02-m2-package-archive.md. Base origin/live main
21dced22ae1ef2eb7724372499418986ce473012; branch codex/m2-package-archive.
Eight-file scope, own execution/no DSH/subagents. This checkpoint is precommit;
hosted/head/PR/merge gates are recorded in the final ignored review evidence.

Public load_verified_package returns a fresh verified canonical byte map plus
original metadata; verify_package remains the compatible metadata-only wrapper.
Archive creation verifies once and never rereads retained files after handoff.
Sorted ZIP_STORED members/fixed1980date/regular0644permissions make identical
packages yield identical ZIP bytes in different paths. Archive restore reads a
bounded source snapshot, validates all members before temporary extraction,
fully verifies in an owned TemporaryDirectory, then publishes only canonical
bytes to a new caller root. No extract/extractall or recorded-path filesystem
reads. Original nested formats/bytes preserved; no acquisition/formulas/admission,
database/cache/research/holdout changes or previous builder/test modifications.

Bounds256members/32MiB member/128MiB unpacked/129MiB ZIP. Reject raw traversal,
absolute/drive/backslash/NUL/dot/empty/Windows device/trailing-dot-space names,
case/prefix collisions, duplicate entries, file/directory conflicts, symlinks and
Unix/DOS directory or nonregular types, encrypted/unsupported compression,
truncation/CRC/DEFLATE corruption. No caller destination on bad archive or failed
source verification. Existing output and symlink ancestry rejected before work
and again before exclusive creation; source-internal ZIP outputs rejected.
Late write failure preserves owned partial output, error2/no stdout, no cleanup
or atomic publication claim. Existing research/data/history limits retained.

Exact commands: owned worktree; PYTHONPATH=src; `python` executable
D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_package_archive.py
python -m pytest -q tests/test_package_archive.py::test_unsafe_members_limits_malformed_and_crc_fail_before_destination tests/test_package_archive.py::test_rehashed_tampering_source_failures_and_verified_byte_handoff
python -m pytest -q tests/test_package_archive.py::test_unsafe_members_limits_malformed_and_crc_fail_before_destination
python -m ruff check src/ashare_research/tools/package_archive.py src/ashare_research/tools/package_verification.py src/ashare_research/tools/research_entry.py tests/test_package_archive.py
python -m ashare_research.cli research archive --package tmp/m2-offline-workflow --output tmp/m2-offline-workflow.zip --json
python -m ashare_research.cli research archive --restore tmp/m2-offline-workflow.zip --output tmp/m2-offline-workflow-restored --json
git diff --check
git diff --exit-code 21dced22ae1ef2eb7724372499418986ce473012 -- reports config events evidence src/ashare_research/mechanism tests/fixtures
```

Observed initial four-case run1failed/3passed121.21s; failure was a wrong exact
test expectation (canonical rehashed manifest rejected before report). Corrected
to exact VERIFY_MANIFEST_MISMATCH; no check weakened. Raw Windows unsafe fixtures
and exact failure-code assertions strengthened. Affected two cases2passed50.65s.
After isolated DEFLATE-error mapping and DOS directory guard changes, malformed
case alone passed1.88s and1.65s. No full local suite or repeated four-case run.
All four acceptance cases now satisfied; no new skips. Final scoped Ruff and
diff checks successful; three long test lines wrapped before execution.

Actual fixture six kinds:12/24/27/27/51/131files; exact restored bytes and unchanged
sources. Independent standard-library ZIP inspection checks sorted names/date/
permissions/method and repeatable bytes. Deflated compatible package restores.
Fresh maps not shared; metadata wrapper preserved. Rehashed forged report rejected
despite valid ZIP CRC/inventory hashes. Verified-byte handoff test changes source
after verification: output still contains canonical verified bytes and later fresh
verification rejects changed source. Invalid source creates no ZIP. Existing
foreign outputs retained; symlink guard (real link if privileges permit, reported
link fallback otherwise), late write sanitized; moved real subprocess workflow
ZIP restores131files and rearchives byte-identically. Legacy init forbidden.

Actual retained131file workflow exported/restored exit0. Independent saved file
names/lengths/SHA256 all identical. ZIP6,210,409bytes/hash
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561;
package manifest7889bea763c849fcf194dd95c87b32802fe53b4e381af616e15398e15212d973.
Receipts tmp/m2-package-archive-export-result.json and
tmp/m2-package-archive-restore-result.json; ZIP tmp/m2-offline-workflow.zip;
restored navigation tmp/m2-offline-workflow-restored/index.md.

Primary full status/diff/refs/stash/database snapshot and427file path/hash map
unchanged. PrimaryHEAD3679b1b/stashcb568efd/localmain966206f preserved;
databaseSHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Protected inventory digest0BBAB36862ECEE2F980069CB40D059C19A916727316C9B5487502338839FF476.
Historical gaps/33facts/66missing parents remain; compatible installed baseline
required, no authenticity/signature/history/production eligibility claims.

Required42successfulhostedchecks, exact expected base/head/clean mergeability,
independent scope/contract/commit/diff/protection/sync review before authorized
merge. Stop on failures/conflicts/scope expansion. Engineering continuation
allowed; new data/real research not authorized, no automatic next stage.
