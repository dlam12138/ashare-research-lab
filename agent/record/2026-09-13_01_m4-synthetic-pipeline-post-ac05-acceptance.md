# M4 synthetic pipeline post-AC-05 acceptance record

Date: 2026-09-13. Goal: [post-AC-05 contract](../goals/2026-09-13_m4_synthetic_pipeline_post_ac05_acceptance.md).

## Verified starting state

The worktree began clean on `codex/m4-synthetic-pipeline-acceptance` at `c9ff0c5a17b022ddbce0bd724e10a5ff6aaafb51`, matching local/origin/live main after PR #18 merged with 42 successful CI checks. The Goal was committed first. The preserved candidate remained clean at `codex/m4-synthetic-pipeline-resume@f5f419e0377cf74925bd8bbff27f8a2f1c513ffd`; its historical `CHANGES_REQUIRED` verdict was not accepted as a passing review.

## Scoped transfer and corrections

Using explicit `git restore --source=f5f419e --worktree -- <paths>`, transferred only `README.md`, two new pipeline source files, and the new orchestrator test. Did not transfer the historical record or acceptance file. Updated two `FROZEN_BLOBS` values to the actual post-PR #18 normative blobs (`6c2bd048f4f7e74bb4a8015b53c9a6e76fd483cd`, `2393b4723ef8ac4aa883a34386b7618fb2cd9025`), changed the AC-05 comment to state its corrected S6 rank behavior, and pointed the README implementation evidence link at the new acceptance file. The pipeline implementation itself is byte-identical to the preserved candidate.

## First validation findings

The first 51-test pipeline run gave `50 passed, 1 failed`: AC-21 compared a snapshot of the shared platform temporary directory while an unrelated process changed filenames there. The pipeline call did not use filesystem IO according to its existing `open`/socket probes and repository/package snapshots. The unchanged AC-21 test passed in isolation (`1 passed`, exit 0); the unchanged full suite then passed `51 passed` (exit 0). The first upstream run gave `328 passed`, exit 0. The first governance run gave `14 passed, 1 failed` because README linked to this acceptance file before it existed; after its creation, governance passed `15 passed` (exit 0). Ruff passed. These initial failures remain failures in this record. A committed Goal addendum `45a5864ac4a3d719dc79942e2dc4c56e3c70c99f` then authorized isolating AC-21's external directory with pytest `tmp_path`; all pre-existing no-I/O and snapshot assertions remain. Full post-change reruns and final review follow below.

## Independent review and final local validation

The two source file blobs are byte-identical to `f5f419e` (`b53e847ef40e7f9d41fbf4af63521341a5297f53`, `dfdc8876b1ba40ad968a3ec41747aca31b23baae`). Direct source inspection confirmed a single keyword-only request entry, S0–S8 ordered composition, existing stage producer/validator calls, S3 enabled-only replication gate, S4 quality rejection, S6 existing execution error propagation, S7 digest-bound immutable envelope and V1–V6 validation. The package exports exactly 20 frozen symbols; the test suite checks the 14-code set and forbids direct provider/IO imports and calls. No source behavior was altered during this transfer. AC-01–AC-30 are present and the final 51-test run reported no skips or xfails.

| Exact command (`PYTHONPATH=<worktree>/src`, Python `D:/量化分析-m4a2i/.venv/Scripts/python.exe`) | Result |
| --- | --- |
| `python -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py` | Initial: 50 passed, 1 failed (AC-21 shared temp directory), exit 1; unchanged rerun: 51 passed, exit 0; after isolated `tmp_path` correction: **51 passed in 61.74s**, exit 0 |
| `python -m pytest -q -p no:cacheprovider tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py` | **328 passed in 38.30s**, exit 0 |
| `python -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | Initial: 14 passed, 1 failed (new evidence file absent), exit 1; after file creation: **15 passed in 0.12s**, exit 0 |
| `python -m ruff check src tests` | All checks passed, exit 0, including after AC-21 isolation |

The two corrected normative blobs match main (`6c2bd048...`, `2393b472...`). Protected bounded-execution, M4-B registry and Stage4P blobs remain `9617f643...`, `6d9c2920...`, `dfd41eaa...`. The original M2 worktree retains its existing dirty files at `3679b1ba...`; the preserved candidate worktree is clean at `f5f419e...`; the one stash remains `cb568efd...`; the default database file SHA256 remains `4A71D3C7...E2FCE6`. No database connection or real-data execution was made. `docs/**`, `reports/**`, `config/**`, `data/**`, `events/**`, `.github/**`, and `pyproject.toml` have no diff against `origin/main`.

## Release boundary

The worktree contains only this Goal plus the six authorized deliverable paths. The inherited design's recorded limitations remain: numeric result identity is frozen only for the same interpreter/numpy runtime, and `READY_SYNTHETIC` grants no real-research authorization. Final Git/remote/worktree and Markdown checks, scoped commit, PR and CI evidence are completed by Codex after this record is written; their exact commit/PR identifiers are given in the final evidence packet. No next research stage begins here.
