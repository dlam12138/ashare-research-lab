<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial mainline landing acceptance

Verdict: PASS

- Contract: agent/goals/2026-10-10_financial_mainline_landing.md. This
  docs-only record doubles as its acceptance evidence and is merged in its
  own follow-up PR per the contract's allowed scope.
- Base: origin/main 47dbb6780933f8fb7abab922aa47027a1342de41. Delivery
  branch codex/financial-json-review was pushed at tip
  72bd22399d315cb9eb5285266e071f970de0a39a (8 ahead, 0 behind; clean
  worktree D:/量化分析-worktrees/量化分析-financial-json-review).
- PR #93 (dlam12138/ashare-research-lab, "feat(m2): read-only multi-year
  company financial analysis (existing 12 metrics)"): base main, head
  72bd223. Pre-merge verification: headRefOid 72bd223, mergeable
  MERGEABLE, mergeStateStatus CLEAN, state OPEN; all 42 extracted PR
  check-runs pass (7 workflows x push/pull_request events; watcher closed
  at "20:21:32 total=42 pass=42", zero failures).
- Merge performed under the standing authorization quoted in the contract:
  `gh pr merge 93 --merge --match-head-commit 72bd223...` exit 0. PR state
  MERGED, mergedAt 2026-10-10T12:21:56Z UTC, merge commit
  ff51ceba1f6e0ee7d0093a161dcb9f62dd3a47bf (parents 47dbb678 + 72bd223).
- Post-merge synchronization: local and live origin/main both
  ff51ceba1f6e0ee7d0093a161dcb9f62dd3a47bf; the merge commit tree equals
  the branch tip tree (3b970e0c055ead7f149db0bcf4bf23ba1f3cf685).
- Landed content in PR #93 (23 files, +4374): README.md availability flip;
  src/ashare_research/financial_analysis.py (new, 1202 lines),
  src/ashare_research/tools/financial_analysis.py (new, 100),
  src/ashare_research/tools/research_entry.py (modified, 12);
  tests/test_financial_analysis.py (new, 1191);
  docs/core_financial_analysis_guide_v1.md; 2 acceptance files; 7 goals
  and 8 records for the financial analysis line.
- Protection sweep after merge (start-snapshot comparison script): 404
  file hashes, 0 mismatched; primary DB SHA256
  4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6
  unchanged (read-only hashing only, no connection); stash cb568efd
  retained (count 1); 68 worktrees compared with exactly 2 flagged diffs,
  both expected: (a) the delivery branch head advanced by its two planned
  docs commits (8fafbbe README flip, 72bd223 goal), (b) the root worktree
  status list is identical as a set (17 pre-existing entries, HEAD
  3679b1b unchanged) with one Chinese filename rendered octal-escaped in
  that sweep's raw git output. No unexpected drift.
- Validation commands and results: local pre-push pytest of the
  project/research/financial entry files 64 passed; CI-parity preflight
  record 2026-10-10_14 (all seven workflows' windows and portable legs:
  239 passed + capsule chain + envelope compares MATCH); hosted PR #93
  checks 42/42 pass at the pushed head; post-merge
  `git ls-remote origin refs/heads/main` and tree comparison as above;
  this record's own PR checks must pass before it merges.
- Residual risk (unchanged by this landing, recorded in 2026-10-10_14):
  ubuntu matrix legs cannot run locally (hosted-only; all passed hosted);
  local Python 3.13.9 vs CI Python 3.11 for the full suite.
- Deviations: none. No failed check, conflict, unexpected head movement
  or protection drift occurred. No force push, no direct push to main,
  no branch deletion, no history rewrite, no data acquisition, no DSH,
  no primary database access beyond read-only hashing.
- This landing does not start the next project stage; any next stage
  beyond the landed capability requires its own contract and
  authorization.
