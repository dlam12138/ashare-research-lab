# M2 delivery handoff walkthrough

Objective: make the existing M2 offline delivery usable as one documented sender /
recipient workflow, with an actual retained end-to-end example. User continuation
2026-10-04 authorizes this documentation/acceptance stage; root executes directly,
no DSH or subagents.

Verified baseline: live/origin main a4e87e0f65de86fdd173589d910fcfe4fac54a48,
owned worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance,
new branch codex/m2-handoff-guide. Primary HEAD3679b1b, local main966206f,
stashcb568efd unchanged. Original primary snapshot and all427 protected path/hash
lines freshly compared against retained physical baselines; database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged.

Allowed tracked scope: this Goal; README.md; docs/m2_delivery_handoff.md;
acceptance/2026-10-04_m2_handoff_guide.md;
agent/record/2026-10-04_01-m2-handoff-guide.md. Owned new tmp artifacts allowed.
Forbidden: source/test/CI/config/report/data changes, new research or acquisition,
outbound messages, real backtests, holdout, original artifacts/user paths, database
writes, force/main pushes, destructive cleanup or additional product features.

Required behavior: executable PowerShell examples using existing research CLI;
sender ZIP generation; recipient full verification before restoration; root index
navigation; restored directory versus original ZIP comparison; explain content
comparison versus financial compare, return codes and safe retry/new paths.
State compatible installed baseline requirement and fixed historical evidence
limitations. No claims of signature/authenticity or research qualification.

Validation: documentation-only, no new tests or local pytest suite. Read actual
parsers/receipt schemas, run exactly one end-to-end chain with PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe in the owned worktree:
python -m ashare_research.cli research deliver --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-handoff-walkthrough/delivery.zip --json
python -m ashare_research.cli research archive --verify tmp/m2-handoff-walkthrough/delivery.zip --json
python -m ashare_research.cli research archive --restore tmp/m2-handoff-walkthrough/delivery.zip --output tmp/m2-handoff-walkthrough/received --json
python -m ashare_research.cli research diff --left tmp/m2-handoff-walkthrough/received --right-archive tmp/m2-handoff-walkthrough/delivery.zip --json
git diff --check
git diff --exit-code a4e87e0 -- src tests reports config events evidence .github
Check new guide's relative links against actual files; independently inspect
retained index, receipts, return codes, ZIP/source hashes and protected baselines.

Acceptance: all four commands exit0; all three archive receipts agree on digest /
131 files; restored index links resolve; diff reports131unchanged and0 changes;
guide examples/schema/path semantics match actual evidence; five-file docs-only
diff; primary/stash/database/427protected hashes unchanged; no repeated tests.

Commit/push: scoped branch only, normal push and PR. Independent final review of
actual commit/diff/contract/acceptance/worktree/stash/live refs. Existing required
hosted gates must succeed before standing-authorized merge under tracked AGENTS;
no weakening/cancelling gates. Stop on failure, baseline drift, conflict or scope
expansion. Record final actual merge/refs/evidence if merged. Verdict one of PASS,
CHANGES_REQUIRED, BLOCKED. Another stage requires user authorization.
