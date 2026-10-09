# Paired synthetic preparation comparison acceptance

Goal: agent/goals/2026-10-07_m4_preparation_comparison.md.
Verified dependency origin/live codex/m4-preparation-diagnostics:
748b782438ce25fbaab086eb2ddc48eb44a99958. PR73 OPEN/MERGEABLE;
latest observed39SUCCESS/2pending checks, not a successful complete hosted gate.
main remains8d0fb4d. Root directly implemented; no DSH/delegation.

Delivered research prepare-compare (--package DIR | --archive ZIP)
--left-inputs JSON --right-inputs JSON [--json].
Both distinct inputs use unchanged complete plan verification and original
preparation/projector; each plan is independently verified before its input.
Same literal caller path reuses one original loaded snapshot. Other aliases
traverse the original link/reparse checks, including aliases resolving to the
same file. Plan identity, declared-domain digest, role order and audit dates must
match; denominator changes cannot masquerade as repairs.

Original before/after quality, source/input/contract/plan/dataset/matrix digests,
dates/roles/validity/reasons/PIT availability/record IDs/evidence references and
truthful per-side read/execution boundaries preserved. Audit counters distinguish
unchanged, became valid, became invalid and changed diagnostic metadata; they
are not statistical estimates or assertions about source authenticity.
Byte equality is separate from adapter canonical input-digest equality.
Observation value changes may appear as evidence/metadata changes, not gap
repair; no raw observation/matrix values or statistical effects emitted.
Errors are sanitized, code2, empty stdout. No input writes or digest repairs.

Actual exact commands: PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe.

```powershell
python -m pytest -q tests/test_preparation_compare.py tests/test_preparation_diagnostics.py
python -m pytest -q tests/test_preparation_compare.py
python -m ruff check src/ashare_research/tools/preparation_compare.py src/ashare_research/tools/research_entry.py tests/test_preparation_compare.py
git diff --check
python tmp/preparation-comparison/demo.py
python tmp/preparation-comparison/verify_protections.py
```

Initial targeted result6passed5.21s; Ruff/diff passed. Independent review found
resolved-path equality could skip the right-side link gate. Changed reuse to
literal Path equality, added alias regression and reran affected comparison
tests:3passed3.54s; Ruff/diff passed. No failed/full local test run or existing
test edits. Existing preparation/diagnostic/verifier modules byte-equal to base.

Meaningful cases: exact original summaries and denominator4; null/PIT defects to
valid and reversed transitions; metadata-only value/evidence change; canonical
format/observation-order equivalence; empty input/false read boundaries; once-read
input snapshots despite subsequent mutation; same-path read reuse; valid domain
shrink rejection; two individually valid plans replaced between reads reject;
stale evidence, duplicate JSON, corrupt plan and invalid flags fail closed;
service/network/database/pipeline/statistical-execution guards and immutable files.

Actual subprocess directory/ZIP outputs identical. Invented gap comparison:
before3/4, after4/4,16compared cells/15unchanged/1became valid. Eight source file
hashes unchanged. Actual Windows junction alias rejected LINKED_INPUT_PATH,
code2/empty stdout. Retained JSON/Markdown/demo evidence under
tmp/preparation-comparison/demo/.

Final protection check:39foreign worktree registrations/branches/HEAD/status,
27dirty-file hashes (including both paths missed by the prior task snapshot),
427protected file hashes, stash/localmain/database unchanged. No comprehensive
ignored-runtime hash claim. Primary original changes preserved.

Local acceptance PASS. Seven tracked files; owned commit/live synchronization,
PR identifier and exact-head hosted checks independently queried after publication
and recorded in final packet. Pending checks remain pending, not reported success.
Stacked PR against codex/m4-preparation-diagnostics depends73->71->70->69->68.
No automatic merge or following stage; real research/holdout/statistics remain sealed.
