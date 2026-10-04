# M2 handoff guide — local acceptance checkpoint

Goal: agent/goals/2026-10-04_m2_handoff_guide.md. Base origin/live main
a4e87e0f65de86fdd173589d910fcfe4fac54a48; branch codex/m2-handoff-guide.
Root own execution, no DSH/subagents. Five documentation files only: README,
docs/m2_delivery_handoff.md, Goal, this checkpoint and dated agent record.

The guide connects existing sender generation, receiver verification, restoration,
index navigation and exact file comparison. It documents actual receipt fields,
safe new paths, failure handling, compatible baseline and historical limitations.
Explicitly states that diff exit0 may contain differences; inspect same_content.
No source, tests, CI, fixed inputs, calculation or research qualification changes.

Actual one-pass walkthrough, PYTHONPATH=src, Python executable
D:/量化分析/.venv/Scripts/python.exe in the owned worktree:
```powershell
python -m ashare_research.cli research deliver --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-handoff-walkthrough/delivery.zip --json
python -m ashare_research.cli research archive --verify tmp/m2-handoff-walkthrough/delivery.zip --json
python -m ashare_research.cli research archive --restore tmp/m2-handoff-walkthrough/delivery.zip --output tmp/m2-handoff-walkthrough/received --json
python -m ashare_research.cli research diff --left tmp/m2-handoff-walkthrough/received --right-archive tmp/m2-handoff-walkthrough/delivery.zip --json
git diff --check
git diff --exit-code a4e87e0 -- src tests reports config events evidence .github
```
All commands exit0. Archive statuses archived/verified/restored, each131files;
all three receipts' archive digests equal actual ZIP SHA256:
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.
ZIP6210409bytes; manifestSHA256
7889bea763c849fcf194dd95c87b32802fe53b4e381af616e15398e15212d973.
Diff status compared, same_content=true,131unchanged,0added/removed/changed.
Independently counted131restored files and checked every root index link exists.
Actual receipts: tmp/m2-handoff-walkthrough/{deliver,verify,restore,diff}-receipt.json;
readable start: tmp/m2-handoff-walkthrough/received/index.md. No repeat runs or
local pytest suite; documentation links/schema checked against real files/code.

Baseline primary HEAD3679b1b/localmain966206f/stashcb568efd, existing dirty and
untracked paths preserved. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 and427protected
path/hash lines unchanged at baseline; final independent review rechecks them.
No new research findings:33facts/66missingparents and provider historical gaps
remain. No implementation blockers or scope expansion.

This is the local precommit checkpoint, not a hosted-CI or merge claim. Normal
scoped commit/push/PR, required hosted gates and exact-base/head independent
review precede standing-authorized merge. Final refs/CI/protection/merge verdict
are retained separately in ignored tmp/m2-handoff-guide-final-review.md to avoid
changing the reviewed commit. Another stage requires user authorization.
