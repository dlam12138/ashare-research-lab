<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial analysis: independent mainline integration review

## Objective and verified baseline

Independently verify that the three-commit company financial analysis delivery
on codex/financial-json-review is ready for mainline integration, covering
fast-forward feasibility, diff scope, full repository gates at the branch tip
and preserved protected state; then record the review in one Goal plus one
work record. The user continued the project and asked to focus on the
mainline under AGENTS.md and the project north star. No DSH was requested or
used.

Verified at task start:
- Owner worktree D:/量化分析-worktrees/量化分析-financial-json-review on
  branch codex/financial-json-review was clean at
  11874aa02e2d49758735a807eefba40a8e7f1c87, three commits above origin/main.
- origin/main and live main: 47dbb6780933f8fb7abab922aa47027a1342de41.
  Chain: 47dbb678 -> ceb953b -> 4446fb84 -> 11874aa.
- Root D:/量化分析 stays feat/m2-value-assessment-mvp at 3679b1b with
  protected user edits; stash single entry cb568efd; no PR exists for the
  reviewed branch; the branch is absent from origin.
- Interpreter D:/量化分析-m4a2i/.venv/Scripts/python.exe (Python 3.13.9,
  DuckDB 1.5.5). Baseline snapshot
  C:/Users/111/AppData/Local/Temp/codex-financial-integration-review-20261010-before.json
  captured 68 worktree HEAD/status pairs, 404 protected file hashes, the root
  north-star/DB inputs and the stash entry.

## Allowed scope and required behavior

Read-only git and test inspection inside the owner worktree; create this Goal
and one work record; one docs-only commit containing exactly these two files.
The branch tip must otherwise remain byte-identical to the fully tested
revision, so the review and record are added without touching runtime code.
The record must state exactly one verdict: PASS, CHANGES_REQUIRED or BLOCKED,
with every residual risk a reviewer needs before merge authorization.

## Forbidden scope

No business code, test, README, guide, acceptance, schema, dependency or
configuration changes; no push, merge, PR, tag, amend or branch deletion; no
primary database connection beyond read-only hashing; no edits in other
worktrees; no DSH, provider or holdout execution; no new scoring, ranking or
recommendations; no deletion or cleanup of generated temporary artifacts.

## Required checks and exact commands

```powershell
git merge-base --is-ancestor origin/main HEAD
git rev-list --left-right --count origin/main...HEAD
git merge-tree --write-tree origin/main HEAD
git diff origin/main...HEAD --name-status
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ tests/
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m compileall -q src
```

The full suite at the branch tip is the deterministic mainline gate defined by
.github/workflows/stage2g-reproducibility.yml; the previously accepted focused
financial checks cannot substitute for it. The 8 skips and 2 warnings must be
attributed to pre-existing environmental causes by direct evidence, not
assumption. After the commit, recompute the start snapshot and require every
foreign tree HEAD/status and every protected hash to match, except the owner
worktree HEAD moving to the new docs commit; the root database is compared by
SHA256 hash only. Confirm origin/main, the stash and the absence of a
PR/remote branch.

## Acceptance criteria and stop conditions

- origin/main is an ancestor of HEAD; the merge-tree result equals HEAD^{tree}.
- The diff versus origin/main contains only the 18 already-recorded delivery
  files, all carrying provenance entries; no pyproject, dependency or
  workflow changes; research_entry.py shows only its additive hunks.
- pytest, ruff and compileall pass at the branch tip with exact commands,
  environment, counts and warning attributions recorded. Full-suite failures
  that are not clearly pre-existing stop the review as CHANGES_REQUIRED.
- Protected snapshot comparison passes; the root database hash is unchanged;
  the feature branch, stash and origin refs remain untouched.
- Exactly one new commit containing the Goal and the record; no push.
- Stop for concurrent protected-state drift, scope expansion or unexplained
  test results.

## Commit and push requirements

Create one normal local commit (docs(m2): review company financial analysis
integration). Do not amend, push, merge or create a PR; integrating into the
feature branch remains a separate explicitly authorized step.
