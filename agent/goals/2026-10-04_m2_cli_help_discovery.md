# Complete offline CLI help discovery

Objective: fix missing deliver/diff help examples in the unified research entry;
derive all child help examples from the existing command registry and show a
compact generate/verify/compare path. User continuation authorizes this bounded
engineering fix; root executes without DSH/subagents.

Verified base: origin/live main1b7e72930134e7991bba255a09cc592bef5e3957.
Owned branch codex/m2-cli-help-discovery in the capsule-postmerge-acceptance worktree.
Primary HEAD3679b1b/localmain966206f/stashcb568efd and full original primary snapshot
unchanged;427protected hashes freshly compared. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged.

Allowed four files: this Goal; src/ashare_research/tools/research_entry.py;
acceptance/2026-10-04_m2_cli_help_discovery.md;
agent/record/2026-10-04_02-m2-cli-help-discovery.md. Owned ignored evidence allowed.
Forbidden: command registry/dispatch/parser behavior changes, new features,
existing tests, baselines/data/calculations/CI, real research/backtests/holdout,
outbound messages, foreign worktrees/user changes/stash/database, main/force pushes
and destructive cleanup.

Required: all registered commands have exactly one child --help example; future
registry entries automatically appear. Keep help lazy, UTF-8, no config/logging/
service initialization. Show executable quickstart examples for deliver, ZIP
verification and two-ZIP diff with clearly identified placeholder paths/dates.
Preserve every existing command, help invocation and exit status.

Validation: low-impact help-only change, no new tests. With PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe in owned worktree:
python -m pytest -q tests/test_research_entry.py::test_discovery_help_safe_dispatch_and_legacy_preservation
python -m ruff check src/ashare_research/tools/research_entry.py
python -m ashare_research.cli research --help
git diff --check
Inspect actual help for all13registered child examples exactly once; instrument
research_entry.importlib.import_module to reject imports while rendering help.
No full local suite or test repetition unless a failure requires correction.

Acceptance: scoped existing regression passes; actual UTF-8 help includes new
quickstart and all13commands; lazy help guard passes; four-file scope only;
protected427hashes/primary/stash/database unchanged. Independent review of actual
commit/diff/Goal/acceptance/test evidence, clean owned worktree and local/origin/live
refs. Commit scoped branch, normal push/PR. Required hosted gates before standing-
authorized merge; stop on failure/conflict/drift/scope expansion, never bypass.
Final PASS/CHANGES_REQUIRED/BLOCKED with actual refs and evidence. Another stage
requires user authorization; no automatic next stage.
