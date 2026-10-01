# Unified research entry acceptance

Local verdict: PASS; hosted checks/merge pending at this commit.
Goal: agent/goals/2026-10-01_m2_unified_research_entry.md.
Base: origin/live main676222d8ddebf6b2bc0e4065afc9849904955e6b.
Task: codex/m2-unified-research-entry. Seven allowed files: cli.py,
tools/research_entry.py, tests/test_research_entry.py, README, Goal, record,
this acceptance. One bounded DSH implementation exited0, no observed scope
deviation, recursive delegation, helper/test execution or alternate model.
Parent owns independent review, the single targeted run and Git delivery.

Observable behavior: installed ashare-research research report/facts/metrics/demo
delegates intact options to existing tool main functions. Root and research help
discover workflows; exact subtool help retained. Offline dispatch precedes legacy
config/logging/service initialization. Global config/debug combinations rejected,
including legacy config abbreviation, with no configuration value echoed.
Legacy init-db and build-value-facts service_factory flow exercised unchanged.
Original module entries remain available. No provider/database parameter added.

Exact local commands, executed in owned worktree with PYTHONPATH=src:
```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析/.venv/Scripts/python.exe' -m pytest -q tests/test_research_entry.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/cli.py src/ashare_research/tools/research_entry.py tests/test_research_entry.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ashare_research.cli research metrics --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-unified-research-entry
git diff --check
```
Results: four tests passed41.15s, no skips; Ruff and diff check pass; CLIexit0,
exported2 managed files221491 bytes. Discovery/help, real report/demo bytes,
forbidden initialization guards, dated facts/metrics equivalent to direct main,
future-restatement exclusion, empty history, real child export and foreign-path
preservation, error codes and global-option rejection covered in four cases.
No full local regression repeated; all required hosted checks remain mandatory.

Actual artifact tmp/m2-unified-research-entry:
- report.md21070 bytes SHA256d639a892a56794432c8f880acdd3cfb80af77b95f953a6dae5662fbd9bd3d4e6
- report.json200421 bytes SHA2569fe7b9918e7e0941765c7f44c6b1ffcaa102ab4289f60d9529659ecf3e0c8dd0
- manifest.json6271 bytes SHA2566a0f3497259e584f5d8155e0c7dccb84538fbdfa0d4761e705d4203c51de3fd2
Byte identities equal original direct replay artifacts, seven computed FY2023
metrics at both dates and seven value changes. Original source limitations remain:
mixed-date report compilation; facts/metrics only33 committed facts/66 missing
parents; retained availability not independently reproved; no stored metric
version admission or publication proof; synthetic demo is invented24rows.

Protected review: primary HEAD/branch/full dirty snapshot and untracked entries,
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, local main966206f and DB hash
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged;
full reports/config/events/evidence/mechanism/fixtures hash map matches baseline.
No primary/foreign worktree cleanup, new source acquisition or research run.

Delivery: commit/push these seven files only on task branch. Independently check
actual diff/HEAD, clean worktree/stash/protected hashes, exact live base/head,
required successful hosted checks and mergeability before authorized PR merge.
Final response records actual head/merge/CI/sync; local acceptance is not a claim
that pending hosted checks already passed. Further scoped engineering is allowed
under user continuation; new data/research/holdout stage remains unauthorized.
