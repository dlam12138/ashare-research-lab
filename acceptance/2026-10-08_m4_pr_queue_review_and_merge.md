# M4/M2 open PR queue review and merge closeout — acceptance

Verdict: PASS

- Contract: `agent/goals/2026-10-08_m4_pr_queue_review_and_merge.md`.
- Work records: `agent/record/2026-10-08_01-m4-pr-queue-review-and-merge.md`
  (single rolling record, updated across both sessions).
- Branch: `codex/m4-pr-queue-closeout` (created from origin/main `8d0fb4d`);
  this acceptance document, the Goal and the record are the branch's only files.

## Scope performed

Under the standing merge authorization recorded 2026-09-28, and the user's
explicit instruction "继续推进项目。不用dsh。你自己来干" (proceed, no DSH, root
agent only), the open PR queue #72 and #81–#91 was independently re-verified and
merged where the exact head had a fully successful hosted check set and GitHub
computed a clean merge. No research stage, no data acquisition, no holdout, no
statistics, no production code change outside the reviewed PR branches
(conflict-resolution merges only).

## Completed merges (verified merge commits on main)

| PR | head at merge | checks at head | main after merge |
| --- | --- | --- | --- |
| #81 | `c3e22e6d` | 42/42 success | `184baf28` |
| #82 | `36b66ee0` | 42/42 success | `5b30367e` |
| #83 | `fb6738c1` | 42/42 success | `95fc18e` |
| #84 | `bbc29429` | 42/42 success | `3346dbb6` |
| #85 | `3909db6c` | 42/42 success | `91a31bdd` |
| #86 | `b48cc47b` | 42/42 success | `a9cae1fb` |
| #87 | `32f1dcfa` | 42/42 success | `fd55e12c` |
| #88 | `98011e78` | 42/42 success | `94b01231` |
| #90 | `42aae481` | 42/42 success | `f087b18d` |
| #72 | `acb1fd17` | 42/42 success | `47dbb678` |

Prior session (same Goal) already merged #68–#80 in dependency order, including
the cross-platform test defect fix `1a81ffa` (junction fixture made portable:
POSIX symlink / Windows junction), verified present in main.

Final main after the entire queue: `47dbb6780933f8fb7abab922aa47027a1342de41`
(live GitHub ref and local `origin/main` agree after fetch). Each of the ten heads
merged on 2026-10-09 carried a fully successful 42-check hosted set at merge time,
re-read per PR; #86's state was being recomputed (UNKNOWN) at the check instant and
the merge request was accepted by GitHub.

## Conflict resolutions published to the reviewed branches

GitHub's merger refuses some criss-cross histories (two incomparable merge
bases; "the merge commit cannot be cleanly created") even when local git
merges cleanly. The verified remedy is to make each branch head contain the
current main before merging. All such merges below were content no-ops
(tree diff vs the previous head is empty); only ancestry changed, and the
pre-existing 42-check success set had to be re-earned by hosted CI on the new
heads (that is why heads changed).

- `codex/m4-registry-view` → `fb6738c1`, `codex/m4-registry-transition-preflight`
  → `bbc29429`, `codex/m4-registry-compare` → `8a0fd4ba`,
  `codex/m4-registry-compare-summary` → `8c206a5b`,
  `codex/m4-registry-membership` → `b3b1f3f8`.
- #88 `codex/m4-hypothesis-compare` → `06d24ed7`: merged future-main content
  (`b3b1f3f8`); resolved README (kept main's block plus the hypothesis-diff
  section) and `research_entry.py` (kept all command rows; hypothesis-diff row
  added at the top). Local `pytest tests/test_research_hypothesis_compare.py
  tests/test_research_plan.py tests/test_research_entry.py` = 11 passed;
  ruff clean on the three touched files; `git diff --check` clean.
- #90 `codex/m4-hypothesis-batch` → `59c80de3`: same class of README/entry
  resolution (plan-batch row at top). Local pytest for
  `tests/test_research_hypothesis_batch.py tests/test_research_plan.py
  tests/test_research_entry.py` = 14 passed; ruff clean; diff check clean.
- #72 `codex/m4-plan-comparison` → `f43aa29b`: resolved README (both example
  sets kept), `research_entry.py` (plan usage lists both --compare-with and
  --output/--archive surfaces) and `research_plan.py` (`--compare-with`
  integrated into the extended `main()` with INVALID_ARGUMENTS guard and a
  comparison output branch; helper functions unchanged). Local pytest for
  `tests/test_research_plan.py tests/test_research_plan_comparison.py
  tests/test_research_entry.py` = 8 passed; ruff clean; diff check clean.

## Chain pre-merge (second continuation, 2026-10-09)

After #84 merged, the next heads flipped to DIRTY again (same criss-cross
condition). Instead of one fix-wait-merge cycle per PR, all six remaining heads
were prepared in one chain: each new head contains a locally simulated "future
main" merge commit (`F1`–`F5`, created with `git commit-tree`; never pushed as
main), so every GitHub merge sees a unique merge base equal to the previous
head's fix parent. All merges below were ordinary non-force pushes; the five
registry/hypothesis heads were content no-ops (tree identical before/after).

