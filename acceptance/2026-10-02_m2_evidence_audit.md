# Verified evidence audit acceptance

Local PASS; required hosted CI/merge pending at this commit.
Goal agent/goals/2026-10-02_m2_evidence_audit.md; record
agent/record/2026-10-02_01-m2-evidence-audit.md.
Verified origin/live base2647ed3ef16ae26e613638546f61e2c9d1ab95cd;
task codex/m2-evidence-audit. Seven allowed files: audit module, research_entry,
new audit tests, README, Goal, record, this acceptance. Direct implementation per
user instruction; no DSH, delegation or executor deviation.

Delivered complete verified input dependency ledger: date+fact ID grouping, exact
original fact decimals/source/context/lineage/parents, every impacted metric/year/
role/result ID/status, original missing-role year/context/reason. Same-query repeated
references deduplicated, different dates retained separately. Descriptive original
source omissions/unresolved parents only; not new financial/research eligibility
judgments. Counts distinguish dated rows, unique used facts and used parent IDs.
Canonical full session verified before projection, rebuilt through public API.
27file export retains unchanged24file session and relative evidence links; outer
manifest is an integrity inventory, not signature/authenticity verifier. All bytes
rendered before exclusive root mkdir, existing file/dir/link refused, corrupt input
creates no final parent/root, late IO may retain owned partial output. No clock,
machine paths, new sources/formulas/scores/data acquisition or research run.

Exact commands in owned worktree, PYTHONPATH=src:
```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析/.venv/Scripts/python.exe' -m pytest -q tests/test_evidence_audit.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/evidence_audit.py src/ashare_research/tools/research_entry.py tests/test_evidence_audit.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ashare_research.cli research audit --session tmp/m2-research-session --output tmp/m2-evidence-audit
& 'D:/量化分析/.venv/Scripts/python.exe' -m ashare_research.cli research session --verify tmp/m2-evidence-audit/session
git diff --check
```
Results:4passed25.81s, no skips; initial three E501 strings split before tests,
final Ruff/diff pass. Actual export and nested verificationexit0. No full local
suite repeated. Tests real exact traces/values/all dependencies/dedup, missing
history/empty scope/same-date references, portable evidence/hash/moved nested
verification, real CLI/legacy guards/tamper/invalid args/foreign and empty paths.
Old tests unchanged; mandatory hosted complete checks retained.

Actual tmp/m2-evidence-audit:27files/26managed. audit.json83813bytes
SHA256a75de99d9b159be5e628e6d125ce9eab8d5e83b73d4ad49512bfde0db14fc9ad;
audit.md5796bytes SHA25675c4586d06d9c0079cb691761a690af12c908e164b4a5b41da1356b676794c14;
manifest.json5338bytes SHA256b20f9266004588f3abfa2d1ceacc6838c5d1a7b78e416e558af8bef397bfc21e.
Nested24files byte-identical to original session and verifierstatus verified.
Selected FY2023 before/after:18dated facts,14unique fact IDs,28unique unresolved
parent IDs,18dated facts with gaps,0missing roles. These are used-input counts,
not full snapshot coverage. Entire frozen snapshot remains33facts/66absent raw
parents; historical availability/publication not reproved and no metric admission.
Missing proof fields do not mean sources do not exist or fact values are wrong.

Independently compare primary dirty/untracked snapshot and captured protected
reports/config/events/evidence/mechanism/fixture map; preserve primary3679b1b,
stashcb568efd/local main966206f, DB SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
foreign worktrees/runtime and prior artifacts. Final actual commit/scope/Goal/
clean task worktree/local-origin/live remote sync review. Commit/push seven task
files only; exact base/head,42required successful checks and clean mergeability
before standing-authorized PR merge; never main push. Final response records actual
CI/head/merge/sync; pending hosted results not preclaimed. Further authorized
engineering may continue; new data/research/holdout stage remains unauthorized.
