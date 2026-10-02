# Verified-byte reuse acceptance checkpoint

Goal agent/goals/2026-10-02_m2_verified_session_reuse.md; record
agent/record/2026-10-02_03-m2-verified-session-reuse.md. Verified base origin/live
main d2657d2deaeaa48b7789980a76bb4195e43687fd, task branch
codex/m2-verified-session-reuse. Own execution/no DSH or subagents.

Nine allowed files: README.md; Goal; record; this acceptance;
src/ashare_research/tools/research_session.py; research_review.py;
evidence_audit.py; session_compare.py in same directory;
tests/test_verified_session_reuse.py. Existing tests/engines/pins untouched.
Full verification returns its exact canonical bytes and metadata to the caller,
legacy verification returns identical metadata; consumers avoid second builds.
No cache, no reopening after verification, each call freshly verifies every file
and whole root manifest with original layout/error/pin checks.

Exact local commands in owned worktree, PYTHONPATH=src, python explicitly
D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_verified_session_reuse.py
python -m ruff check src/ashare_research/tools/research_session.py src/ashare_research/tools/research_review.py src/ashare_research/tools/evidence_audit.py src/ashare_research/tools/session_compare.py tests/test_verified_session_reuse.py
python -m ashare_research.cli research compare --left tmp/m2-research-session --right tmp/m2-research-session --right-view compare_with --output tmp/m2-session-compare-reused
git diff --check
```

Results:4passed33.95s/no skips; one targeted run, no reruns/full local suite;
Ruff and diff checks success. Actual CLI exportexit0/50managed51totalfiles.
Independently instrumented real build_session calls: loader1/legacy verifier1,
review1/audit1/compare2, formerly2/2/4 for consumers. This proves50%fewer builds,
not50%wall-clock speedup. Caller mutation does not affect later calls, disk
tampering after successful load detected on fresh calls, rehashed forged input
and foreign layout rejected, CLI failures leave stdout/output parent absent.

Retained pre-change JSON hashes inspected at actual base and pinned in regression:
- review7acdb34156d4d705dded2121316ad347cb9708a6ed1cee54fb9b2d2fc8a688c2
- audita75de99d9b159be5e628e6d125ce9eab8d5e83b73d4ad49512bfde0db14fc9ad
- compare07d2f801d782fd18abbf31193b7aa2c3364aab655e75e57439c70293e6ae136a
All identical after refactor. Actual51file old/new export byte equality verified
by this Python stdin script (no hash-only claim):
```python
from pathlib import Path
before = Path('tmp/m2-session-compare')
after = Path('tmp/m2-session-compare-reused')
old = {p.relative_to(before).as_posix(): p.read_bytes() for p in before.rglob('*') if p.is_file()}
new = {p.relative_to(after).as_posix(): p.read_bytes() for p in after.rglob('*') if p.is_file()}
assert len(old) == len(new) == 51
assert old == new
print('51 files byte-identical to the retained pre-change export')
```
Outer manifest hash unchanged97adfae6e950d98b40d04c2794f635ed3a8945f52faab5ca7e2858b6fa8de477.

Final review pending hosted outcomes: exact nine-file scope/base/head, clean task
tree/origin0/0, protected primary status/diff/untracked/stash/localmain/DB/hashmap,
42successful mandatory checks and clean mergeability before standing-authorized
merge. Final packet will record actual CI/job logs, PR/head/merge synchronization
and verdict. No new acquisition/research/backtests/holdout authorized. Original
33facts/66missing parents/historical availability limits unchanged; installed
compatible baseline still required, outer manifest inventory only.