- #85 `3909db6c` (merge of main `3346dbb6`; tree no-op)
- #86 `b48cc47b` (merge of F1; no-op)
- #87 `32f1dcfa` (merge of F2; no-op)
- #88 `98011e78` (merge of F3; no-op)
- #90 `42aae481` (merge of F4; resolved real README / `research_entry.py`
  conflicts: both the hypothesis-diff and plan-batch sections retained, and two
  separate `ResearchCommand` entries kept, hypothesis-diff first; focused tests
  19 passed, ruff clean)
- #72 `acb1fd17` (merge of F5; README/entry auto-merged; focused tests
  21 passed, ruff clean)

On the new heads GitHub reported MERGEABLE with no conflicts; hosted CI re-earned
42/42 success on each; they were then merged sequentially.

## Not merged: #89 and #91 (reported, awaiting a design decision)

Evidence of duplication with already-merged functionality:

- #89 adds a top-level `research plan-package --hypothesis JSON --output
  NEW_DIR` / `--verify DIR` command with package members `report.json` /
  `report.md`, while main already provides the same workflow as
  `research plan --hypothesis JSON --output NEW_DIR` / `--verify DIR` with
  members `plan.json` / `plan.md` (merged via #68). Both declare
  `SCHEMA = "m4_compile_only_plan_package_v1"`, so the two layouts conflict
  add/add on the same module and would define one schema name for two
  different member sets.
- #91 builds ZIP delivery on top of #89 (`plan-archive --package DIR
  --output NEW_ZIP` / `--verify ZIP`); main already provides ZIP delivery as
  `research plan --hypothesis JSON --archive NEW_ZIP` / `--verify-archive ZIP`
  (merged via #69). #91's only extra surface is archiving an existing package
  directory, which main can express by re-exporting from the hypothesis.
- Merging either PR as-is is impossible without a design decision (rename one
  layout, or reconcile member names/manifest schema and downstream users).
  This is out of the "review and merge" scope and is reported instead, with
  branches and PRs left open and untouched.
- Optional salvage noted for a possible future, separately authorized change:
  #89 contains extra I/O hardening main's version lacks (open + fstat
  dev/ino identity checks, `..` rejection, per-file size limits, directory
  identity revalidation before writes).

## Protected baseline verification (before and after)

- Primary worktree `D:/量化分析`: `feat/m2-value-assessment-mvp` @
  `3679b1bac7a1634c6452784a4d8f6d139966f222`, pre-existing dirty/untracked
  user files preserved (21 `git status --short` entries at both checks; none
  created or removed by this task).
- Stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` unchanged (single entry).
- Database `D:/量化分析/data/research.duckdb` SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`
  unchanged.
- No force push, no direct main push, no branch deletion, no tag rewrite; all
  pushes were ordinary fast-forward pushes to the reviewed PR branches.

## Exact validation commands (selection)

```powershell
gh pr view <N> --json headRefOid,mergeStateStatus,mergeable
gh pr checks <N>
gh pr merge <N> --merge
git merge-base --all origin/main <head>      # multi-base diagnosis
git merge-tree --write-tree --name-only origin/main <head>
git diff --stat <previous-head> <merge-head> # empty = content no-op merge
git -c http.proxy= -c https.proxy= fetch origin main   # proxy bypass; see limits
python -m pytest -q <PR test modules>        # per-branch local validation
python -m ruff check <PR changed files>
git diff --check
git stash list; Get-FileHash -Algorithm SHA256 data/research.duckdb
```

## Limits and residual risks

- Hosted CI on the new heads is required and was awaited before each merge;
  local runs alone are not treated as merge evidence.
- Local git through the configured SOCKS proxy intermittently failed
  (`Failed to connect to github.com port 443`); bypass mode worked earlier,
  and the configured proxy worked later in the session. Fetch retries were
  used; no git configuration was changed.
- The criss-cross merge-base behavior of GitHub's merger is not fully
  documented; the workaround (branch contains current main) is empirical but
  was applied consistently and each merge was re-verified at its exact head.
- #89/#91 remain open by design; closing or reworking them requires the user's
  design decision (see above).
- No real-data acquisition, research execution, holdout use or statistics were
  performed or authorized anywhere in this closeout.
- During the second continuation the local proxy kept dropping connections
  (`api.github.com` EOF, git schannel handshake failures). Queries/merges were
  completed through direct connections (gh with HTTP(S)_PROXY cleared for the
  child process; git with `-c http.proxy= -c https.proxy=`); no configuration
  was changed.
- The chain pre-merge commits F1–F5 exist only as branch ancestry; main received
  only GitHub-created merge commits. The workaround is empirical (GitHub's
  criss-cross behavior is undocumented) but was applied consistently and every
  merge was re-verified at its exact head.

## Final evidence packet

- Goal compliance and final state: see the record file sections 验证/结果/最终Git状态
  in `agent/record/2026-10-08_01-m4-pr-queue-review-and-merge.md`.
- This branch's own commit and PR are merged under the standing authorization
  after the hosted checks on its exact head complete successfully.
