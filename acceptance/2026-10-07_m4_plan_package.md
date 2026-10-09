# M4 compile-only plan package acceptance evidence

Goal: agent/goals/2026-10-07_m4_plan_package.md. User continuation, root alone,
no DSH/agents. Base origin/live main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b;
isolated codex/m4-plan-package. Exactly eight scoped files, no existing tests,
mechanism/compiler/fixtures/CI/baselines changed.

Added --hypothesis JSON --output NEW_DIR [--json] and --verify DIR [--json].
Source loaded once, original strict1MiB parser and frozen compilers retained;
exact original hypothesis bytes, deterministic full JSON/Markdown and byte
inventory exported to four flat files. No host paths or timestamps embedded.
Verification reads bounded regular files only, rejects missing/extra/nested/
linked/reparse entries or ancestors, recompiles source under current compilers,
and compares all four files byte-for-byte. Rehashing tampered artifacts cannot
make them pass. All original execution/statistics/outcome/holdout/source-validation/
readiness boundaries false. Consistency verification does not prove authorship,
independent sealing, historical-source evidence or execution authority.

Compilation/rendering complete before exclusively creating destination; existing
paths rejected. Parent must exist. Files created exclusively, no overwrites or
deletes. I/O failure returns sanitized failure without success stdout; partial
owned output retained and rejected by verification. Publication is not atomic;
concurrent hostile filesystem changes are outside the security contract.

Exact local commands, PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_research_plan.py tests/test_research_plan_package.py
# 5 passed in 1.08s; no existing tests rewritten.
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_package.py
# All checks passed; one loop-closure lint finding fixed before test execution.
git diff --check
# PASS.
```
Cases cover public roundtrip, one-read mutation handoff, original identities and
bytes, deterministic relocation and regeneration, prohibited service/network/DB/
executor calls, four-artifact tampering with forged inventory hashes, missing/
extra/nested/oversized/reparse root/file/ancestor entries, invalid combinations,
existing file/directory preservation, malformed source before mkdir, absent parent,
and injected write failure preserving partial output without success receipt.
Windows reparse rejection exercised via portable injected lstat attributes.
Independent code review found relative paths must expand to absolute paths before
ancestor inspection; corrected and added relative verify/export coverage. The
affected new test file rerun: python -m pytest -q tests/test_research_plan_package.py,
3 passed; Ruff/diff rechecked. No full local suite or unrelated repeat.

Actual public CLI subprocess demo, exit0/no stderr:
```powershell
python -m ashare_research.cli research plan --hypothesis docs/examples/m4_hypothesis.json --output tmp/plan-package-demo --json
# Directory renamed to tmp/plan-package-relocated.
python -m ashare_research.cli research plan --verify tmp/plan-package-relocated --json
```
Four expected files, false boundaries, original source bytes retained.
Source SHA256974b8cc55309e2219dc12dec6bdff45e346e2092f88435581f7533bbfe6cdb47;
contract56e914cf9afef8af935c2553e242dc2c0c888d537c5494dabb05eb094a1c4610;
plan c73268f7b63a24f300aec8e5fd3f20adbe3fc1031b85acebe3835148964c3267.
Receipts tmp/plan-package-{export,verification}-receipt.json.

Pre-implementation snapshot tmp/m4-plan-package-baseline.json records primary
dirty/untracked state/diff/HEAD/local-main/stash, database SHA256 and408protected
file hashes, and worktree registrations. Final independent committed scope/diff/
refs/sync/protection/Goal review and hosted checks recorded in
tmp/m4-plan-package-final-review.md. Local evidence PASS; final acceptance depends
on those checks. No merge authorized by supplied user governance; no next stage.
