<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Goal: land the reviewed financial analysis capability on canonical main

## Authorization basis

Tracked AGENTS.md (added 2026-09-28 by
02a451861da9b3c74fb9ecf9c250303b385e61f, an ancestor of origin/main 47dbb678
and of this branch) grants standing user authorization: "automatically merge
task-scoped PRs after independent review, successful required checks and
verification of the expected head and mergeability. Do not request per-PR
confirmation. This applies to engineering, evidence and governance PRs within
the user's authorized scope... It supersedes historical per-PR approval stop
points, but not their data, research or safety restrictions. Stop on failed
checks, conflicts or scope expansion; never bypass protections to merge."

The root worktree's untracked local AGENTS.md copy predates that rule; record
2026-09-28_01 explicitly states the root copy "will not automatically inherit
this tracked rule until safely reconciled". The tracked file is the
repository truth, so this goal supersedes the "awaiting explicit
authorization" wording of records 2026-10-10_13/_14 for the landing action
only; no data, research or safety restriction is loosened.

## Verified baseline

- Branch codex/financial-json-review at
  74cdaf756bf9744d1701521a427eafe30dc6506c (clean worktree
  D:/量化分析-worktrees/量化分析-financial-json-review), 0 behind / 6 ahead of
  origin/main; merge-tree write-tree equals the tip tree.
- Independent review PASS: record 2026-10-10_12. CI-parity preflight of all
  seven workflows (windows and portable legs): record 2026-10-10_14.
  Landing package (PR body, README anchors): record 2026-10-10_13.
- origin/main and live main 47dbb678; protection snapshot (68 trees, 404
  hashes, primary DB SHA256, stash cb568efd) intact.

## Allowed scope and required behavior

- README availability flip at the two exact anchors (one commit).
- This goal (one commit); plus one follow-up docs-only landing record PR
  after the capability merges, mirroring the 2026-09-28 precedent of
  recording completed merges.
- Push the branch; open one task-scoped PR to main with the prepared body
  (numbers refreshed); after every required hosted check succeeds and the PR
  head still equals the pushed tip, merge with --match-head-commit.
- Post-merge: verify live main advanced to the merge commit whose tree
  equals the branch tip tree; rerun the protection sweep; report everything
  distinguishing merged versus pending, with no false completion claims.

## Forbidden scope

Force push; direct push to main; branch deletion; history rewriting; new data
acquisition, real backtests or holdout use; scoring/ranking/advice; DSH;
primary database access beyond read-only hashing; edits in foreign
worktrees; scope expansion beyond this contract.

## Required checks and exact commands

```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_project_entry.py tests/test_research_entry.py tests/test_financial_analysis.py
git diff --check
git push -u origin codex/financial-json-review
gh pr create --repo dlam12138/ashare-research-lab --base main --head codex/financial-json-review --title "feat(m2): read-only multi-year company financial analysis (existing 12 metrics)" --body-file <prepared body>
gh pr checks <pr> --watch
gh pr view <pr> --json headRefOid,mergeable,mergeStateStatus
gh pr merge <pr> --merge --match-head-commit <tip sha>
git ls-remote origin refs/heads/main
```

## Acceptance criteria and stop conditions

- Hosted required checks all succeed for the exact pushed head; the PR head
  still equals the pushed tip at merge time.
- Merge completes; live main equals the returned merge commit; its tree
  equals the branch tip tree; protected state unchanged except origin/main
  advancing, which is the intended change.
- Stop on any failed check, conflict, unexpected head movement, protection
  drift or scope expansion; report without merging. Never bypass protections.

## Commit and push requirements

Two local docs commits before push (README flip; this goal); one push; one
PR; merge under the standing authorization without per-PR confirmation;
follow-up record in its own docs-only PR.
