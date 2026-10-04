# Unified research help discovery — local checkpoint

Goal agent/goals/2026-10-04_m2_cli_help_discovery.md; base origin/live main
1b7e72930134e7991bba255a09cc592bef5e3957; branch codex/m2-cli-help-discovery.
Root own execution, no DSH/subagents. Four-file scope: Goal, this checkpoint,
agent/record/2026-10-04_02-m2-cli-help-discovery.md and research_entry.py.

Fixed actual missing deliver/diff child help examples. All child --help lines
now derive from COMMANDS; future registry entries are included automatically.
Added compact generate/verify/compare examples with explicit example dates,
placeholder paths/new-output requirement and the existing handoff guide path.
No command registration/dispatch/parser, calculations, fixed inputs or tests changed.

Exact validation in owned worktree with PYTHONPATH=src and executable
D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_research_entry.py::test_discovery_help_safe_dispatch_and_legacy_preservation
python -m ruff check src/ashare_research/tools/research_entry.py
python -m ashare_research.cli research --help
git diff --check
```
Existing targeted regression1passed12.71s; Ruff passed; actual help exited0,
saved tmp/m2-cli-help-discovery-help.txt; diff check passed. One manual in-memory
inspection guarded importlib.import_module with an exception during --help and
captured stdout: all13registered child help examples appear exactly once, all
three quickstart lines present, no child imports. No new tests or full local
suite; no repeats. Existing regression also covers actual subprocess help,
unknown-command failures and preservation of legacy initialization behavior.

Primary original branch/status/diff/HEAD/localmain/stash/database snapshot and
427protected hashes compared at baseline, unchanged. PrimaryHEAD3679b1b,
localmain966206f,stashcb568efd; databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 preserved.
Final independent review rechecks commit/scope/refs/protection after push/merge.

Local checkpoint only; hosted gates/merge not yet claimed here. Normal scoped
push/PR, all required hosted checks and exact base/head/CLEAN gate before standing-
authorized merge. Final actual evidence kept in ignored
tmp/m2-cli-help-discovery-final-review.md. No scope expansion/local blocker;
historical evidence limitations remain. Another stage requires user authorization.
