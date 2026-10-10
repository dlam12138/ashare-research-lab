<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Record: mainline landing preparation for the financial analysis delivery

## Task contract (this record doubles as contract and acceptance)

Objective: prepare - without executing - the mainline landing (push, PR,
merge) of codex/financial-json-review into canonical main: correct the
integration-target topology, pre-verify every executable step, and freeze the
PR package so that an explicit authorization reduces to a small bounded
command sequence.

Verified baseline at this task's start (2026-10-10):
- Delivery worktree D:/量化分析-worktrees/量化分析-financial-json-review clean
  at 636241294b01724c7f0a37493df4b2d0aad67e0f (codex/financial-json-review),
  4 commits above origin/main.
- Root D:/量化分析 unchanged: feat/m2-value-assessment-mvp at 3679b1b, 23
  protected dirty entries; stash cb568efd single entry.
- Live remotes unchanged since the integration review snapshot: origin/main
  47dbb678, origin/feat/m2-value-assessment-mvp ecb74a41, delivery branch
  absent; gh pr list empty.
- North star v2 section 18: the nominated next milestone line starts from
  "从已经合并并通过 CI 的 canonical main 开始" (M4 North-Star Preflight ->
  M4-A -> M4-B). Landing this read-only M2 value-assessment capability into
  canonical main is therefore the current mainline prerequisite; it adds no
  scores, rankings or advice.

## Integration-target topology (corrects an earlier informal suggestion)

- feat/m2-value-assessment-mvp (root worktree branch; local 3679b1b, live
  remote ecb74a41) is NOT an integration target for this delivery: it
  diverged from main at 9e016e77 (2026-07-27); versus origin/main it is 261
  behind and 317/318 ahead, and its remote tip is a revert of a misplaced M3
  merge. Merging this delivery into it would be a non-fast-forward historical
  merge with no mainline value; no such merge was attempted.
