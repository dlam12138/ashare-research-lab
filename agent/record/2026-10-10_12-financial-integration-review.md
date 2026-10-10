<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Record: financial analysis independent mainline integration review

## Scope and baseline

Independent integration review of codex/financial-json-review for the user's
continued mainline direction, executed read-only at
11874aa02e2d49758735a807eefba40a8e7f1c87 with a clean worktree on
D:/量化分析-worktrees/量化分析-financial-json-review. Contract:
agent/goals/2026-10-10_financial_integration_review.md. Start snapshot:
C:/Users/111/AppData/Local/Temp/codex-financial-integration-review-20261010-before.json
(68 trees, 404 hashes, root DB, stash). Interpreter
D:/量化分析-m4a2i/.venv/Scripts/python.exe (Python 3.13.9, DuckDB 1.5.5),
PYTHONPATH=src. No DSH or executor delegation was used.

## Fast-forward and diff evidence

- `git merge-base --is-ancestor origin/main HEAD` -> exit 0.
- `git rev-list --left-right --count origin/main...HEAD` -> 0 3.
- `git merge-tree --write-tree origin/main HEAD` ->
  4c42dd169c15095fc4aa810284e7666471348df3, identical to HEAD^{tree}: merging
  origin/main into the branch reproduces the branch tree exactly
  (content-clean fast-forward; no conflict resolution).
- `git diff origin/main...HEAD --shortstat` -> 18 files changed,
  3843 insertions(+), 0 deletions; numstat sums to the same 3843.
- `git diff origin/main...HEAD -- pyproject.toml` -> empty; the name-status
  list contains no dependency, schema or workflow files.
- research_entry.py: 12 added lines, 0 removed - one docstring usage line, one
  provenance comment and one financial ResearchCommand registration block.
- All 18 changed files carry provenance entries (16 x action=created;
  README.md and research_entry.py x action=modified; all model=GPT-5,
  agent=Codex, date=2026-10-09/10).
- Commits: ceb953b feat(m2): analyze any eligible symbol with the existing
  metric definitions; 4446fb8 docs(m2): record core financial analysis
  mainline integration; 11874aa fix(m2): deliver validated company financial
  analysis.

## Full-suite gate at branch tip

Commands run in the clean owner worktree at 11874aa with PYTHONPATH=src:

- `python -m pytest -q` -> 3206 passed, 8 skipped, 2 warnings in
  2228.86s (0:37:08).
- `python -m ruff check src/ tests/` -> All checks passed! (exit 0).
- `python -m compileall -q src` -> exit 0.
- The worktree stayed clean and HEAD stayed 11874aa after all three commands.

Skip/warning attribution (verified by focused rerun, not assumed):
- `pytest -q -rs` over the five skip sites (test_capsule_builder_output_guard,
  test_capsule_output_preservation, test_m2_stage2k1r3_true_upstream_capsule,
  test_m2_stage2k1r4d1b_calendar_object_pinning,
  test_m3_stage3car2_digest_portability) -> 64 passed, 8 skipped in 11.12s;
  all 8 are environmental: symlink creation unavailable for this account (5)
  and real baostock snapshot not present in repo (3).
- The 2 warnings are pre-existing pandas dateutil-fallback UserWarnings from
  tests/test_quality.py (src/ashare_research/quality/validators.py, untouched
  by this branch).
- Context: the six most recent GitHub workflow runs at origin/main 47dbb678
  all concluded success, including "Stage 2G reproducibility" (full suite).

## Protected-state verification

Recomputed against the start snapshot before this commit (owner worktree
still clean at 11874aa):

- 68/68 worktree HEAD/status pairs identical, including the dirty root and
  all other-agent worktrees; the root worktree's single rendered difference
  is core.quotepath escaping of one Chinese filename, proven byte-identical
  with `-c core.quotepath=false status --porcelain=v1` (23/23 entries match).
- 404/404 protected file hashes identical (frozen reports/config/evidence,
  foreign work records, root north-star/governance files).
- data/research.duckdb SHA256
  4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6
  (hash-only, no connection); origin/main local and live 47dbb678; stash
  cb568efd single entry; gh pr list for the branch empty; branch absent from
  origin.
- The post-commit rerun (owner HEAD moving to the docs commit, everything
  else identical) is reported in the final chat report.

## Boundary compliance (north star v2)

- The capability is read-only and offline: caller-supplied database path only,
  no default database, no network, no writes, no schema migration; usage and
  boundaries are documented in README.md and
  docs/core_financial_analysis_guide_v1.md.
- No new formula, score, rank, eligibility, advice or target price; the
  production_eligible / score_eligible / metric_publication_proven flags stay
  false, preserving the M2 conditional closure and existing evidence gaps.
- The diff touches no M3/M4 mechanism, holdout, provider or dataset files;
  the M3 daily-mechanism NOT_ESTABLISHED and M4 real-execution boundaries are
  unchanged in code and data.

## Limitations and residual risks

- The full suite is runtime-heavy (37 minutes here) but deterministic; no
  flakiness was observed in this single run.
- The review validates integration mechanics, gates and boundary compliance;
  it does not re-verify the upstream provenance of caller-supplied databases
  or the correctness of the 12 pre-existing metric definitions, which were
  accepted earlier.
- The README capability row still labels mainline integration as pending
  review; that wording belongs to the merge stage and is out of this review's
  scope.
- The branch remains local; merging is a separate authorized step and should
  be a fast-forward of 47dbb678 to the final tip.

## Verdict

PASS - the branch is content-verified against mainline: pure fast-forward,
scoped provenance-complete diff, full gates green at the tip, protected state
intact, boundaries preserved. Integration into the feature branch is ready
pending explicit user authorization; nothing was pushed or merged.
