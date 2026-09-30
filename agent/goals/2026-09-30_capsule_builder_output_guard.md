# Goal: validate capsule input before claiming a fresh output directory

- Objective: invalid/missing snapshots must not leave an output directory that
  blocks retry. Refuse caller outputs present initially or appearing at mkdir,
  without adopting/clobbering their contents. Preserve valid capsule bytes.
- Authorization: user requested continued engineering after PR #37 merged;
  bounded capsule boundary repair and scoped PR delivery under standing merge
  authorization in AGENTS.md. No new research/data stage.
- Verified baseline: live remote main/origin/main
  74418cc39c89945aa1a45e4627ee3873fced92b8, PR #37 MERGED with 42 successful
  checks. New clean branch codex/capsule-builder-output-guard at that commit;
  prior delivery branch 0c06484 preserved in the same isolated worktree.
- Protected primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222,
  all dirty/untracked files and user worktrees; stash
  cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed: only build_test_capsule guards/order/docstring in
  src/ashare_research/reproducibility/capsule.py, new
  tests/test_capsule_builder_output_guard.py, this Goal, corresponding record and
  acceptance document. DSH edits only source/new test; parent owns evidence and Git.
- Required behavior: existing output guard remains before reading input;
  explicitly reject dangling symlinks as well as existing file/directory targets.
  Validate supplied snapshot before creating output or missing parent directories.
  Claim output with mkdir(parents=True, exist_ok=False), retaining atomic refusal
  of a competing directory at that boundary. No retries/adoption, target deletion
  or rollback of caller files. All later building, DB publication, manifest
  structure/digests and runner behavior unchanged.
- Required tests: actual missing and invalid snapshot leave no output/parents;
  corrected input can retry same output without manual cleanup; initial file,
  directory, live/dangling symlink rejected before input access with preservation;
  deterministic competing directory/file creation at output mkdir leaves caller
  bytes intact and causes FileExistsError. Existing valid build/compare/run tests
  remain. Symlink privilege skips explicit and only environmental.
- Boundaries: failures after successful exclusive output mkdir can still leave
  task-created partial output. No full directory atomic publication, cleanup,
  hostile path-mutation/provenance or concurrent input-writer guarantees added.
- Forbidden: other source/tests, fixtures/schema/research contracts/methods,
  real inputs/providers/backtests/holdout, user runtime cleanup, primary changes,
  test weakening, recursive delegation, force push or direct main push.
- Exact parent validation (PowerShell in this worktree):
  $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
  python -m pytest tests/test_capsule_builder_output_guard.py tests/test_capsule_runtime_db_isolation.py tests/test_capsule_output_preservation.py tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_stage2g_dividend_correction_and_valuation.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
  & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
  git diff --check
  git diff --cached --check
- Parent reproduces baseline missing-input retry block and output-creation race
  in owned temporary directories, reruns same probe after repair, compares old/new
  valid manifest bytes using committed fixture. Baseline new tests may run in memory
  against git-show source, without changing protected worktree files.
- Acceptance: parent independently inspects actual bounded diff, baseline fails
  and repaired behavior passes, required suite/lint/whitespace pass with explicit
  skips, valid capsule manifests unchanged, protected state retained; all hosted
  checks successful on exact published head before expected-head guarded merge.
- Stop: scope conflict, failed validation after two repairs, failed hosted checks,
  head/base drift, DSH unavailable/failed or protected-state drift. No fallback
  worker or bypass. No automatic next stage.
- Delivery: one scoped commit/task-branch push/PR, then guarded merge after
  independent local review and all expected hosted checks. Preserve branches;
  final PR/head/merge identities and synchronization supplied in final handoff.
