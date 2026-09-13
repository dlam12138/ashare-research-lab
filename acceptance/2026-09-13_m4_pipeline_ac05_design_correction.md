# Acceptance: M4 pipeline AC-05 design correction

Verdict: **PASS** for the scoped documentation correction. Goal: [task contract](../agent/goals/2026-09-13_m4_pipeline_ac05_design_correction.md); work record: [execution record](../agent/record/2026-09-13_01_m4-pipeline-ac05-design-correction.md).

The verified base is `main@291b733d710fcccae9436f4d93215988af06db5a`; the review branch is `codex/m4-ac05-design-correction`. This verdict concerns the AC-05 specification only; it is not acceptance of the unmerged pipeline implementation.

The previous AC-05 wording allowed only `AdapterError` or `MatrixError` for a minimum materializable domain. Yet the already-frozen design §8.5.1 includes `ExecutionError("SINGULAR_DESIGN")` as composed-reachable, and the upstream estimator's rank check produces it for the preserved three-row fixture after adapter and matrix construction succeed. The correction records all three stage-specific outcomes without changing or bypassing that check. It still requires stable first error and no partial envelope. Empty domain still raises `AdapterError("EMPTY_EXPECTED_DOMAIN")` at `ExpectedDomainV1` construction.

Changed paths are exactly the two normative Markdown files, this acceptance file, its record, and the new Goal. No source/test/README/API/schema/error code/authorization change was made. A three-row fixture yielding `SINGULAR_DESIGN` is an observed case, not a new rule that all small inputs must fail.

Validation from the correction worktree: governance/project-entry `15 passed` (exit 0); bounded-execution `49 passed` (exit 0); Ruff `All checks passed` (exit 0); `git diff --check` and cached check exit 0. The preserved candidate's AC-05 probe was independently rerun in its clean worktree: `1 passed` (exit 0). The existing S6 rank gate and §8.5.1 classification were independently inspected. Markdown UTF-8, links, whitespace, and final newline were checked separately. The exact command forms, elapsed times and environment are in the linked record.

Protected M2 HEAD, stash, database SHA256 and three protected blob hashes match the Goal/record. `main`, `origin/main` and live GitHub main agree at the verified base. The proxy-cleared `git ls-remote` failed twice (exit 128), but the configured-proxy `git ls-remote` and GitHub API each succeeded and returned the same live main (exit 0). No open PR existed at review time. The original M2 worktree remains dirty with its pre-existing user files; this correction worktree is scoped to the five stated files. No other worktree, stash or runtime data was modified.

This result allows the design correction to be reviewed as a separate change. It does not authorize automatic merge, implementation acceptance, real-data work, or the next project stage.
