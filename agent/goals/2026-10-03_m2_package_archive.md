# Portable verified research package archive

Objective: deterministic ZIP delivery and verified restoration of all six existing
package kinds, including the complete workflow. User continuation authorizes this
engineering stage; parent executes, no DSH/subagents. Verified base origin/live
main21dced22ae1ef2eb7724372499418986ce473012; clean owned worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance; branch
codex/m2-package-archive. Primary HEAD3679b1b, dirty/untracked snapshot,
stashcb568efd, localmain966206f and database hash
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
protected. Save427file path/hash map reports/config/events/evidence/mechanism/fixtures.

Allowed eight files: this Goal; agent/record/2026-10-03_02-m2-package-archive.md;
acceptance/2026-10-03_m2_package_archive.md; README.md;
src/ashare_research/tools/package_archive.py;
src/ashare_research/tools/package_verification.py;
src/ashare_research/tools/research_entry.py; tests/test_package_archive.py.
Forbidden: modifying earlier builders/engines/tests/fixed sources, new data or
communications/formulas/scoring/research admission, database/cache/holdout/real
backtests, destructive cleanup or main push. Preserve foreign worktrees/artifacts.

Required: research archive --package DIR --output NEW_ZIP [--json];
research archive --restore ZIP --output NEW_DIR [--json]. Expose public fresh
load_verified_package returning existing metadata and exact verified canonical
bytes; verify_package wrapper retains its metadata and error behavior. No cache,
private-builder use or second retained-file read after verification. Deterministic
sorted ZIP_STORED members/fixed1980date/regular0644permissions, no machine paths,
current clock or extra archive files. Before output creation, fully verify source
or safely decode archive into owned TemporaryDirectory and fully verify every byte.
Restore only verified canonical bytes, never ZipFile.extract/extractall.

Reject preexisting outputs and symlink ancestry before build and before exclusive
creation, and archive output nested in source package. Reject ZIP traversal,
absolute/drive/backslash/empty/dot/Windows-device/trailing-dot-or-space names,
case collisions, duplicates, links/nonregular/directory members, encrypted or
unsupported methods, malformed/truncated/CRC failures and size/count overlimits.
Bounds:256members/32MiB per member/128MiB uncompressed total/129MiB archive.
Member metadata is also bounded before prefix inspection:512namebytes and32path
components, fitting all six current fixed package kinds. Add an exact early-rejection
case; rerun only unsafe archive acceptance locally after this review correction.
CRC passes or rehashed inventories alone never suffice: actual complete package
verification required. No writes to caller destination on invalid archive,
tampering or source failure. Late writes preserve owned partial outputs with
sanitized errors2/no success stdout; no atomic publication claim or cleanup.
Results JSON/readable receipt include package kind/count/digest and archive SHA,
reproducibility limits; no signatures/authenticity/history/admission claims.

Exact commands: PYTHONPATH=src; primary .venv/Scripts/python.exe:
python -m pytest -q tests/test_package_archive.py
python -m ruff check src/ashare_research/tools/package_archive.py src/ashare_research/tools/package_verification.py src/ashare_research/tools/research_entry.py tests/test_package_archive.py
python -m ashare_research.cli research archive --package tmp/m2-offline-workflow --output tmp/m2-offline-workflow.zip --json
python -m ashare_research.cli research archive --restore tmp/m2-offline-workflow.zip --output tmp/m2-offline-workflow-restored --json
git diff --check
Four cases: real roundtrip/all six kinds and deterministic bytes/fresh loader;
unsafe archive layout/bounds/CRC; rehashed tampering/prebuild failures/no foreign
writes; actual portable CLI/output guards/sanitized failures/no legacy init.
One targeted run, repeat only for fixes; no full local suite. Acceptance: exact
restored nested bytes131file workflow, six kinds covered, no protected changes,
four meaningful cases/scoped lint/diff successful. Required hosted42checks,
expected head/base/clean mergeability and independent review before authorized
merge. Commit/push only eight files; final evidence covers Goal/scope/actual Git/
CI/protection/sync. Stop on failures/conflicts/baseline changes/scope expansion;
never bypass gates. Final PASS/CHANGES_REQUIRED/BLOCKED. Engineering may continue;
new data/real research unauthorized, no automatic next stage.
