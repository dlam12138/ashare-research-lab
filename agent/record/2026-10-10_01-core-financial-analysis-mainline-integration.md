# Core financial analysis: mainline integration

<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

Goal: `agent/goals/2026-10-10_core_financial_analysis_mainline_integration.md`.
Root works directly without DSH or delegation. A prior context of this same
task (compaction boundary) created the two protection scripts under
`tmp/core-financial-analysis-mainline/`; this session captured the baseline
before any edit, integrated, and verified.

## What was done

- Re-verified before editing: owned worktree clean on `codex/core-financial-analysis`
  @ 4155359; origin/main local ref and live `ls-remote` both 47dbb678; merge-base
  0818edff; `git merge-tree` conflict scope limited to `research_entry.py`;
  foundation modules unchanged between feature base ce76502 and origin/main.
  Captured baseline: 64 foreign worktrees, 207 protected hashes (includes the
  primary database), stash `cb568efd`, local main 966206f.
- Created `codex/core-financial-analysis-mainline` from origin/main 47dbb678.
- `git cherry-pick 4155359` → `ceb953b`; author and message preserved. The
  merge-tree-predicted conflict in `research_entry.py` did **not** materialize:
  the feature diff's three hunks (docstring line, provenance entry,
  `ResearchCommand` block) have matching contexts on mainline. No manual
  resolution was performed; identity was verified instead:
  `git diff origin/main HEAD -- src/ashare_research/tools/research_entry.py`
  shows exactly those three hunks (+12 lines), and the seven other feature
  files are byte-identical to 4155359 (`git diff` quiet).
- Integration identity: `47dbb678` is an ancestor of `HEAD`;
  `git diff --stat 47dbb678 HEAD` = 8 files, +2644 lines.

## Validation (exact commands and actual results)

- `pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py
  tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py
  tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py
  tests/test_research_entry.py` → **166 passed in 76.52s**.
- `pytest -q tests/test_research_hypothesis_batch.py tests/test_m4b_hypothesis_registry.py`
  → **32 passed in 2.69s** (mainline entry contract on the new base).
- `ruff check` (entry, feature core/CLI, feature tests) → All checks passed.
- `git diff --check` → clean (exit 0).
- `python tmp/core-financial-analysis-mainline/verify_protections.py` → **PASS**:
  64 foreign worktrees, 207 protected hashes (primary DB SHA256 unchanged),
  stash, local main and origin/live main identical to task start.
- CLI smoke on a temporary DB rebuilt from the committed stage2g snapshot:
  `research --help` lists mainline commands plus `financial`;
  `research plan-batch --help` exit 0; `research financial --help` exit 0;
  `research financial --database <tmp> --symbol 601857.SH --as-of 2024-03-31
  --year 2023 --json` → schema `m2_core_financial_analysis_report_v1`,
  12 records, 7 `computed` / 5 `missing_input` (honest absence, unchanged).
- Evidence-to-content note: tests and smoke ran on the resolved worktree whose
  content is byte-identical to commit `ceb953b`; the commit itself changes no
  file content relative to what was tested.

## Deviations and notes

- The full-branch merge conflict seen in `git merge-tree` (M4-preparation
  command drift) is not part of this integration path: only the feature diff
  (+12 entry lines) was ported, so mainline's M4 tooling is untouched.
- Network: direct GitHub connections fail in this environment. The live-main
  check uses the repository's configured proxy (`socks5h://127.0.0.1:10808`)
  with bounded subprocess timeouts; an earlier unbounded attempt was killed
  and affected no repository state. Verifier fixed to compare foreign
  registrations correctly (owned worktree excluded) before reuse.
- The temp smoke database under `%TEMP%` (`fin-mainline-smoke-*`) was left in
  place because recursive deletion was blocked by command policy; it is
  outside the repository and touches nothing protected.
- The transient protection scripts under gitignored `tmp/` carry provenance
  headers; they are ephemeral tooling and are not committed.

## Limits and unresolved

None affecting the integration. The feature's own documented limits
(caller-database provenance not verified by the tool; descriptive-only
same-period/adjacent-year reporting) carry over unchanged.

Delivery: one scoped local docs commit with this record, the goal and the
acceptance. No push, PR or merge; the next stage requires explicit user
authorization.
