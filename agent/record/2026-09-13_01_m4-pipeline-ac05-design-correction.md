# M4 pipeline AC-05 design correction record

Date: 2026-09-13. Goal: [AC-05 correction contract](../goals/2026-09-13_m4_pipeline_ac05_design_correction.md).

## Baseline and decision

The new worktree began clean at `main` / `origin/main` / live GitHub main `291b733d710fcccae9436f4d93215988af06db5a`. The Goal was committed first as `174903f2972f99c22b7ff8e54b3c7f380a875c77`. The prior candidate remained clean on `codex/m4-synthetic-pipeline-resume@f5f419e0377cf74925bd8bbff27f8a2f1c513ffd` with `CHANGES_REQUIRED` acceptance; it was neither modified nor treated as accepted.

The existing design §8.5.1 lists `SINGULAR_DESIGN` as a composed-entry S6 error. In `execution/bounded.py`, `_estimate` checks matrix rank before OLS and raises this code without pseudoinverse or dropped-column fallback. The preserved candidate's `test_ac05_minimum_materializable_domain_and_empty_domain_boundary` confirms a three-row preparation reaches that check; on this turn it was independently rerun: `1 passed in 0.30s`, exit 0. AC-05 alone had restricted failure to `AdapterError` / `MatrixError`, contradicting those frozen facts.

## Changes

- `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`: classify the adapter, matrix and S6 rank outcomes separately; require the existing error type/code to pass through and forbid a partial envelope or rank-gate bypass. Clarify that a particular three-row fixture is singular, without claiming every three-row input is singular.
- `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`: add the AC-05 cross-reference and make the already-listed S6 `SINGULAR_DESIGN` explicit in §8.4.
- This record and `acceptance/2026-09-13_m4_pipeline_ac05_design_correction.md`: document the narrow correction and verification. No source, tests, README, schemas, protected blobs or runtime data changed.

## Validation performed

From the correction worktree, `PYTHONPATH=<worktree>/src`, Python `D:/量化分析-m4a2i/.venv/Scripts/python.exe`:

| Command | Observed result |
| --- | --- |
| `python -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | 15 passed in 0.21s; exit 0 |
| `python -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py` | 49 passed in 28.15s; exit 0 |
| `python -m ruff check src tests` | All checks passed; exit 0 |
| Preserved candidate: `python -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py::test_ac05_minimum_materializable_domain_and_empty_domain_boundary` | 1 passed in 0.30s; exit 0 |
| `git diff --check`; `git diff --cached --check` | Both exit 0 |

The repository has one unchanged stash (`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`); original M2 HEAD remains `3679b1bac7a1634c6452784a4d8f6d139966f222`; default DB SHA256 remains `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`. Three protected blobs remain `9617f64360b6c3d9a6148ec08c25fa0209a0f9f4`, `6d9c292001c09a4b1a8e895e54619dc1e8826f3d`, and `dfd41eaafc099e7748499f72de7ddd800bf97f69`. Other existing worktrees were read-only and retain their HEADs.

The contract's proxy-cleared `git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/main` failed twice with connection reset / port 443 connection failure (exit 128). The configured-proxy `git ls-remote origin refs/heads/main` then returned live main `291b733d710fcccae9436f4d93215988af06db5a` (exit 0). GitHub API independently returned the same live main (exit 0), matching local `main` and `origin/main`; `gh pr list --state open` returned `[]` (exit 0). This is a direct-transport deviation, not a claim that the proxy-cleared command passed.

## Next boundary

This task delivers a design correction only. The preserved implementation needs a fresh, separate acceptance against the corrected AC-05 after this correction is integrated into main. Do not infer permission to merge this branch or start that acceptance from this record.