- The canonical mainline is origin/main 47dbb678, integrated through PRs from
  codex/* branches (merged PR titles #82-#90 plus the merge-commit history).
  The delivery branch is a pure fast-forward candidate for main: 0 behind /
  4 ahead, and merge-tree write-tree equals HEAD^{tree} (integration review
  record 2026-10-10_12).

## Prepared landing package (execute only after explicit authorization)

PR title:
feat(m2): read-only multi-year company financial analysis (existing 12 metrics)

PR body: canonical copy below; working file
C:/Users/111/AppData/Local/Temp/codex-financial-pr-body-20261010.md
(2129 bytes, SHA256
2DC64A26277F485676F35D91EBFFF35FB4A5A967E2C6F4895CA2D576D742F965).
No pull_request_template exists; title style matches merged PRs #82-#90.

```markdown
# Read-only multi-year company financial analysis (existing 12 metrics)

## Summary
- New `ashare-research research financial` entry (`ashare_research.tools.financial_analysis`): multi-year PIT core financial analysis for any eligible A-share symbol against an explicitly supplied, read-only DuckDB facts database.
- Reuses the repository's existing 12 metric definitions (4 growth / 2 cash flow / 4 earnings quality / 2 capital return). No new formulas, no scores, no rankings, no advice.
- Strict fact/context binding (symbol, fiscal year, scope, period end/start, instant/duration); missing or excluded evidence stays visible; non-finite numbers are projected to null; incompatible newer restatements never fall back to older versions.
- Optional `--compare-with` two-instant restatement comparison, `--json`, and byte-manifest `--output NEW_DIR` export.

## Verification (branch tip 6362412, delivery worktree)
- `pytest -q` -> 3206 passed, 8 skipped, 2 warnings (both pre-existing); `ruff check src/ tests/` clean; `compileall -q src` clean.
- Integration review PASS: `merge-base --is-ancestor origin/main HEAD` holds; `merge-tree` write-tree equals `HEAD^{tree}` (content-clean fast-forward); diff vs main = 20 files, +4045, no pyproject/schema/workflow changes; all changed files carry provenance entries.
- Commits after 6362412 on this branch are docs-only (README availability wording and landing records); reviewed runtime code is unchanged.
- Protected state intact: 68/68 worktrees, 404/404 protected hashes, primary DB SHA256 unchanged (hash only, never opened).
- Evidence: `agent/goals/2026-10-10_financial_integration_review.md`, `agent/record/2026-10-10_12-financial-integration-review.md`, `acceptance/2026-10-10_m2_core_financial_analysis*.md`.

## Boundaries
- Read-only and offline: caller-supplied database path only, no default database, no network, no schema migration, no writes.
- No scoring / ranking / eligibility / recommendation / target price; M2 conditional closure, M3 `M3_DAILY_MECHANISM_NOT_ESTABLISHED` and M4 real-execution boundaries untouched.
- Built and reviewed without DSH delegation.
```

README wording flip to include in the same authorized stage (exact anchors at
6362412; keep all links and the rest of each line unchanged):
- README.md:29 cell `本分支已实现，主线集成待审阅` ->
  `已实现（只读、显式数据库、多年度 PIT；复用既有 12 个指标）`
- README.md:1055 `此入口在本分支可用，主线集成仍待审阅；` ->
  `此入口已随主线可用；`

Exact command sequence for the authorized stage (goal-first per AGENTS.md):

```powershell
# 0) next-stage goal + README flip commit, then focused re-validation
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_project_entry.py tests/test_research_entry.py tests/test_financial_analysis.py
git -C 'D:/量化分析-worktrees/量化分析-financial-json-review' diff --check
git -C 'D:/量化分析-worktrees/量化分析-financial-json-review' commit -m "docs(m2): state mainline availability of financial analysis"
# 1) push and open the PR
git -C 'D:/量化分析-worktrees/量化分析-financial-json-review' push -u origin codex/financial-json-review
gh pr create --repo dlam12138/ashare-research-lab --base main --head codex/financial-json-review --title "feat(m2): read-only multi-year company financial analysis (existing 12 metrics)" --body-file 'C:/Users/111/AppData/Local/Temp/codex-financial-pr-body-20261010.md'
# 2) merge only after CI is green AND a separate explicit merge instruction
#    (never push directly to main; merging outside a PR is not contemplated)
```

## Pre-verification performed (read-only, this task)

- `git push --dry-run origin
  codex/financial-json-review:codex/financial-json-review` authenticated and
  reported `* [new branch]` (gh CLI logged in as dlam12138, scopes
  gist/read:org/repo/workflow); an immediate `git ls-remote origin
  refs/heads/codex/financial-json-review` confirmed the remote branch was NOT
  created - the probe changed nothing anywhere.
- Full protection sweep against the integration-review start snapshot: 68
  trees and 404/404 hashes match; only the known expected deltas are this
  branch's HEAD advancing to 6362412 under the previous task's contract and
  the root worktree's core.quotepath rendering. research.duckdb SHA256
  4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6
  unchanged; stash, origin/main local+live, PR list and remote refs unchanged.
- README flip anchors exact-match exactly two locations (README.md:29 and
  README.md:1055); links inside the row verified present.

## Validation, acceptance and stop conditions

- This task is docs-only (one record): validation = exact anchor match, body
  file checksum and embedded-copy equality, `git diff --check`, protection
  sweep, and worktree cleanliness; no business tests are required because no
  executable file changes (proportional validation per AGENTS.md).
- Acceptance: exactly one local commit containing only this record; owner
  worktree clean afterwards; protected state unchanged except this branch's
  own HEAD advancing; the landing package above is verified executable.
- Stop conditions: any protection drift, anchor mismatch, authentication
  failure or scope expansion. Forbidden in this task: code/test/README edits,
  push, PR creation, merges, force-push, DSH, primary-database access, foreign
  worktree edits.
- Commit/push: one local docs commit (prepare landing package); no push; the
  landing itself remains blocked on explicit user authorization.

## Deviation from an earlier informal chat suggestion

The previous chat turn informally suggested merging into
feat/m2-value-assessment-mvp. That suggestion was topology-invalid and is
superseded by this record's verified target (canonical main via PR); no merge
was attempted anywhere.
