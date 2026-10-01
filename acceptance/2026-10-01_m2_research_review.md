# Verified research archive review acceptance

Local PASS; required hosted checks/merge pending at this commit.
Goal agent/goals/2026-10-01_m2_research_review.md; record
agent/record/2026-10-01_10-m2-research-review.md.
Verified base origin/live main3245e5c77efe832e82b6b8eebedcd903b38560f4;
task codex/m2-research-review. Seven allowed files: review module, entry,
new review tests, README, Goal, record, this acceptance.
Direct implementation per explicit user direction; no DSH or delegation.

Delivered annual tables for both dates, original comparison states and missing
roles/years, original decimal strings/units/status/engine/input IDs/date bounds.
Full source verifier runs first; view is rebuilt from canonical verified request
using existing public session API; retained mutable input cannot substitute new
values after verification. No new arithmetic, percentage conversion, scoring or
claims. Mixed-date value compilation and historical publication limits explicit.
Portable27file export includes unchanged24file nested session, review.md/json and
outer inventory manifest; all bytes rendered before exclusive final root mkdir.
Existing file/dir/link rejected, invalid source leaves parent absent; late IO may
leave owned partial output. Outer inventory is not a new authenticity verifier.

Exact commands in owned worktree with PYTHONPATH=src:
```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析/.venv/Scripts/python.exe' -m pytest -q tests/test_research_review.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m pytest -q tests/test_research_review.py::test_cli_existing_output_and_rehashed_input_tamper_fail_safely
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/research_review.py src/ashare_research/tools/research_entry.py tests/test_research_review.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ashare_research.cli research review --session tmp/m2-research-session --output tmp/m2-research-review
& 'D:/量化分析/.venv/Scripts/python.exe' -m ashare_research.cli research session --verify tmp/m2-research-review/session
git diff --check
```
Results:4passed22.42s; after empty-output fix only affected CLI case repeated,
1passed5.78s. Scoped lint initial UP012 fixed, final Ruff/diff pass. Actual export
and nested verificationexit0. No full local suite repeated. Mandatory hosted full
checks retained. Coverage original values/identity/revisions, insufficient history
and empty scope, exact portable evidence/hashes/moved nested verification, real
CLI/initialization guards, foreign-output safety, rehashed numeric input tamper,
invalid options and empty output handling. Existing tests unchanged.

Actual tmp/m2-research-review has27files,26managed. review.md5341bytes
SHA2564d78a52288dc669072d6f65366e9c5f5efac054e46b82fc4f11c71b88a2777d4;
review.json31460bytes SHA2567acdb34156d4d705dded2121316ad347cb9708a6ed1cee54fb9b2d2fc8a688c2;
manifest.json5341bytes SHA25605dedead89e95f8d1c4518d2791b2a3463505b8b9c88515fa7306966794a70d2.
Nested session24files verifies, byte-identical to original export; original7FY2023
value changes/16before and21after facts preserved. Remaining33facts/66absent raw
parents, retained availability not reproved, no historical metric version admission,
cash proxy and annual ROE conventions unchanged. No research/data stage expansion.

Protection: independently compare full primary dirty/untracked snapshot and source
reports/config/events/evidence/mechanism/fixtures hashes; primary3679b1b,
stashcb568efd/local main966206f and DB SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
remain preserved. Final review actual commit/scope/clean task tree/origin/live sync.
Commit/push seven task files only, then exact base/head and42required successful
checks/clean mergeability before standing-authorized PR merge. Final response
reports actual CI/head/merge/sync; pending hosted checks not preclaimed. No executor
deviation: user's no-DSH instruction overrides default routing. Further engineering
may continue with authorization; new research/data/holdout stages unauthorized.
