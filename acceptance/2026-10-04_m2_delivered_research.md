# Direct delivered research — local acceptance

Goal agent/goals/2026-10-04_m2_delivered_research.md. Verified base origin/live
main ffb6a9d97b316af45ba2e4ac57eb46cc07b82de9; branch codex/m2-delivered-research.
User selected direct viewing/comparing delivery metrics/evidence. Root execution,
no DSH/subagents. Eight files: Goal, this checkpoint, dated record, README,
delivered_research.py, session_compare.py, research_entry.py and new test file.

research read selects review/audit/compare from a fully verified workflow or
matching section package, directory or ZIP. JSON envelope preserves whole original
report and complete verification/optional archive receipt; text reuses original
renderers. Fixed member names only; missing sections/wrong kinds fail explicitly.
research compare accepts session/workflow ZIP per side alongside existing session
directories. Full outer verification precedes extracting canonical session bytes;
existing financial comparison engine/record shape/export format unchanged. No
source reread after verified handoff. No caller restoration or arbitrary paths.
No new arithmetic, data acquisition, research or qualification claims.

Validation in owned worktree, PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_delivered_research.py tests/test_session_compare.py
python -m ruff check src/ashare_research/tools/delivered_research.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_delivered_research.py
git diff --check
git diff --exit-code ffb6a9d -- tests/test_session_compare.py reports config events evidence .github src/ashare_research/mechanism
```
Six tests passed263.07s, first and only targeted run: two new cases plus all four
existing financial comparison cases. Initial Ruff found one import-order issue
in the new test; formatting corrected before tests, final scoped Ruff PASS.
No test failures, repeats, weakened tests or local full suite.

Actual fixed workflow/session packages verify report JSON equivalence, original
rendered Markdown, three sections, matching standalone packages and unchanged
source bytes. ZIP/ZIP API and directory/ZIP CLI comparison exactly equal original
directory report with seven value changes, including all nested source records.
ZIP comparison export independently verifies as a canonical compare package.
Bad argument combinations, arbitrary section paths, wrong package kinds and
missing compare section fail. Forged outer Markdown plus recomputed manifest
hash/size and valid ZIP CRC rejected by both read and compare, even when nested
session metrics remain untouched. No success stdout/source mutation. A source
changed after verification is not reread; a later fresh read rejects corruption.

Actual retained delivery demo (all exit0, each command once):
```powershell
python -m ashare_research.cli research read --archive tmp/m2-handoff-walkthrough/delivery.zip --section review
python -m ashare_research.cli research read --archive tmp/m2-handoff-walkthrough/delivery.zip --section audit --json
python -m ashare_research.cli research compare --left-archive tmp/m2-handoff-walkthrough/delivery.zip --right-archive tmp/m2-handoff-walkthrough/delivery.zip --right-view compare_with --json
```
Saved tmp/m2-delivered-research-demo/review.md, audit.json, compare.json.
Comparison7keys/7value_changed, all other states0. Audit18datedfactrows,14unique
facts,28unresolvedparents,0missinginputroles; all18datedrows retain evidence gaps.
Original ZIP SHA256 unchanged
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.

Primary original snapshot/protected427hashes verified before implementation,
HEAD3679b1b/localmain966206f/stashcb568efd; DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 preserved.
Independent final review rechecks actual commit/diff/Goal/refs/protection.
Local checkpoint only; hosted CI and merge results retained separately in
tmp/m2-delivered-research-final-review.md without changing reviewed HEAD.
Normal scoped push/PR, all hosted gates and exact base/head/CLEAN review before
standing-authorized merge. No scope deviation/local blocker. Compatible installed
baseline required; historical/publication/source gaps unchanged. No automatic
next stage or real-data/research/backtest/holdout/production admission.
