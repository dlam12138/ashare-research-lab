# M2 offline research bundle acceptance

Local verdict: PASS. Hosted PR/check/merge gate pending at this commit; actual
head/merge and required results must be independently included in final handoff.
Goal: agent/goals/2026-10-01_m2_offline_research_bundle.md.
Base origin/main/live main 73a462f8b6e118c9ab82c24934f2ef790a4f9ecf;
branch codex/m2-offline-research-bundle, originally clean owned worktree.

Six files: new tools/value_research_bundle.py and test_value_research_bundle.py,
README, Goal, record 2026-10-01_05_m2-offline-research-bundle.md, this acceptance.
Complete offline batch: readable/JSON assembly, export, byte-exact nine-source
attachments, manifest and source-independent package re-render verification.
Parent inspected source/loading/projection/rendering/export/verifier and real
report. Original decimals/status/IDs/heterogeneous dates retained; nested shadow
time contract explicit. Report sources are clickable; risk detail IDs remain in
JSON/attachments. No new metrics, scoring, recommendation, source acquisition,
DB or M4/holdout execution. Fixed historical evidence, not current research/PIT.

Exact parent commands in owned worktree:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest -q tests/test_value_research_bundle.py
python -m pytest -q tests/test_value_research_bundle.py --lf --tb=short
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/value_research_bundle.py tests/test_value_research_bundle.py
python -m ashare_research.tools.value_research_bundle --output tmp/m2-research-bundle
python -m ashare_research.tools.value_research_bundle --verify tmp/m2-research-bundle
git diff --check
git diff --cached --check
```

Initial 2 passed/2 failed: Markdown bold markup broke literal phrase assertion;
test word ban incorrectly rejected current_timestamp_recorded=false. Parent fixed
wording and checks actual false flag plus absence of timestamp/generated_at/
created_at fields. No required assertion removed. Failed cases rerun for diagnosis;
final four business cases PASS in 2.15s, no skips; scoped Ruff PASS. Last date-table
wording clarified unextracted dates; actual final export/verification re-executed.
No local full-suite run; mandatory hosted full regression remains required.
Four cases cover faithful projection/boundaries, actual export/portable verification/
determinism/source links, rehashed tampering and foreign-directory preservation.
An optional symlink probe records unavailable capability without skipping required
directory assertions; no historical tests, custom temp/ACL or gate edits.

Actual package tmp/m2-research-bundle: 12 files, 11 managed, 554196 managed bytes;
report.md 70839 bytes, report.json 211164 bytes. Verification status verified,
11/11, pinned sources enforced, rebuilt from retained attachments.
Manifest identity e368a55be2cf714890e3780ec1f7fee52bcbd4e82299b9ed0db4bfd77f5e7b43.
Markdown SHA256 d8e4d392b59b102235c197c8d99863371bd5cec1e99c893cd325f98b411c229c.
JSON SHA256 c452f97aaa301cd734784f35cf8fa6db2a53b80b8367426426a0512ad373afac.
Earlier owned renderings moved within verified workspace boundaries to
tmp/m2-research-bundle-pre-review and -pre-wording; no foreign artifact deleted.

DSH deviation: temporary unapproved helper writes and manual CLI/assertion
simulations, despite instruction; final helpers removed, no worker fallback.
Parent acceptance uses actual four-case pytest, not worker success claims.
Exact primary status/binary diff/HEAD/stash unchanged: HEAD
3679b1bac7a1634c6452784a4d8f6d139966f222, stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
Protected research.duckdb SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
All tracked reports/config/events/evidence/mechanism/fixtures SHA256 unchanged;
other worktrees/local main 966206f preserved. Owned branch published only through
scoped PR; expected head/base/42 successful checks and mergeability required.
Output late IO failure may leave owned partial package, which verification rejects.
Fixed-source bundle hashes prove integrity only; original 18 dated gaps, ROIC
non-computability and PE deferred decision persist. No next research stage allowed.
