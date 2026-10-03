# Direct verification of delivered research ZIPs

Objective: recipients can fully verify an existing research ZIP without creating
a caller destination. Latest user continuation authorizes this engineering stage;
root executes directly, no DSH/subagents. Verified base origin/live main
f291ea6ed06770d8b778d3734a569775a60aaeae; clean owned worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance; branch
codex/m2-archive-verification. Primary HEAD3679b1b, local main966206f,
stashcb568efd, existing dirty/untracked files and database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 preserved.
Physical primary snapshot and427protected path/hash lines saved in ignored tmp.

Allowed seven files: this Goal;
agent/record/2026-10-03_03-m2-archive-verification.md;
acceptance/2026-10-03_m2_archive_verification.md; README.md;
src/ashare_research/tools/package_archive.py;
src/ashare_research/tools/research_entry.py;
tests/test_archive_verification.py. Forbidden: changing existing tests, verifier,
builders, research engines, fixed inputs, formulas/scoring/admission, data
acquisition/communications, database/cache/holdout/real backtests, unrelated
worktrees/artifacts, force/main push or destructive cleanup.

Required behavior: research archive --verify ZIP [--json], mutually exclusive
with --package/--restore. --output forbidden for verification and required for
existing export/restore. Fully bounded snapshot read and existing safe decoder /
canonical whole-package verification shared with restore, without creating a
caller destination. Owned temporary decoding remains necessary and cleaned up
normally. Return existing archive receipt schema with status verified, exact ZIP
SHA256/byte count, package kind/count/manifest digest and full original verifier
metadata/limitations; no absolute source path or timestamp. No source mutation,
network/legacy-config/log/default-database initialization, retained-file cache,
new signatures,
CRC-only acceptance or historical authenticity claims. Existing export/restore
receipt, limits, guards, error behavior and byte format remain compatible.
Reject invalid mode/output combinations with error2/no success stdout before
source reading. Source/layout/limits/CRC/content failures share restore codes.

Required meaningful tests: all six kinds with actual canonical packages and
receipt compatibility; real process workflow verification with no destination;
invalid arguments before source read, corrupt/unsafe/rehashed content rejection,
bounded single source read, source errors and no foreign changes. Run one new
targeted suite plus existing unsafe archive case; rerun only actual fixes. No
local full suite or repeated CI matrix. Exact commands, PYTHONPATH=src using
D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_archive_verification.py tests/test_package_archive.py::test_unsafe_members_limits_malformed_and_crc_fail_before_destination
python -m ruff check src/ashare_research/tools/package_archive.py src/ashare_research/tools/research_entry.py tests/test_archive_verification.py
python -m ashare_research.cli research archive --verify tmp/m2-offline-workflow.zip --json
git diff --check
git diff --exit-code f291ea6ed06770d8b778d3734a569775a60aaeae -- reports config events evidence src/ashare_research/mechanism tests/fixtures

Acceptance: all six real kinds verified; retained131-file ZIP verifies with exact
prior ZIP/manifest digest, source hash unchanged, no new destination; parser and
malformed/content rejection evidenced; targeted checks pass; seven-file scope,
primary/database/stash/protected hashes unchanged. Commit and normal push only
task branch, create scoped PR. All42required hosted checks successful across
seven workflows, exact base/head/CLEAN mergeability and independent evidence
review before standing-authorized merge. Final evidence records actual commands,
results, scope, branch/commits, merge and remote sync, protection and limitations.
Stop on failure/conflict/baseline change/scope expansion; no bypass. Final verdict
PASS/CHANGES_REQUIRED/BLOCKED. No automatically starting another stage; real data,
research or production use remain outside this authorization.
