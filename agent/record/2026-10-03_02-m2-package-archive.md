# Package archive execution record

Parent execution only; no DSH/subagents. Goal
agent/goals/2026-10-03_m2_package_archive.md, base
21dced22ae1ef2eb7724372499418986ce473012, branch codex/m2-package-archive.
Verified actual branch/HEAD/status/worktrees/remotes/stash/database and read
governance/current workflow/verifier. Saved primary and427file protection snapshots.
Record established before implementation. Bounded eight-file engineering stage;
Actual implementation: fresh public verified-byte package loader with compatible
metadata wrapper; deterministic ZIP builder and bounded verified restore CLI.
All six actual package kinds roundtrip with exact original bytes. Restored actual
workflow131files identical; ZIP6,210,409bytes/SHA256
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.
Initial four-case run1failed/3passed121.21s: test expected file mismatch, but
correct sorted canonical comparison rejected rehashed manifest first. Changed
the exact assertion to manifest mismatch, did not relax verification. Strengthened
unsafe Windows fixtures to retain raw backslashes/NUL and require exact error codes.
Affected two cases2passed50.65s; DEFLATE malformed-error mapping and DOS-directory
guard checked by only the affected case (1passed1.88s then1passed1.65s).
No local full suite or repeated four-case suite. Three E501 lines wrapped before
tests; final scoped Ruff/diff checks passed. Protected427file saved map and complete
primary status/diff/refs/stash/database snapshot unchanged. Exact commands and
acceptance evidence in acceptance/2026-10-03_m2_package_archive.md; hosted gates
and actual commit/PR/merge final evidence recorded after reviewed HEAD is fixed.
Independent final review additionally bounded member metadata (512namebytes /
32pathcomponents) before prefix checks, preventing excessive intermediate prefix
allocation. Added exact early-rejection fixture; unsafe case only rerun locally:1passed2.21s.
Earlier head a08161d Ubuntu full CI3004passed3skipped is intermediate evidence;
all hosted gates must succeed again on the final fix commit before merge.
